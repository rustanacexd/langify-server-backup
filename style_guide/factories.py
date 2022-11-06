import factory
from factory import Faker

from django.conf import settings
from path.factories import UserFactory

from . import models

locale = 'en_US'
LANGUAGE_CHOICES = [l[0] for l in settings.LANGUAGES if len(l[0]) <= 2]


class LocaleFactory(factory.django.DjangoModelFactory):
    def __init__(self, locale='en_US', *args, **kwargs):
        self.locale = locale
        super(LocaleFactory, self).__init__(*args, **kwargs)


class StyleGuideFactory(LocaleFactory):
    class Meta:
        model = models.StyleGuide
        django_get_or_create = ('language',)

    title = Faker('text', locale=locale, max_nb_chars=50)
    content = Faker('paragraph', locale=locale)
    language = factory.Iterator(LANGUAGE_CHOICES)


class TagFactory(LocaleFactory):
    class Meta:
        model = models.Tag

    name = Faker('text', locale=locale, max_nb_chars=40)
    slug = Faker('slug', locale=locale)


class IssueFactory(LocaleFactory):
    class Meta:
        model = models.Issue

    title = Faker('text', locale=locale, max_nb_chars=150)
    content = Faker('paragraph', locale=locale)
    style_guide = factory.SubFactory(StyleGuideFactory)
    user = factory.SubFactory(UserFactory)


class IssueCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.IssueComment

    content = Faker('paragraph')
    user = factory.SubFactory(UserFactory)
    issue = factory.SubFactory(IssueFactory)


class IssueReactionFactory(IssueCommentFactory):
    class Meta:
        model = models.IssueReaction

    content = Faker('text', max_nb_chars=5)
