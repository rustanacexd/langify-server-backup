import re

import regex

from django.db import transaction
from panta.models import OriginalWork, TranslatedWork

from .apis import EGWWritingsClient
from .constants import EMPTY_WORKS, EXISTING_WORKS, WORKS_WITH_YOUNGER_EDITION
from .models import OriginalSegmentSentenceRelation, OriginalSentence

TYPES = [t[0] for t in OriginalWork.types]


def check_existing_works():
    """
    Checks if the titles in EXISTING_WORKS exist in the database and are unique.

    Suggests other titles from the EGWWritings search if title was not found.
    """
    titles_in_db = tuple(
        OriginalWork.objects.order_by('title').values_list('title', flat=True)
    )
    count = len(titles_in_db)
    client = None

    for titles in EXISTING_WORKS.values():
        for t in titles:
            if isinstance(t, str):
                title = t
            else:
                title = t[0]
            if title in titles_in_db:
                if t == title:
                    next_index = titles_in_db.index(t) + 1
                    if next_index < count and t == titles_in_db[next_index]:
                        print(0, f'"{t}" has more than one match!')
                continue
            if not client:
                client = EGWWritingsClient()
            data = client.get('search/suggestions/', query=title, lang='en')
            if data:
                if title != data[0]['title']:
                    print(1, f'"{title}" doesn\'t match "{data[0]["title"]}"')
                    if len(data) > 1:
                        print(2, f'or "{data[1]["title"]}"')
            else:
                print(0, f'No match for "{title}"')


class OpenTranslations:
    """
    A class to generate translated works with segments.

    Options:
    - filter by types: str (OriginalWork.types)
    - specify titles: tuple/list of strings or pair of title and abbreviation
    - existing: open works that are listed in EXISTING_WORKS
    - protect: set TranslatedWork.protected = True
    - verbosity: 2 prints warning when book not found in the database
    """

    def __init__(
        self,
        language,
        types=TYPES,
        titles=None,
        existing=False,
        protect=False,
        verbosity=1,
    ):
        self.language = language
        self.types = types
        self.titles = titles
        self.verbosity = verbosity
        self.skip_titles = EMPTY_WORKS + WORKS_WITH_YOUNGER_EDITION
        if not existing:
            self.skip_titles += EXISTING_WORKS.get(language, ())
        self.protect = protect
        self.originals = (
            OriginalWork.objects.order_by('pk')
            .exclude(translations__language=language)
            .distinct()
        )

    def create(self):
        """
        Adds translated works with segments for given language and types.
        """
        self.check_title_is_unique(EMPTY_WORKS)
        self.check_title_is_unique(WORKS_WITH_YOUNGER_EDITION)
        self.check_title_is_unique(EXISTING_WORKS.get(self.language, ()))

        books_count = self.create_books()
        periodicals_count = self.create_works_of_type('periodical')
        manuscripts_count = self.create_works_of_type('manuscript')

        print(
            f'Opened {books_count} books, {periodicals_count} periodicals and '
            f'{manuscripts_count} manuscripts for translation.'
        )

    def get_lookups(self, title):
        if isinstance(title, str):
            return {'title': title}
        else:
            return {'title': title[0], 'abbreviation': title[1]}

    def check_title_is_unique(self, title_list):
        for title in title_list:
            lookups = self.get_lookups(title)
            count = OriginalWork.objects.filter(**lookups).count()
            assert count == 1, (
                f'There is not exactly one book "{title}" available but '
                f'{count}.'
            )

    def create_translation(self, original: OriginalWork):
        TranslatedWork.objects.create(
            title=original.title,
            subtitle=original.subtitle,
            abbreviation=original.abbreviation,
            type=original.type,
            description=original.description,
            language=self.language,
            trustee_id=original.trustee_id,
            private=original.private,
            original=original,
            protected=self.protect,
        )

    def create_books(self) -> int:
        type = 'book'
        books_count = 0
        if type in self.types:
            # Do it this way to have the order of the White Estate
            client = EGWWritingsClient()
            books = client.get(
                'content/books/shortlist', lang='en', type='book'
            )
            for book in books:
                title = book['title']
                if title not in self.skip_titles:
                    try:
                        # It is safe to just use the first one because existing
                        # ones are excluded.
                        # (So, if a title exists two times, the second work is
                        # opened the second time the title comes up.)
                        work = self.originals.filter(title=title, type=type)[0]
                    except IndexError:
                        if self.verbosity >= 2:
                            works = OriginalWork.objects.filter(title=title)
                            if not works.exists():
                                print(
                                    f'Warning: "{title}" not found in the '
                                    'database.'
                                )
                        # Translated work should exist already
                        continue
                    # Skip books with not unique title
                    pair = (title, work.abbreviation)
                    if pair in self.skip_titles:
                        continue
                    # Skip books not specified
                    titles = self.titles
                    if titles and not (title in titles or pair in titles):
                        continue
                    self.create_translation(work)
                    books_count += 1
        return books_count

    def create_works_of_type(self, type: str) -> int:
        works_count = 0
        if type in self.types:
            works = self.originals.filter(type=type)
        else:
            works = self.originals.none()
        for work in works:
            # Skip works not specified
            titles = self.titles
            pair = (work.title, work.abbreviation)
            if titles and not (work.title in titles or pair in titles):
                continue
            self.create_translation(work)
            works_count += 1
        return works_count


