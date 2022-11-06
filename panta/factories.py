from random import choice, randint

import factory
from factory import Faker

from base.constants import ADDITIONAL_LANGUAGES, LANGUAGES, ROLES
from django.db.models import Max
from panta.constants import HEADINGS, IMPORTANT_HEADINGS, PARAGRAPHS
from path.factories import UserFactory

from . import models

locale = 'en_US'


class LocaleFactory(factory.django.DjangoModelFactory):
    def __init__(self, locale='en_US', *args, **kwargs):
        self.locale = locale
        super(LocaleFactory, self).__init__(*args, **kwargs)


class TrusteeFactory(LocaleFactory):
    class Meta:
        model = models.Trustee

    name = Faker('company', locale=locale)
    description = Faker('text', locale=locale)
    code = factory.Sequence(lambda n: 't{}'.format(n))


class AuthorFactory(LocaleFactory):
    class Meta:
        model = models.Author

    first_name = Faker('first_name', locale=locale)
    last_name = Faker('last_name', locale=locale)
    suffix = Faker('suffix', locale=locale)
    born = Faker('date_between', start_date='-1000y', end_date='-15y')
    bio = Faker('text', locale=locale)


class LicenceFactory(LocaleFactory):
    class Meta:
        model = models.Licence

    title = Faker('text', locale=locale, max_nb_chars=100)
    description = Faker('text', locale=locale)


class TagFactory(LocaleFactory):
    class Meta:
        model = models.Tag

    name = Faker('slug', locale=locale)
    slug = Faker('slug', locale=locale)


class AbstractWorkFactory(LocaleFactory):
    title = Faker('text', locale=locale, max_nb_chars=50)
    subtitle = Faker('text', locale=locale, max_nb_chars=100)
    abbreviation = factory.Sequence(lambda n: 'a{}'.format(n))
    type = 'book'
    language = locale[:2]
    trustee = factory.SubFactory(TrusteeFactory)
    private = False


