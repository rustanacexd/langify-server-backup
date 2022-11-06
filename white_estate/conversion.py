import json
import tempfile
import zipfile
from html import unescape
from io import BytesIO
from pathlib import Path
from pprint import pprint
from xml.etree.ElementTree import XML

import regex as re
from bs4 import BeautifulSoup

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from panta import models
from panta.constants import CHANGE_REASONS
from panta.utils import get_system_user
from panta.validators import ROMAN_NUMERAL_PATTERN

from .apis import EGWWritingsClient
from .models import Class, Tag

User = get_user_model()


class SortingError(Exception):
    pass


WHITESPACE_RE = re.compile(r'&(nbsp|#160);')

# XML

WORD_NAMESPACE = (
    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
)
PARA = WORD_NAMESPACE + 'p'
TEXT = WORD_NAMESPACE + 't'


class Import(EGWWritingsClient):
    """
    Import Ellen White books.
    """

    verbosity = 2
    html_tags = {}
    html_classes = {}
    tags = {}
    reference_only_regex = re.compile(
        r'.*((Refiled as)|(Copied from)|(Filed in)|(Extract from)'
        r'|(Duplicate of)|(Notes only)|(Missing)|(Unauthenticated)|(Same as)'
        r'|(Fragment only))'
    )
    imported = 0
    skipped = 0

    max_mismatch = 20

    # API

    def __init__(self, dry=False):
        super().__init__()
        self.dry = dry
        if dry:
            print('Dry mode: Nothing is saved to the database')

    def get_original_work(self, lookup):
        if isinstance(lookup, int):
            return models.OriginalWork.objects.get(pk=lookup)
        else:
            return models.OriginalWork.objects.get(abbreviation__iexact=lookup)

    def get_tag(self, name):
        if name not in self.tags:
            self.tags[name], created = models.Tag.objects.get_or_create(
                name=name, defaults={'slug': slugify(name)}
            )
        return self.tags[name]

    def load_document_from_zip(self, work):
        self.egw_id = work['book_id']
        data = self.get(work['download'], json=False)
        with zipfile.ZipFile(BytesIO(data)) as doc:
            work = self.get_json_work(doc)
            segments = self.load_segments(doc)
        if work['author'] != 'Ellen Gould White':
            if self.verbosity >= 3:
                print(
                    f'Skipping work "{work["title"]}" because it is written by '
                    f'{work["author"]}.'
                )
            self.skipped += 1
            return None, None
        return work, segments

    def work_exists(self, work):
        key = work.get('book_id') or work['pubnr']
        segments = models.OriginalSegment.objects.filter(
            key__startswith=f'{key}.'
        )
        if segments.exists():
            if self.verbosity >= 4:
                print(
                    f'Skipping work "{work["title"]}" because it '
                    'was imported already.'
                )
            return True
        return False

    # API: single work

    def from_api(self, query=None, book_id=None, language='en'):
        book_id = book_id or self.get_id_for_book(query, language)
        url = f'/content/books/{book_id}/download/'
        self.verbosity = 5
        work = {'book_id': book_id, 'download': url}
        return self.load_document_from_zip(work)

    def get_json_work(self, path):
        with path.open('info.json') as work:
            work = json.load(work)
        return work

    @transaction.atomic
    def create(self, query=None, book_id=None, language='en'):
        """
        Use this to import a single work with all it's segments.
        """
        work, segments = self.from_api(
            query=query, book_id=book_id, language=language
        )
        if self.work_exists(work):
            return
        self.create_work_and_segments(work, segments, None)

    @transaction.atomic
    def update(self, work):
        """
        Use this to update some fields of a work and all it's segments.
        """
        if isinstance(work, str):
            work = models.OriginalWork.objects.get(abbreviation__iexact=work)
        x, segments = self.from_api(query=work.abbreviation)
        queryset = work.segments.all()
        self.work = work
        segments = self.update_segments(segments, queryset)
        self.update_translated_segments(segments)

    # API: multiple works

    def import_all_english_egw_writings(self):
        """
        Use this to import all English writings from E. White
        with all their segments.

        Already imported works are skipped.
        """
        for folder in self.get_folders():
            if folder['name'] == 'EGW Writings':
                folders = {f['folder_id']: f for f in folder['children']}
                break

        to_import = {
            4: 'Books',
            1227: 'Devotionals',
            5: 'Periodicals',
            8: 'Pamphlets',
            9: 'Manuscript Releases',
            10: 'Misc Collections',
            14: 'Biography',
        }
        for folder_id, name in to_import.items():
            folder = folders[folder_id]
            assert folder['name'] == name
            if self.verbosity >= 1:
                print(f'Importing {name}…')
            self.import_works_in_folder(folder)

        # It seemed easier to me to import following works not with the
        # "books by folder" endpoint
        self.import_all_english_egw_manuscripts()

        return {'imported': self.imported, 'skipped': self.skipped}

    def import_works_in_folder(self, folder):
        json_works = self.get(f'content/books/by_folder/{folder["folder_id"]}')
        add_tag = (
            'Devotionals',
            'Pamphlets',
            'Manuscript Releases',
            'Misc Collections',
            'Letters',
            'Manuscripts',
            'Biography',
        )

        for w in json_works:
            if self.work_exists(w):
                self.skipped += 1
                continue

            # Get and prepare data
            work, segments = self.load_document_from_zip(w)
            if not work:
                continue

            # Tag name
            folder_name = folder['name']
            if folder_name in add_tag:
                tag_name = folder_name.strip('s')
            else:
                tag_name = None

            # Save
            self.create_work_and_segments(work, segments, tag_name)
            self.imported += 1

    def import_all_english_egw_periodicals(self):
        """
        An alternative way to import periodicals. Imports more works than with
        'import_all_english_egw_writings'.
        """
        if self.verbosity >= 1:
            print(f'Importing Periodicals…')
        for work, segments in self.get_documents('periodical'):
            self.create_work_and_segments(work, segments, None)
            self.imported += 1

    def import_all_english_egw_manuscripts(self):
        if self.verbosity >= 1:
            print(f'Importing Letters & Manuscripts…')
        for work, segments in self.get_documents('manuscript'):
            # Don't import refiled/copied works
            skip = False
            if len(segments) <= 8:
                for s in segments:
                    classes = self.get_classes(s)
                    is_info = 'mspubinfo' in classes or 'ltpubinfo' in classes
                    match = re.match(self.reference_only_regex, s['content'])
                    if is_info and match:
                        if self.verbosity >= 3:
                            print(
                                f'Skipping work "{work["title"]}" because it '
                                'doesn\'t have content (notes only).'
                            )
                        self.skipped += 1
                        skip = True
            if skip:
                continue
            tag = work['subtype'].title()
            assert tag in ('Letter', 'Manuscript')
            self.create_work_and_segments(work, segments, tag)
            self.imported += 1

    def get_documents(self, kind):
        next_url = f'content/books?type={kind.lower()}'
        works = ()
        while next_url:
            for w in works:
                if self.work_exists(w):
                    self.skipped += 1
                else:
                    work, segments = self.load_document_from_zip(w)
                    if work:
                        yield work, segments
            received = self.get(next_url)
            next_url = received['next']
            works = received['results']

    # API: create/update

    @transaction.atomic
    def create_work_and_segments(self, work, segments, tag_name):
        try:
            self.create_work(work)
            self.create_segments(segments)
        except Exception:
            print(work)
            raise
        if tag_name:
            self.work.tags.add(self.get_tag(tag_name))

    def create_segments(self, json_segments, osegments=None):
        model_segments = self.build_model_segments(json_segments, osegments)
        if not self.dry:
            if osegments:
                model = models.TranslatedSegment
            else:
                model = models.OriginalSegment
            objs = model.objects.bulk_create(model_segments)
            if osegments:
                user = get_system_user('egwwritings')
                for s in objs:
                    s._history_user = user
                records = model.history.bulk_history_create(objs)
                # todo: Improve this when this issue is implemented
                # github.com/treyhunner/django-simple-history/issues/442
                model.history.filter(pk__in=[r.pk for r in records]).update(
                    history_type='+',
                    history_change_reason=CHANGE_REASONS['import'],
                )
                self.check_tags_and_classes(model_segments)
            else:
                self.register_tags_and_classes(model_segments)

        if self.verbosity >= 2:
            count = len(model_segments)
            print(f'Imported "{self.work.title}" with {count} segments')

    def update_segments(self, json_segments, queryset):
        model_segments = self.build_model_segments(json_segments)
        saved_segments = []
        for segment in model_segments:
            to_update = queryset.get(
                page=segment.page,
                reference=segment.reference,
                position=segment.position,
                work=segment.work,
            )
            content_changed = to_update.content != segment.content
            to_update.tag = segment.tag
            to_update.classes = segment.classes
            to_update.content = segment.content
            to_update.key = segment.key
            if content_changed:
                pass
            # TODO save with new record when content changed
            to_update.save_without_historical_record()
            saved_segments.append(to_update)

        self.register_tags_and_classes(saved_segments)
        return saved_segments

    def update_translated_segments(self, segments):
        for segment in segments:
            segment.translations.update(
                tag=segment.tag, classes=segment.classes
            )

    def convert_content(self, content, key):
        # Convert character references to Unicode but not < and >
        lt, gt = '&lt;', '&gt;'
        if lt in content or gt in content:
            content = content.replace('&ldquo;', '“').replace('&rdquo;', '”')
            text = content.replace(lt, '').replace(gt, '')
            assert not re.match(
                '&[a-z]+;', text
            ), f'< or > found with other character references in "{content}".'
        else:
            content = unescape(content)

        content = self.replace_inline_p(content)

        # Fix malformed HTML
        if key == '14039.2047':
            content = content.replace(
                '<span class="egw-eng title="COL 116">',
                '<span class="egw-eng" title="COL 116">',
            )
        elif key == '428.4126':
            content = content.replace(
                '<sup class"footnote">', '<sup class="footnote">'
            )
        elif key == '12670.1640':
            content = content.replace('<b/>', '<br/>')
        elif key == '650.952':
            content = content.replace('<en>', '<em>')

        soup = BeautifulSoup(content, 'html.parser')
        soup = soup.decode()
        s, n = WHITESPACE_RE.subn(' ', soup)
        if n:
            length = len(soup)
            for m in WHITESPACE_RE.finditer(soup):
                start = m.start() - 5 if m.start() > 5 else 0
                end = m.end() + 5 if m.end() < length - 5 else length
                info = 'Replace non breaking white space: "{}"'
                print(info.format(soup[start:end]))

        return s

    def replace_inline_p(self, content):
        po, pc = '<p', '</p>'
        br = '<br/>'
        length_br = len(br)
        if po in content:
            if self.verbosity >= 2:
                print(f'Replaced <p> with <span> in "{content}".\n\n')
            content = content.replace(po, '<br/><br/><span')
            content = content.replace(pc, '</span><br/><br/>')
            while content.startswith(br):
                content = content[length_br:]
            while content.endswith(br):
                content = content[:-length_br]

        return content

    @transaction.atomic
    def add_translation(self, query, language, original):
        original = self.get_original_work(original)
        if language == 'tr':
            language = 'tur'
        work, segments = self.from_api(query=query, language=language)
        self.create_work(work, original=original)
        self.create_segments(segments, osegments=original.segments.all())

    # JSON file

    def from_file(self, source):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.load_data(source, temp_dir)
            self.import_data(temp_dir)

    def load_data(self, source_file, temp_dir):
        with zipfile.ZipFile(source_file) as zip_ref:
            zip_ref.extractall(temp_dir)

    @transaction.atomic
    def import_data(self, source_dir):
        path = Path(source_dir)
        self.create_work(path)
        self.create_segments(self.load_segments(path))

    # DOCX file

    def from_docx(self, path):
        with zipfile.ZipFile(path) as document:
            xml_content = document.read('word/document.xml')
        tree = XML(xml_content)
        paragraphs = []
        for para in tree.getiterator(PARA):
            texts = (node.text for node in para.getiterator(TEXT) if node.text)
            if texts:
                paragraphs.append(''.join(texts))
        return paragraphs

    # Import

    def create_work(self, json_work, original=None):
        # original is an OriginalWork instance used for the TranslatedWork
        if original:
            work = models.TranslatedWork()
            work._create_segments = False
        else:
            work = models.OriginalWork()
        work.title = json_work['title']
        work.abbreviation = json_work['code']
        work.type = json_work['type']
        work.description = json_work['description']
        if json_work['lang'] == 'tur':
            work.language = 'tr'
        else:
            work.language = json_work['lang']
        work.trustee = models.Trustee.objects.first()  # TODO
        work.private = False

        if original:
            work.original = original
            work.protected = False
        else:
            author = json_work['author'].rsplit(maxsplit=1)
            work.author = models.Author.objects.only('pk').get(
                first_name=author[0], last_name=author[-1]
            )
            work.published = json_work['pub_year'] or ''
            work.licence = models.Licence.objects.first()  # TODO
            work.isbn = json_work['isbn'] or ''
            work.publisher = json_work['publisher'] or ''
            self.egw_id = json_work['book_id']

        work.full_clean()

        if not self.dry:
            work.save()
        self.work = work

    def load_segments(self, path):
        json_segments = []
        if isinstance(path, zipfile.ZipFile):
            regex = re.compile(r'{}\..*\.json'.format(self.egw_id))
            segments_files = [p for p in path.namelist() if re.match(regex, p)]
            for f in segments_files:
                json_segments.extend(json.load(path.open(f)))
        else:
            segments_files = path.glob('{}.*.json'.format(self.egw_id))
            for f in segments_files:
                with f.open() as file_segments:
                    json_segments.extend(json.load(file_segments))

        json_segments.sort(key=lambda segment: segment['puborder'])
        return json_segments

    def get_classes(self, segment):
        return list(set(segment['element_subtype'].split()))

    def build_model_segments(self, json_segments, osegments=None):
        model_segments = []
        position = 1
        old_page = 0
        prev_page_format = None
        if osegments:
            osegment_generator = iter(osegments)
            osegment = None

        for js in json_segments:
            page = js['refcode_2'].strip()
            page_smaller = page.isdigit() and old_page > int(page)
            self.tag = js['element_type']
            classes = self.get_classes(js)
            content = self.convert_content(js['content'], js['para_id'])
            if osegments:
                if position > js['puborder'] or page_smaller:
                    raise SortingError
                ms = None
                english_reference = False
                warn = True
                for translation in js['translations']:
                    if translation['lang'] == 'en':
                        # The first element
                        if osegment is None:
                            ms, osegment = self.get_next_translated_segment(
                                translation['para_id'], osegment_generator
                            )
                        else:
                            model_book_id, model_parag_id = osegment.key.split(
                                '.'
                            )
                            para_id = translation['para_id']
                            json_book_id, json_parag_id = para_id.split('.')
                            assert model_book_id == json_book_id
                            if model_parag_id == json_parag_id:
                                warn = self.add_content_to_last_segment(
                                    content, classes, model_segments
                                )
                            elif int(model_parag_id) < int(json_parag_id):
                                ms, osegment = self.get_next_translated_segment(
                                    translation['para_id'], osegment_generator
                                )
                            else:  # model_parag_id > json_parag_id
                                raise SortingError
                        english_reference = True
                        break
                if ms is None:
                    if not english_reference and model_segments:
                        warn = self.add_content_to_last_segment(
                            content, classes, model_segments
                        )
                    if warn:
                        print('\nWarning! This text is not included:')
                        pprint(js)
                    continue
            else:
                if position != js['puborder'] or page_smaller:
                    raise SortingError
                ms = models.OriginalSegment()
                ms.key = js['para_id']

            if page:
                if re.match(ROMAN_NUMERAL_PATTERN, page.upper()):
                    if prev_page_format != 'alphabetical':
                        page = page.upper()
                        prev_page_format = 'roman'
                elif page.isdigit():
                    prev_page_format = 'arabic'
                else:
                    page = page.lower()
                    prev_page_format = 'alphabetical'
            else:
                prev_page_format = None

            ms.position = position
            ms.page = page
            ms.tag = self.tag
            ms.classes = classes
            ms.content = content
            reference = js['refcode_short']
            if reference:
                ms.reference = reference
            else:
                ms.reference = f'{self.work.abbreviation} :{position}'
            ms.work = self.work

            # full_clean not possible here because tags and classes aren't
            # created yet

            model_segments.append(ms)
            position += 1
            if page.isdigit():
                old_page = int(page)

        return model_segments

    def get_next_translated_segment(self, para_id, osegment_generator):
        for osegment in osegment_generator:
            if osegment.key == para_id:
                ms = models.TranslatedSegment()
                ms.original = osegment
                return ms, osegment

    def add_content_to_last_segment(self, content, classes, segments):
        last_segment = segments[-1]
        warn = True
        if last_segment.tag == self.tag and last_segment.classes == classes:
            last_segment.content = '{} {}'.format(last_segment.content, content)
            warn = False
        return warn

    # Tags and classes

    def register_tags_and_classes(self, model_segments):
        for segment in model_segments:
            if self.verbosity >= 5:
                print(segment.reference, segment.key)
            self.register_tag(segment, segment.tag)
            self.register_classes(segment, segment.tag, segment.classes)
            self.register_inline_markup(segment)

            try:
                segment.full_clean()
            except (ValidationError, KeyError) as e:
                if not self.dry:
                    print(segment.reference, segment.key, segment.content)
                    raise e
                # Catch the error that the work cannot be null because
                # it isn't saved in dry run
                errors = e.message_dict.copy()
                work_err = errors.pop('work', None)
                msg = ['This field cannot be null.']
                if errors or work_err != msg:
                    raise e

    def register_tag(self, segment, name):
        try:
            tag = self.html_tags[name]
        except KeyError:
            tag, created = Tag.objects.get_or_create(name=name)
            self.html_tags[name] = tag
        self.perform_registration(tag.segments, segment)

    def register_classes(self, segment, tag, names):
        tag = self.html_tags[tag]
        for name in names:
            index = '{}_{}'.format(tag, name)
            try:
                cls = self.html_classes[index]
            except KeyError:
                cls, created = Class.objects.get_or_create(tag=tag, name=name)
                self.html_classes[index] = cls
            self.perform_registration(cls.segments, segment)

    def perform_registration(self, relation, segment):
        # Every segment can only be registered once
        try:
            relation.add(segment)
        except IntegrityError as e:
            msg = 'duplicate key value violates unique constraint'
            if msg not in str(e):
                raise

    def register_inline_markup(self, segment):
        soup = BeautifulSoup(segment.content, 'html.parser')

        for e in soup.descendants:
            if e.name is None:
                continue
            if e.name == segment.tag:
                # Raised because statistics assume that a tag is not inline
                # when the segment's tag has that value
                raise NotImplementedError(
                    'Inline tag equal to segment tag not supported.'
                )
            self.register_tag(segment, e.name)
            classes = e.get('class', [])
            self.register_classes(segment, e.name, classes)

    def check_tags_and_classes(self, model_segments):
        tags = Tag.objects.values_list('name', flat=True)
        reg_classes = Class.objects.values_list('tag__name', 'name')
        tag_msg = 'Tag "{}" not available!'
        class_msg = 'Class "{}" with tag "{}" not available!'
        for segment in model_segments:
            if segment.tag not in tags:
                print(tag_msg.format(segment.tag))
            for cls in segment.classes:
                if (segment.tag, cls) not in reg_classes:
                    print(class_msg.format(cls, segment.tag))
            soup = BeautifulSoup(segment.content, 'html.parser')
            for e in soup.descendants:
                if e.name is None:
                    continue
                if e.name not in tags:
                    print(tag_msg.format(e.name))
                classes = e.get('class', [])
                for cls in classes:
                    if (e.name, cls) not in reg_classes:
                        print(class_msg.format(cls, e.name))

    # Compare

    def find_different_segment_ids(self, original, translation, language):
        """
        Compares an original and a translation concerning the para_id.
        """
        work, tsegments = self.from_api(query=translation, language=language)
        osegments = iter(self.get_original_work(original).segments.all())
        para_id = next(osegments).key
        for ts in tsegments:
            for translation in ts['translations']:
                if not (
                    translation['lang'] == 'en'
                    and translation['para_id'] == para_id
                ):
                    print('mismatch', para_id, '!=', translation['para_id'])
            para_id = next(osegments).key

    def find_different_chapter_lengths(self, original, translation, language):
        """
        Compares an original and a translation concerning the number of
        segments in chapters.
        """
        work, tsegments = self.from_api(query=translation, language=language)
        osegments = iter(
            self.get_original_work(original).segments.filter(
                tag__startswith='h'
            )
        )
        for position, ts in enumerate(tsegments, start=1):
            if ts['element_type'].startswith('h'):
                try:
                    os = next(osegments)
                    print(
                        os.tag,
                        os.position,
                        ts['element_type'],
                        position,
                        'd',
                        os.position - position,
                    )
                except StopIteration:
                    print('-', '-', ts['element_type'], position, 'd', '-')
        for s in osegments:
            print(s.tag, s.position, '-', '-', 'd', '-')

    def compare_segments(self, book_1, book_2):
        b1 = {s['para_id']: s['content'] for s in book_1}
        b2 = {s['para_id']: s['content'] for s in book_2}
        self.compate_segment_in_other_book(book_1, b2)
        self.compate_segment_in_other_book(book_2, b1)

    def compate_segment_in_other_book(self, book, other_book):
        from difflib import ndiff

        count = 0
        for s in book:
            para_id = None
            for translation in s['translations']:
                if translation['lang'] == 'de':
                    para_id = translation['para_id']
            if not para_id:
                print('Nothing to compare for ', s['refcode_short'])
                continue
            if not s['content'] == other_book[para_id]:
                print(
                    '\n'.join(ndiff([s['content']], [other_book[para_id]])),
                    end='\n\n',
                )
                count += 1
                if count > self.max_mismatch:
                    break