class TextToSentences:
    """
    Splits texts into sentences. Made for English EGW documents.
    """

    punctuation = r'[\.:!?]'
    opening_quotation_marks = '"\'”“’‘„‚«»›‹'
    closing_quotation_marks = '"\'”“’‘«»›‹'

    # Removed ¡ and ¿ because they got lost and we don't need them in English
    # texts
    # The basic regex comes from https://stackoverflow.com/a/25736515
    split_regex = regex.compile(
        r"""
        ((?<=[^\p{{Lu}}]           # Find a not capital letter
        {p})                       # ending with a punctuation
        |(?<=B\.C\.)               # or B.C. (includes a warning)
        |(?<=R\.V\.)               # or R.V./R. V. (assumes that this is always
        |(?<=R\.\ V\.))            # at the end of a sentence)
        (</[emspan]{{2,4}}>)?      # optional closing tags </em>, </span>
        ([{cqm})\]])*              # optional quotation marks/parentheses
        (\s+|—|\s*<[a-z ="]+/?>)   # followed by space, m-dash or (opening) tag
        ([{oqm}(\[])*              # optional quotation marks/parentheses
        (<span\ clas[^>]+>)?       # optional opening tag <span>
        (?=\p{{Lu}})               # followed by a capital (not consuming)
        """.format(
            p=punctuation,
            oqm=opening_quotation_marks,
            cqm=closing_quotation_marks,
        ),
        re.X,
    )

    not_splitting = {
        # Abbreviations
        'art.': 'article',
        'dr.': 'doctor',
        'mr.': 'mister',
        'brn.': 'brethren',
        'bro.': 'brother',
        'mrs.': 'mistress',
        'ms.': 'miss',
        'jr.': 'junior',
        'sr.': 'senior, sister, sir',
        'i.e.': 'that is',
        'e.g.': 'for example',
        'pp.': 'pages',
        'rev.': 'Reverend',
        'st.': 'Saint',
        'th.': '[first name]',
        'vol.': 'volume',
        'vols.': 'volumes',
        'vs.': 'versus',
    }
    probably_splitting = {
        r'[^\.:!?]\.\.\.': 'ellipsis',
        r'b\.c\.': 'before Christ',
        r'etc\.': 'et cetera',
    }

    # Check that the sentence consists of the abbreviation only or has a non
    # word character in front
    not_splitting_regex = r'^(.*\W)?({})(</[emspan]*>)?$'
    not_splitting = re.compile(
        not_splitting_regex.format('|'.join(not_splitting)), re.I
    )
    probably_splitting = re.compile(
        not_splitting_regex.format(r'|'.join(probably_splitting)), re.I
    )

    page_break = re.compile(r'</span>(.{0,3})<span class="[a-z0-9_\- ]+">')

    span_regex = re.compile(
        r'^\[?(<span class="[a-z0-9_\- ]+">)(?P<text>.+)(</span>)'
        r'(?P<punctuation>[\.!?]?)\]?$'
    )

    citation_regex = re.compile(
        r'((?P<text>.+)(?P<separator>[— -]))?'
        r'(?P<citation><span class="egwlink [^>]+>[^<]+</span>'
        r'|<em>[^<]+</em>[chbpvol0-9 \.,]*)'
        r'(?P<punctuation>{p}?)$'.format(
            p=punctuation, cqm=closing_quotation_marks
        )
    )
    citation_connectors = ('to', 'and', 'in', 'See', 'See also', ',')

    inline_heading_regex = re.compile(
        r'^(?P<heading><(strong|em)>.+</(strong|em)>[{cqm}]?)(\.?(—|-)|:)'
        r'(?P<paragraph>.+)$'.format(cqm=closing_quotation_marks)
    )

    parentheses_regex = re.compile(
        r'^(?P<p1>[(\[]?)(<span class="non-egw-comment">)?(?P<text>[^()\[\]<]+)'
        r'(</span>)?(?P<p2>[)\]]?)$'
    )

    quotation_mark_regex = re.compile(
        r'^(?P<m1>[{oqm}]?)(?P<text>[^{oqm}{cqm}]+)(?P<m2>[{cqm}]?)'
        r'(?P<punctuation>{p}?)(?P<m3>[{cqm}]?)$'.format(
            p=punctuation,
            oqm=opening_quotation_marks,
            cqm=closing_quotation_marks,
        )
    )

    footnote_regex = regex.compile(
        r'(?P<s1>.+{p}[)\]{cqm}]*)?(?P<s2><sup .+</sup>)'
        r'(\s(?P<s3>[(\[{oqm}]*\p{{Lu}}.+)?)?'.format(
            p=punctuation,
            oqm=opening_quotation_marks,
            cqm=closing_quotation_marks,
        )
    )

    print_sentence = None

    def split(self, text):
        """
        Splits a given text into sentences and returns them as list.

        Is made for English EGW documents.
        """
        # Positive lookbehind assertions require a pattern with a fixed length.
        # Therefore, it is difficult to split sentences with following
        # punctuation. And we probably don't have to support it.
        for p in ('!!', '??', '!?', '?!'):
            assert p not in text, 'Found not supported "{}" in "{}".'.format(
                p, text
            )

        text = text.strip()
        sentences = []
        sentence = ''
        separator = ''

        # Remove foreword spans, etc.
        match = re.match(self.span_regex, text)
        if match:
            text = match.group('text') + match.group('punctuation')

        # Extract little headings
        match = re.match(self.inline_heading_regex, text)
        if match:
            sentences.append(match.group('heading'))
            text = match.group('paragraph')

        # Remove page breaks
        text = self.remove_page_breaks(text)

        # Regular split
        # Group split list into sentences
        sentence_lists = [['', '']]
        for i, group in enumerate(regex.split(self.split_regex, text), start=2):
            if i % 7 == 0:
                sentence_lists.append([])
            sentence_lists[-1].append(group)
        sentence_lists[-1].extend(['', '', '', ''])

        for pre, otag, s, _x, ctag, post, next_separator in sentence_lists:
            next_sentence = None
            if not s:
                continue

            # Add quotation marks, parentheses and HTML tags
            s = (pre or '') + (otag or '') + s + (ctag or '') + (post or '')

            # Print sentence
            if self.print_sentence:
                print(
                    'Warning: A sentence is split with an abbreviation or '
                    'ellipsis at the end but we are not sure if the sentence '
                    'ends here:'
                )
                print('   ', self.print_sentence)
                # Print the next sentence also to get the context
                print('   ', s)
                self.print_sentence = None

            # Join a sentence that was separated because of an abbreviation
            if sentence:
                sentence += separator + s
            else:
                sentence = s
            separator = next_separator

            # Remove citation
            match = re.match(self.citation_regex, sentence)
            if match:
                extracted = match.group('text')
                # Don't include sentences that are a mere reference
                if not extracted:
                    sentence = ''
                    continue
                # Remove citation part when at the end of a sentence
                if match.group('citation').startswith('<span'):
                    if not extracted.endswith(self.citation_connectors):
                        sentence = extracted
                        stripped = sentence.rstrip(self.closing_quotation_marks)
                        endings = ('.', ';', '!', '?', ']')
                        if not stripped.endswith(endings):
                            sentence += match.group('punctuation')
                elif match.group('separator') == '—':
                    sentence = extracted
                    next_sentence = match.group('citation')

            # Separate footnotes
            completed, sentence = self.handle_footnote(sentence)
            sentences.extend(completed)

            # Remove arounds
            sentence = self.remove_arounds(sentence)

            # Handle abbreviations
            if sentence and not self.ends_with_abbreviation(sentence):
                # Remove ellipsis
                if sentence.endswith('...'):
                    sentence = sentence[:-3].strip()
                sentences.append(sentence)
                sentence = ''
                if next_sentence:
                    sentences.append(next_sentence)

        return sentences

    def remove_page_breaks(self, text):
        parts = re.split(self.page_break, text)
        if len(parts) == 3:
            return ''.join(parts)
        return text

    def handle_footnote(self, sentence):
        match = sentence and regex.match(self.footnote_regex, sentence)
        if not match:
            return [], sentence
        completed, s = self.handle_footnote(match.group('s3') or '')
        if self.ends_with_abbreviation(match.group('s1') or ''):
            if completed:
                completed[0] = '{}{} {}'.format(
                    match.group('s1'), match.group('s2'), completed[0]
                )
                sentence = s
        else:
            completed.insert(0, match.group('s2'))
            if match.group('s1'):
                completed.insert(0, self.remove_arounds(match.group('s1')))
            sentence = s
        return completed, sentence

    def ends_with_abbreviation(self, sentence):
        if not sentence.endswith('.'):
            return False

        # Sentence is not finished
        if re.search(self.not_splitting, sentence):
            return True

        # Sentence ends with B.C., etc.
        if re.search(self.probably_splitting, sentence):
            # Print the sentence in the next iteration to prevent printing
            # the message at the end of a text
            self.print_sentence = sentence

        # "Oh!", "Hi!", "No?" are valid sentences and don't need a check
        if len(sentence) < 5:
            print(
                'Warning: "{}" is a very short sentence. Please check '
                'if it is an abbreviation instead.'.format(sentence)
            )

    def remove_arounds(self, sentence):
        # Remove parentheses and non-egw-comment
        # This does not check if parentheses match each other
        match = re.match(self.parentheses_regex, sentence)
        if match and (match.group('p1') or match.group('p2')):
            sentence = match.group('text')

        # Remove quotation marks
        # This does not check if the two quotation marks match
        match = re.match(self.quotation_mark_regex, sentence)
        if match and (
            match.group('m1') or match.group('m2') or match.group('m3')
        ):
            sentence = match.group('text') + match.group('punctuation')
        return sentence

    @transaction.atomic
    def process_works(self, works, verbosity=1, save=True):
        """
        Takes the segments of given works and saves new sentences and relations.
        """
        for work in works:
            print('Processing "{}"'.format(work))
            for seg in work.segments.all():
                self.print_sentence = None
                if verbosity >= 2:
                    print('Processing', seg)
                for i, sentence in enumerate(self.split(seg.content), start=1):
                    if verbosity >= 3 and '<' in sentence:
                        print(sentence, '\n')
                    if not save:
                        continue
                    sentence, created = OriginalSentence.objects.get_or_create(
                        content=sentence
                    )
                    OriginalSegmentSentenceRelation.objects.get_or_create(
                        segment=seg, sentence=sentence, number=i
                    )
                    sentence.count = sentence.segments.count()
                    sentence.save()

    def find_changes(self, works):
        """
        Informs if the generated sentences are still up-to-date for given works.

        This is practical if you changed something in this class and you want
        to be sure that you didn't accidentally change the behaviour.
        """
        for work in works:
            print('Checking "{}"'.format(work))
            for segment in work.segments.prefetch_related('sentences'):
                old_sentences = [s.content for s in segment.sentences.all()]
                new_sentences = self.split(segment.content)

                def print_message(subject, sentence):
                    print(
                        '{} found in {}:\n{}\n'.format(
                            subject,
                            segment.reference or segment.position,
                            sentence,
                        )
                    )

                # Check what should be added
                for s in new_sentences:
                    if s not in old_sentences:
                        sentence_exists = OriginalSentence.objects.filter(
                            content=s
                        ).exists()
                        if sentence_exists:
                            print_message('New relation', s)
                        else:
                            print_message('New sentence', s)
                # Check what should be removed
                for s in old_sentences:
                    if s not in new_sentences:
                        print_message('Stale relation', s)

    def delete_unrelated_sentences(self):
        print(OriginalSentence.objects.filter(segments=None).delete())