class OriginalWorkFactory(AbstractWorkFactory):
    class Meta:
        model = models.OriginalWork

    author = factory.SubFactory(AuthorFactory)
    published = randint(1800, 2019)
    licence = factory.SubFactory(LicenceFactory)

    @factory.post_generation
    def segments(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        segments = []
        next_heading = 0

        def add_segment(tag):
            if tag == 'p':
                content = Faker(
                    'paragraph', locale=locale, nb_sentences=randint(1, 7)
                )
            else:
                content = Faker(
                    'sentence', locale=locale, nb_words=randint(1, 10)
                )
            position = len(segments) + 1
            segments.append(
                OriginalSegmentFactory.build(
                    position=position, work=self, tag=tag, content=content
                )
            )

        if isinstance(extracted, int):
            for i in range(extracted):
                if i == next_heading:
                    tag = choice(IMPORTANT_HEADINGS)
                    next_heading += randint(1, 60)
                else:
                    tag = 'p'
                add_segment(tag)
        else:
            for tag in extracted.split(' '):
                add_segment(tag)

        models.OriginalSegment.objects.bulk_create(segments)


class TranslatedWorkFactory(AbstractWorkFactory):
    class Meta:
        model = models.TranslatedWork

    original: models.OriginalWork = factory.SubFactory(OriginalWorkFactory)
    protected = False


class OriginalSegmentFactory(LocaleFactory):
    class Meta:
        model = models.OriginalSegment

    work: models.OriginalWork = factory.SubFactory(OriginalWorkFactory)
    tag = choice(HEADINGS + PARAGRAPHS)
    content = Faker('paragraph', locale=locale)

    @factory.lazy_attribute
    def position(self):
        segments = models.OriginalSegment.objects.filter(work_id=self.work.pk)
        return segments.aggregate(Max('position'))['position__max'] or 0 + 1

    @factory.lazy_attribute
    def reference(self):
        return f'{self.work.abbreviation} :{self.position}'


class TranslatedSegmentFactory(LocaleFactory):
    class Meta:
        model = models.TranslatedSegment

    position = factory.LazyAttribute(lambda obj: obj.original.position)
    work = factory.SubFactory(TranslatedWorkFactory)
    original = factory.SubFactory(OriginalSegmentFactory)
    tag = choice(HEADINGS + PARAGRAPHS)
    content = Faker('paragraph', locale=locale)

    @factory.lazy_attribute
    def reference(self):
        return self.original.reference


class BaseTranslatorFactory(LocaleFactory):
    class Meta:
        model = models.BaseTranslator

    name = Faker('company', locale=locale)
    type = choice(('ai', 'hb', 'tm'))


class BaseTranslationFactory(LocaleFactory):
    class Meta:
        model = models.BaseTranslation

    translator = factory.SubFactory(BaseTranslatorFactory)
    language = choice(LANGUAGES)[0]


class BaseTranslationSegmentFactory(LocaleFactory):
    class Meta:
        model = models.BaseTranslationSegment

    original = factory.SubFactory(OriginalSegmentFactory)
    translation = factory.SubFactory(BaseTranslationFactory)
    content = Faker('paragraph', locale=locale)


class SegmentDraftFactory(LocaleFactory):
    class Meta:
        model = models.SegmentDraft

    position = factory.LazyAttribute(lambda obj: obj.segment.position)
    segment = factory.SubFactory(TranslatedSegmentFactory)
    work = factory.LazyAttribute(lambda obj: obj.segment.work)
    content = Faker('paragraph', locale=locale)
    owner = factory.SubFactory(UserFactory)


class VoteFactory(LocaleFactory):
    class Meta:
        model = models.Vote

    user = factory.SubFactory(UserFactory)
    role = choice([r[0] for r in ROLES])
    value = choice((-2, -1, 1, 2))


class SegmentCommentFactory(LocaleFactory):
    class Meta:
        model = models.SegmentComment

    work = factory.SubFactory(TranslatedWorkFactory)
    position = 1
    content = Faker('paragraph', locale=locale)
    user = factory.SubFactory(UserFactory)


class ReferenceFactory(LocaleFactory):
    class Meta:
        model = models.Reference

    title = Faker('text', locale=locale, max_nb_chars=100)
    type = Faker('text', locale=locale, max_nb_chars=20)
    abbreviation = Faker('text', locale=locale, max_nb_chars=15)
    author = Faker('text', locale=locale, max_nb_chars=100)
    published = Faker('text', locale=locale, max_nb_chars=11)
    language = choice(LANGUAGES)[0]


def get_faker_supported_languages(exclude=set()):
    supported = {
        'ar',
        'bg',
        'bs',
        'cs',
        'de',
        'dk',
        'el',
        'en',
        'es',
        'et',
        'fa',
        'fi',
        'fr',
        'he',
        'hi',
        'hr',
        'hu',
        'id',
        'it',
        'ja',
        'ka',
        'ko',
        'la',
        'lb',
        'lt',
        'lv',
        'mt',
        'ne',
        'ln',
        'no',
        'pl',
        'pt',
        'ro',
        'ru',
        'sk',
        'sl',
        'sv',
        'th',
        'tr',
        'tw',
        'uk',
        'zh',
    }
    return [l[0] for l in LANGUAGES if l[0] in supported - exclude]


def create_work(
    segments=500,
    translations=3,
    languages=None,
    completeness=(0, 100),
    additional_languages=True,
    random=True,
    **kwargs,
):
    """
    Create a work with translations.

    `segments` of the work
    `translations` as total count
    `languages` to be used (randomly by default)
    `completeness` of the translations as min, max in %
    more key word arguments to customize the original work factory
    all optional
    """
    orig_work = OriginalWorkFactory(segments=segments, **kwargs)
    if languages is None:
        if additional_languages:
            languages = get_faker_supported_languages()
        else:
            languages = get_faker_supported_languages(
                exclude={l[0] for l in ADDITIONAL_LANGUAGES}.union({'en'})
            )

    trans_works = []
    if translations:
        steps = (completeness[1] - completeness[0]) / translations
        if isinstance(segments, str):
            segments = len(segments.split(' '))
        segments_add = steps * segments / 100
        translate_until = segments * completeness[0] / 100

        for i in range(translations):
            trans_work = TranslatedWorkFactory(
                language=random and choice(languages) or languages[i],
                trustee=orig_work.trustee,
                original=orig_work,
            )
            segments = trans_work.segments.all().only('pk', 'content', 'work')
            for n, segment in enumerate(segments, start=1):
                if n > translate_until:
                    break
                content_factory = Faker(
                    'paragraph',
                    locale=trans_work.language,
                    nb_sentences=randint(1, 10),
                )
                segment.content = content_factory.generate({})
                segment.save()
            translate_until += segments_add
            trans_works.append(trans_work)

    return dict(original=orig_work, translations=trans_works)
