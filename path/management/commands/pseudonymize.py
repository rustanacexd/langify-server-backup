from random import choice

from allauth.account.models import EmailAddress
from factory import Faker

from base.constants import SYSTEM_USERS
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from ...factories import UserFactory
from ...models import User

KEEP_USERS = SYSTEM_USERS + ('admin',)

PERSONAL_FIELDS = {
    'public_id',
    'username',
    'password',
    'first_name',
    'last_name',
    'pseudonym',
    'email',
    'avatar',
    'address',
    'address_2',
    'zip_code',
    'city',
    'state',
    'country',
    'phone',
    'born',
    'is_verified',
    'description',
    'education',
    'experience',
    'show_full_name',
    'show_age',
    'show_country',
    'show_description',
    'show_education',
    'show_experience',
}

NON_PERSONAL_FIELDS = {
    'id',
    'name_display',
    'avatar_crop',
    'language',
    'is_staff',
    'is_active',
    'is_superuser',
    'subscribed_edits',
    'last_login',
    'date_joined',
}


class Command(BaseCommand):
    help = 'Pseudonymizes user profiles in the database.'

    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise ImproperlyConfigured(
                'This command is available in development only.'
            )

        assert (
            not PERSONAL_FIELDS & NON_PERSONAL_FIELDS
        ), 'Personal fields and non personal fields may not intersect.'
        fields = {
            f.name
            for f in User()._meta.get_fields()
            if not (f.many_to_many or f.one_to_many)
        }
        msg = 'The pseudonymisation lists seem to be outdated: {}.'
        assert PERSONAL_FIELDS | NON_PERSONAL_FIELDS == fields, msg.format(
            (PERSONAL_FIELDS | NON_PERSONAL_FIELDS) ^ fields
        )
        self.stdout.write('Pseudonymize User table...')
        for user in User.objects.all():
            if user.username in KEEP_USERS:
                if user.username == 'admin':
                    user.set_password('admin')
                    user.save_without_historical_record()
                continue
            while True:
                mock = UserFactory.build()
                for field in PERSONAL_FIELDS:
                    if field.startswith('show_'):
                        setattr(user, field, choice((True, False)))
                    elif getattr(user, field):
                        if field == 'password':
                            user.set_password('pw')
                        elif field == 'public_id':
                            user.set_public_id()
                        else:
                            setattr(user, field, getattr(mock, field))
                try:
                    user.save_without_historical_record()
                except IntegrityError:
                    # Duplicate key value violates unique constraint
                    continue
                break

        self.stdout.write('Pseudonymize EmailAddress table...')
        for email in EmailAddress.objects.select_related('user'):
            if email.user.username not in KEEP_USERS:
                if email.primary:
                    email.email = email.user.email
                else:
                    email.email = Faker('email').generate({})
                email.save_without_historical_record()

        self.stdout.write('Delete historical records...')
        User.history.all().delete()
        EmailAddress.history.all().delete()
        msg = (
            'Database pseudonymization completed. You can login with user '
            'and password "admin" or with other usernames and password "pw".'
        )
        self.stdout.write(self.style.SUCCESS(msg))
