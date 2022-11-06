import factory
from factory import Faker

from path.factories import UserFactory

from . import models


class DeveloperCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DeveloperComment

    content = Faker('paragraph')
    user = factory.SubFactory(UserFactory)


class PageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Page

    slug = Faker('slug')
    content = Faker('paragraph')
