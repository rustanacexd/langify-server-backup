from io import BytesIO
from random import choice, randint

import factory
import PIL
from allauth.account.models import EmailAddress
from factory import Faker

from base.constants import LANGUAGES
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile

from . import models

locale = 'en_US'


def create_image(width, height, format='JPEG'):
    img = PIL.Image.new('RGB', (width, height), 'green')
    # https://stackoverflow.com/a/4544525
    img_io = BytesIO()
    img.save(img_io, format=format)
    return ContentFile(img_io.getvalue())


class LocaleFactory(factory.django.DjangoModelFactory):
    def __init__(self, locale='en_US', *args, **kwargs):
        self.locale = locale
        super(LocaleFactory, self).__init__(*args, **kwargs)


class UserFactory(LocaleFactory):
    class Meta:
        model = models.User

    username = Faker('user_name', locale=locale)
    email = Faker('email', locale=locale)
    first_name = Faker('first_name', locale=locale)
    last_name = Faker('last_name', locale=locale)
    is_active = True
    password = factory.PostGenerationMethodCall('set_password', 'pw')

    @factory.post_generation
    def privileges(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.privileges.set(extracted)

    @factory.post_generation
    def create_avatar(self, create, extracted, **kwargs):
        format = 'JPEG'
        if isinstance(extracted, tuple):
            size = extracted
        elif isinstance(extracted, dict):
            format = extracted.get('format', format)
            size = (extracted['width'], extracted['height'])
        elif not extracted:
            return
        else:
            raise ValueError('Tuple or dict required')

        avatar = create_image(*size, format=format)
        self.avatar.save('some_name.jpg', content=avatar, save=False)

    @factory.post_generation
    def all_permissions(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.user_permissions = Permission.objects.all()

    class Params:
        admin = factory.Trait(is_staff=True, is_superuser=True)


class PrivilegeFactory(LocaleFactory):
    class Meta:
        model = models.Privilege

    name = choice(models.PRIVILEGES)[0]
    language = choice([l[0] for l in settings.LANGUAGES if len(l[0]) <= 2])
    trustee = factory.SubFactory('panta.factories.TrusteeFactory')


class ReputationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Reputation

    score = randint(0, 100000)
    language = choice(LANGUAGES)[0]
    user = factory.SubFactory(UserFactory)


class EmailAddressFactory(LocaleFactory):
    class Meta:
        model = EmailAddress

    email = Faker('email', locale=locale)
    user = factory.SubFactory(UserFactory)
