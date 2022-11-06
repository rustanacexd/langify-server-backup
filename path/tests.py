import datetime
import json
import sys
from collections import OrderedDict
from copy import deepcopy
from io import BytesIO
from unittest import skipIf
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from djangorestframework_camel_case.util import camel_to_underscore, camelize

from base.constants import ACTIVE_LANGUAGES, ADDITIONAL_LANGUAGES, PERMISSIONS
from base.serializers import UserFieldSerializer
from base.tests import APITests
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, tag  # noqa: F401
from django.urls import reverse
from django.utils import timezone
from misc.apis import MailjetClient
from misc.factories import DeveloperCommentFactory, PageFactory
from panta.factories import (
    AuthorFactory,
    LicenceFactory,
    OriginalSegmentFactory,
    OriginalWorkFactory,
    ReferenceFactory,
    SegmentCommentFactory,
    SegmentDraftFactory,
    TranslatedSegmentFactory,
    TranslatedWorkFactory,
    TrusteeFactory,
    create_work,
)
from panta.models import TranslatedSegment, TranslatedWork

from . import factories, models, validators
from .adapter import RestAdapter
from .api.serializers import (
    CommunityUserProfileSerializer,
    CountrySerializer,
    TransactionalPasswordResetForm,
    get_permissions_serializer,
)


class UserTests:
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory(username='ellen', first_name='Ellen')
        cls._user = cls.user


class ValidatorTests(SimpleTestCase):
    def test_html_free(self):
        self.assertRaisesMessage(
            ValidationError,
            '"=" is not allowed in this field. Please remove it.',
            validators.html_free,
            'This is not = to this.',
        )


class UserModelTests(UserTests, APITests):
    avatar_path = r'^/media/users/\d{4}/avatar_[a-zA-Z0-9]{7}\.jpg$'
    thumbnail_path = (
        r'/media/cache/images/users/\d{{4}}/avatar_[a-zA-Z0-9]{{7}}/'
        '{size}x{size}.jpg'
    )

    def setUp(self):
        self.user = deepcopy(self._user)

    def test_roles(self):
        self.user.reputations.all().delete()
        self.assertEqual(self.user.roles, [])
        models.Reputation.objects.bulk_create(
            (
                models.Reputation(user=self.user, score=1, language='de'),
                models.Reputation(user=self.user, score=10, language='tr'),
                models.Reputation(user=self.user, score=1000, language='es'),
                models.Reputation(
                    user=self.user, score=1_000_001, language='fr'
                ),
            )
        )
        self.assertEqual(self.user.roles, [])
        create_work(2, 4, ('de', 'es', 'fr', 'tr'), random=False)
        segments = tuple(
            TranslatedSegment.objects.all().order_by('work__language')
        )
        kw = {'history_user': self.user, 'save': False}
        history_objects = [
            segments[2].add_to_history(relative_id=90, **kw),
            segments[4].add_to_history(relative_id=90, save=False),
        ]
        for i, s in enumerate(segments[:-1]):
            s.add_to_history(relative_id=i, add_to=history_objects, **kw)
        TranslatedSegment.history.bulk_create(history_objects)
        self.assertEqual(
            self.user.roles,
            [
                OrderedDict(
                    (
                        ('language', 'Spanish'),
                        ('role', 'reviewer'),
                        ('edits', 2),
                    )
                ),
                OrderedDict(
                    (('language', 'French'), ('role', 'trustee'), ('edits', 2))
                ),
                OrderedDict(
                    (
                        ('language', 'Turkish'),
                        ('role', 'translator'),
                        ('edits', 1),
                    )
                ),
            ],
        )

    def test_name_of_inactiv_user(self):
        self.user.is_active = False
        self.assertEqual(self.user.name, '(deleted user)')
        self.user.is_active = True

    def test_avatar_create_600x600(self):
        user = factories.UserFactory(create_avatar=(600, 600))
        self.assertRegex(user.avatar.url, self.avatar_path)
        self.assertEqual(user.avatar.width, 600)
        self.assertEqual(user.avatar.height, 600)

    def test_avatar_create_800x40(self):
        user = factories.UserFactory(create_avatar=(800, 40))
        self.assertRegex(user.avatar.url, self.avatar_path)
        self.assertEqual(user.avatar.width, 800)
        self.assertEqual(user.avatar.height, 40)

    def test_avatar_create_resize(self):
        user = factories.UserFactory(create_avatar=(800, 1200))
        self.assertRegex(user.avatar.url, self.avatar_path)
        self.assertEqual(user.avatar.width, 600)
        self.assertEqual(user.avatar.height, 900)

    def test_avatar_change_format(self):
        avatar = factories.create_image(40, 40, format='GIF')
        self.user.avatar.save('some_name.jpg', content=avatar)
        self.assertRegex(self.user.avatar.url, self.avatar_path)
        self.assertEqual(self.user.avatar.width, 40)
        self.assertEqual(self.user.avatar.height, 40)

    def test_thumbnail_60(self):
        avatar = factories.create_image(800, 600)
        self.user.avatar.save('some_name.jpg', content=avatar)
        self.assertRegex(
            self.user.avatar_60.url, self.thumbnail_path.format(size=60)
        )
        self.assertEqual(self.user.avatar_60.width, 60)
        self.assertEqual(self.user.avatar_60.height, 60)

    def test_thumbnail_300_no_upscale(self):
        avatar = factories.create_image(50, 1200)
        self.user.avatar.save('some_name.jpg', content=avatar)
        self.assertRegex(
            self.user.avatar_300.url, self.thumbnail_path.format(size=300)
        )
        self.assertEqual(self.user.avatar_300.width, 50)
        self.assertEqual(self.user.avatar_300.height, 300)

    def test_thumbnail_without_avatar(self):
        avatar = factories.create_image(100, 100)
        self.user.avatar.save('some_name.jpg', content=avatar)
        self.user.avatar.delete()
        self.assertIsNone(self.user.avatar_60.name)

    def test_reset_of_custom_crop(self):
        avatar = factories.create_image(100, 100)
        user = factories.UserFactory(avatar_crop={'x1': 10, 'y1': 20})
        user.first_name = 'Update'
        user.full_clean()
        user.save()
        user.refresh_from_db()

        # Crop information should not change if avatar stays the same
        self.assertEqual(user.avatar_crop, {'x1': 10, 'y1': 20})

        # Avatar changes
        user.avatar.save('some_name.jpg', content=avatar)
        user.full_clean()
        self.assertEqual(user.avatar_crop, {})
        avatar = factories.create_image(500, 100)

        # Avatar and crop changes
        user.avatar_crop = {'custom': True}
        user.avatar.save('some_name.jpg', content=avatar)
        user.full_clean()
        self.assertEqual(user.avatar_crop, {'custom': True})

    # TODO:
    # Test avatar frame removal
    # Test smart cropping

    def test_has_required_reputation(self):
        work = TranslatedWork(language='de')
        self.assertTrue(
            self.user.has_required_reputation('add_translation', work)
        )
        self.assertFalse(
            self.user.has_required_reputation('approve_translation', work)
        )
        # Reputation does not exit
        # The workaround creates needed reputations
        return
        work.language = ADDITIONAL_LANGUAGES[0][0]
        self.assertFalse(
            self.user.has_required_reputation('add_translation', work)
        )

    def test_check_perms_no_reputations(self):
        # The workaround creates needed reputations
        self.user.check_perms(TranslatedWork(language='en'), 'add_comment')
        return

        self.assertRaisesMessage(
            PermissionDenied,
            'A reputation of 3 is required for the privilege "add_comment".',
            self.user.check_perms,
            TranslatedWork(language='en'),
            'add_comment',
        )

    def test_check_perms_has_perm(self):
        models.Reputation.objects.create(
            score=100, language='en', user=self.user
        )
        self.assertIsNone(
            self.user.check_perms(TranslatedWork(language='en'), 'add_comment')
        )

    def test_check_perms_has_no_perm(self):
        models.Reputation.objects.create(score=2, language='en', user=self.user)
        self.assertRaisesMessage(
            PermissionDenied,
            'A reputation of 3 is required for the privilege "add_comment".',
            self.user.check_perms,
            TranslatedWork(language='en'),
            'add_comment',
        )

    def test_check_role(self):
        work = TranslatedWork(language='jp')
        reputation = models.Reputation.objects.filter(
            user=self.user, language='es'
        )
        reputation.update(score=PERMISSIONS['review_translation'])
        # Japanese
        self.user.check_role('translator', work)
        self.assertRaisesMessage(
            PermissionDenied,
            'A reputation of 1000 is required for the privilege '
            '"review_translation".',
            self.user.check_role,
            'reviewer',
            work,
        )
        self.assertRaisesMessage(
            PermissionDenied,
            'A reputation of 1000000 is required for the privilege "trustee".',
            self.user.check_role,
            'trustee',
            work,
        )
        # Spanish
        work.language = 'es'
        self.user.check_role('translator', work)
        self.user.check_role('reviewer', work)
        self.assertRaisesMessage(
            PermissionDenied,
            'A reputation of 1000000 is required for the privilege "trustee".',
            self.user.check_role,
            'trustee',
            work,
        )
        reputation.update(score=PERMISSIONS['trustee'])
        self.user.check_role('translator', work)

    def test_check_role_invalid(self):
        self.assertRaisesMessage(
            ValueError,
            'The role "test" is invalid.',
            self.user.check_role,
            'test',
            None,
        )

    def test_get_language_of(self):
        work = TranslatedWorkFactory()
        self.assertIsNone(self.user.work)
        self.assertEqual(self.user.get_language_of(work), work.language)
        self.assertEqual(self.user.work, work)
        another_work = TranslatedWork(language='se')
        self.assertEqual(self.user.get_language_of(another_work), 'se')
        self.assertEqual(self.user.work, another_work)
        with self.assertNumQueries(1):
            self.assertEqual(self.user.get_language_of(work.pk), work.language)
        self.assertEqual(self.user.work, work)
        with self.assertNumQueries(0):
            self.assertEqual(self.user.get_language_of(work.pk), work.language)

    def test_create_historical_record_changing_a_field(self):
        self.assertEqual(self.user.history.count(), 2)
        self.user.address = 'Long Road 123'
        self.user.save()
        self.assertEqual(self.user.history.count(), 3)

    def test_do_not_create_a_historical_record_changing_last_login(self):
        self.user.last_login = timezone.now()
        self.user.save()
        self.assertEqual(self.user.history.count(), 2)

    def test_svg_avatar(self):
        self.assertEqual(self.user.get_avatar(), self.get_svg_avatar(self.user))


class SerializerTests(SimpleTestCase):
    def test_country_serializer_options(self):
        """
        Tests that the response of OPTIONS contains the country names.
        """
        self.assertIn("('AF', 'Afghanistan')", repr(CountrySerializer()))

    def test_user_field_serializer(self):
        user = factories.UserFactory.build(
            public_id='abc', first_name='Uli', last_name='Weber', edits=10
        )
        context = {'request': MagicMock()}
        data = UserFieldSerializer(user, context=context).data
        self.assertEqual(data['id'], 'abc')
        self.assertEqual(data['url'], f'/api/users/{user.username}/')
        self.assertEqual(data['username'], user.username)
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertEqual(data['contributions'], {'edits': 10})

        user.show_full_name = True
        data = UserFieldSerializer(user, context=context).data
        self.assertEqual(data['first_name'], 'Uli')
        self.assertEqual(data['last_name'], 'Weber')

        user.is_active = False
        data = UserFieldSerializer(user, context=context).data
        self.assertEqual(data['id'], None)
        self.assertEqual(data['url'], None)
        self.assertEqual(data['username'], '(deleted user)')
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertEqual(data['contributions'], {})

    def test_community_user_profile_serializer(self):
        user = factories.UserFactory.build(
            first_name='Uli',
            last_name='Weber',
            born=datetime.date.today() - datetime.timedelta(days=12 * 365 + 5),
            country='CH',
            description='This is me.',
            experience='Testing, testing, testing.',
            education='Python and Django.',
        )
        context = {'request': MagicMock()}
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertIsNone(data['age'])
        self.assertIsNone(data['country']['code'])
        self.assertEqual(data['description'], '')
        self.assertEqual(data['experience'], '')
        self.assertEqual(data['education'], '')

        user.show_full_name = True
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], 'Uli')
        self.assertEqual(data['last_name'], 'Weber')
        self.assertIsNone(data['age'])
        self.assertIsNone(data['country']['code'])
        self.assertEqual(data['description'], '')
        self.assertEqual(data['experience'], '')
        self.assertEqual(data['education'], '')

        user.show_full_name = False
        user.show_country = True
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertIsNone(data['age'])
        self.assertEqual(data['country']['code'], 'CH')
        self.assertEqual(data['description'], '')
        self.assertEqual(data['experience'], '')
        self.assertEqual(data['education'], '')

        user.show_country = False
        user.show_age = True
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertEqual(data['age'], 12)
        self.assertIsNone(data['country']['code'])
        self.assertEqual(data['description'], '')
        self.assertEqual(data['experience'], '')
        self.assertEqual(data['education'], '')

        user.show_age = False
        user.show_description = True
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertIsNone(data['age'])
        self.assertIsNone(data['country']['code'])
        self.assertEqual(data['description'], 'This is me.')
        self.assertEqual(data['experience'], '')
        self.assertEqual(data['education'], '')

        user.show_description = False
        user.show_experience = True
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertIsNone(data['age'])
        self.assertIsNone(data['country']['code'])
        self.assertEqual(data['description'], '')
        self.assertEqual(data['experience'], 'Testing, testing, testing.')
        self.assertEqual(data['education'], '')

        user.show_experience = False
        user.show_education = True
        data = CommunityUserProfileSerializer(user, context=context).data
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertIsNone(data['age'])
        self.assertIsNone(data['country']['code'])
        self.assertEqual(data['description'], '')
        self.assertEqual(data['experience'], '')
        self.assertEqual(data['education'], 'Python and Django.')


class UserAPITests(APITests):
    url = reverse('user')

    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory(
            create_avatar=(600, 800), privileges=(factories.PrivilegeFactory(),)
        )

        privileges = []
        for p in cls.user.privileges.all():
            privileges.append(
                {
                    'name': p.name,
                    'language': p.language,
                    'trustee': p.trustee_id,
                    # cls.get_url('privilege-details', p.trustee_id),
                }
            )

        cls.data = {
            'url': reverse('community_user_profile', args=(cls.user.username,)),
            'id': cls.user.public_id,
            'username': cls.user.username,
            'firstName': cls.user.first_name,
            'lastName': cls.user.last_name,
            'email': cls.user.email,
            'avatar': 'http://testserver' + cls.user.avatar.url,
            'avatarCrop': cls.user.avatar_crop,
            'thumbnail': cls.user.get_avatar(),
            'thumbnails': [
                {'url': cls.user.avatar_60.url, 'width': 60, 'height': 60},
                {'url': cls.user.avatar_120.url, 'width': 120, 'height': 120},
                {'url': cls.user.avatar_300.url, 'width': 300, 'height': 300},
            ],
            'address': cls.user.address,
            'address2': cls.user.address_2,
            'zipCode': cls.user.zip_code,
            'city': cls.user.city,
            'state': cls.user.state,
            'country': {'code': '', 'name': '', 'flag': '', 'unicodeFlag': ''},
            'phone': cls.user.phone,
            'language': None,
            'born': cls.user.born,
            'roles': [],
            # 'reputation': cls.user.reputation,
            'contributions': {
                'edits': 0,
                'developerComments': 0,
                'segmentComments': 0,
            },
            'privileges': privileges,
            'lastLogin': None,
            'dateJoined': cls.date(cls.user.date_joined),
            'description': '',
            'experience': '',
            'education': '',
            'isVerified': False,
            'subscribedEdits': True,
            'showFullName': False,
            'showCountry': False,
            'showAge': False,
            'showDescription': False,
            'showExperience': False,
            'showEducation': False,
            'age': None,
        }

    def setUp(self):
        self.user.is_active = True
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save_without_historical_record()
        # self.client.force_login(self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def _test_retreive_list(self):
        factories.UserFactory()
        res = self.client.get(self.get_url('list'))
        # 2 + 1 for AnonymousUser
        self.assertEqual(len(res.json()['results']), 3)

    def test_retreive_detail(self):
        res = self.client.get(self.url)
        self.data['lastLogin'] = self.date(self.user.last_login)
        self.assertEqual(res.json(), self.data)

    def _test_create(self):
        res = self.client.post(self.get_url('list'))
        self.assertEqual(res.status_code, 403)

    def test_update_put(self):
        data = self.data.copy()
        data['firstName'] = 'Edwin'
        data['language'] = ''
        res = self.client.put(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'avatar': [
                    'The submitted data was not a file. '
                    'Check the encoding type on the form.'
                ]
            },
        )
        del data['avatar']
        res = self.client.put(self.url, data)
        self.assertEqual(res.status_code, 200)
        user = models.User.objects.get(pk=self.user.pk)
        self.assertEqual(user.first_name, 'Edwin')
        self.assertEqual(user.avatar.width, 600)
        self.assertEqual(user.avatar.height, 800)

    def test_language_validation_works_with_non_string(self):
        res = self.client.patch(self.url, {'language': {'a': 'b'}})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'language': [
                    '"{&#39;a&#39;: &#39;b&#39;}" is not a valid language code.'
                ]
            },
        )

    def test_language_html_is_escaped(self):
        res = self.client.patch(self.url, {'language': '<script>'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {'language': ['"&lt;script&gt;" is not a valid language code.']},
        )

    def test_is_active(self):
        res = self.client.patch(
            self.url, {'is_active': False, 'password': 'pw'}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Processing restricted')
        success = self.client.login(username=self.user.username, password='pw')
        self.assertFalse(success)
        res = self.client.patch(self.url, {})
        self.assertEqual(res.status_code, 401)

    def test_is_active_password_required(self):
        res = self.client.patch(self.url, {'is_active': False})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Please enter your password to confirm your decision'
                ]
            },
        )

    def test_is_active_password_invalid(self):
        res = self.client.patch(
            self.url, {'is_active': False, 'password': 'invalid'}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'nonFieldErrors': ['Your password was invalid']}
        )

    def test_contributions(self):
        work = TranslatedWorkFactory()
        segment = TranslatedSegmentFactory(work=work)
        segment._history_user = self.user
        segment.save()
        DeveloperCommentFactory(user=self.user)
        SegmentCommentFactory.create_batch(2, work=work, user=self.user)
        res = self.client.get(self.url)
        expected = {'edits': 1, 'developerComments': 1, 'segmentComments': 2}
        self.assertEqual(res.json()['contributions'], expected)

    def test_password_is_not_saved(self):
        password = self.user.password
        res = self.client.patch(self.url, {'password': 'new'})
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(password, self.user.password)

    def test_required_fields(self):
        data = {
            'url': '',
            'id': '',
            'username': '',
            'firstName': '',
            'lastName': '',
            'email': '',
            # 'password',
            'avatar': None,
            'avatarCrop': '',
            'address': '',
            'address2': '',
            'zipCode': '',
            'city': '',
            'state': '',
            'country': '',
            'phone': '',
            'language': '',
            'born': None,
            'reputation': '',
            'privileges': [],
            'lastLogin': '',
            'dateJoined': '',
        }
        res = self.client.put(self.url, data)
        self.assertEqual(res.status_code, 400)
        expected = {
            'email': ['This field may not be blank.'],
            # 'lastName': ['This field may not be blank.'],
            # 'firstName': ['This field may not be blank.'],
        }
        self.assertEqual(res.json(), expected)

    def test_read_only_fields(self):
        editable_fields = {
            'firstName': 'Rose',
            'lastName': 'Aaron',
            'email': 'sweet-ann@example.com',
            # 'password',
            # 'avatar': 'another/path',
            'avatarCrop': {'x': 1, 'y': 2},
            'address': 'Creek Valley 5',
            'address2': '--empty--',
            'zipCode': '12345',
            'city': 'Lake City',
            'state': 'Flower State',
            'country': 'BR',
            'phone': '123 45',
            'language': 'es',
            'born': datetime.date(1990, 5, 5),
        }
        read_only_fields = {
            'url': 'some/path',
            'id': '5',
            'publicId': '5',
            'username': 'user_5',
            # 'reputation': '1000',
            'privileges': [],
            'lastLogin': 'today',
            'dateJoined': 'yesterday',
        }
        data = editable_fields.copy()
        data.update(read_only_fields)
        res = self.client.patch(self.url, data)
        self.assertEqual(res.status_code, 200)
        user = models.User.objects.get(pk=self.user.pk)
        self.data['lastLogin'] = self.date(user.last_login)

        # Updated fields
        for key, value in editable_fields.items():
            self.assertEqual(getattr(user, camel_to_underscore(key)), value)

        # Read-only fields
        for key, value in read_only_fields.items():
            if key == 'url':
                continue

            db_value = getattr(user, camel_to_underscore(key))
            if isinstance(db_value, datetime.datetime):
                db_value = self.date(db_value)
            elif not isinstance(db_value, (int, str)):
                db_value = [
                    {
                        'trustee': p.trustee_id,
                        'language': p.language,
                        'name': p.name,
                    }
                    for p in db_value.all()
                ]

            self.assertNotEqual(db_value, value)
            if key == 'publicId':
                self.assertEqual(db_value, self.data['id'])
            elif not key == 'id':
                self.assertEqual(db_value, self.data[key])

    def _test_upload_avatar_form_parser(self):
        # parsers.FormParser not implemented right now
        from django.utils.http import urlencode

        data = {
            'first_name': 'Andrew',
            # 'firstName': 'Andrew',
            # 'avatar': factories.create_image(123, 456),
        }
        res = self.client.patch(
            self.url,
            urlencode(data),
            content_type='application/x-www-form-urlencoded',
        )
        self.assertEqual(res.status_code, 200)
        user = models.User.objects.get(pk=self.user.pk)
        self.assertEqual(user.first_name, 'Andrew')
        self.assertEqual(user.avatar.width, 123)
        self.assertEqual(user.avatar.height, 456)

    def test_upload_avatar_multipart_parser(self):
        avatar = factories.create_image(1200, 1200)
        avatar.name = 'me.jpg'
        data = {
            'first_name': 'Andrew',
            # 'firstName': 'Andrew',
            'avatar': avatar,
        }
        res = self.client.patch(self.url, data, format='multipart')
        self.assertEqual(res.status_code, 200)
        user = models.User.objects.get(pk=self.user.pk)
        self.assertEqual(user.first_name, 'Andrew')
        self.assertEqual(user.avatar.width, 600)
        self.assertEqual(user.avatar.height, 600)

    def test_destroy(self):
        self.assertTrue(self.user.is_active)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'password': ['This field may not be null.']}
        )
        res = self.client.delete(self.url, {'password': 'pw'})
        self.assertRedirects(
            res, '/', target_status_code=302, fetch_redirect_response=False
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'User deletion requested')
        last_record = self.user.history.latest()
        self.assertEqual(last_record.history_change_reason, 'delete user')
        res = self.client.patch(self.url, {})
        self.assertEqual(res.status_code, 401)

    def test_personal_data(self):
        url = f'{self.url}personal-data/'
        email_address = EmailAddress.objects.create(
            email=self.user.email, user=self.user
        )
        EmailAddress.objects.create(
            email='an@oth.er', user=factories.UserFactory()
        )
        EmailConfirmation.objects.create(email_address=email_address)
        social_app = SocialApp.objects.create()
        social_account = SocialAccount.objects.create(
            provider='ABC OAuth', user=self.user
        )
        SocialToken.objects.create(app=social_app, account=social_account)
        content_type = ContentType.objects.first()
        LogEntry.objects.create(
            object_id=1,
            content_type=content_type,
            action_flag=1,
            change_message='{"some key": "with a value"}',
            user=self.user,
        )
        group = Group.objects.create(name='Test group')
        self.user.groups.add(group)
        permission = Permission.objects.create(
            name='Test permission',
            content_type=content_type,
            codename='test-permission',
        )
        self.user.user_permissions.add(permission)
        DeveloperCommentFactory(user=self.user)
        another_user = factories.UserFactory.build()
        another_user._history_user = self.user
        another_user.save()
        DeveloperCommentFactory(user=another_user)
        page = PageFactory.build()
        page._history_user = self.user
        page.save()
        author = AuthorFactory.build()
        author._history_user = self.user
        author.save()
        licence = LicenceFactory.build()
        licence._history_user = self.user
        licence.save()
        trustee = TrusteeFactory.build()
        trustee._history_user = self.user
        trustee.save()
        trustee.members.add(self.user)
        original_work = OriginalWorkFactory.build(
            author=author, licence=licence, trustee=trustee
        )
        original_work._history_user = self.user
        original_work.save()
        original_segment = OriginalSegmentFactory.build(
            tag='h2', work=original_work
        )
        original_segment._history_user = self.user
        original_segment.save()
        reference = ReferenceFactory.build()
        reference._history_user = self.user
        reference.save()
        translated_work = TranslatedWorkFactory.build(
            original=original_work, trustee=trustee
        )
        translated_work._history_user = self.user
        translated_work.save()
        translated_segment = translated_work.segments.first()
        translated_segment.locked_by = self.user
        translated_segment._history_user = self.user
        translated_segment.save()
        SegmentCommentFactory(work=translated_work, user=self.user)
        SegmentDraftFactory(
            work=translated_work, segment=translated_segment, owner=self.user
        )
        # I can't use self.user for some reason
        user = models.User.objects.get(pk=self.user.pk)
        user._history_user = user
        user.save()

        # Response
        res = self.client.get(url)
        result = res.json()
        hidden_msg = '(Value not displayed for safety reasons)'

        for k, v in self.data.items():
            if k in ('url', 'roles', 'thumbnail', 'contributions'):
                continue
            if k in ('lastLogin',):
                self.assertIn(k, result)
            elif k in ('language', 'country'):
                self.assertIn(result[k], ('', None))
            else:
                self.assertEqual(result[k], v)

        fields = ('id', 'email', 'verified', 'primary', 'emailconfirmationSet')
        excluded = ('user',)
        objects = result['emailaddressSet']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'email',
            'verified',
            'user',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ()
        objects = result['historicalemailaddresses']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])
        # Don't have the wrong e-mail included
        self.assertEqual(objects[0]['email'], self.user.email)

        fields = ('id', 'created', 'sent', 'key')
        excluded = ('email_address',)
        objects = result['emailaddressSet'][0]['emailconfirmationSet']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])
        self.assertEqual(objects[0]['key'], hidden_msg)

        fields = (
            'id',
            'provider',
            'uid',
            'lastLogin',
            'dateJoined',
            'extraData',
            'socialtokenSet',
        )
        objects = result['socialaccountSet']
        self.assertEqual(len(objects), 1)
        excluded = ('user',)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = ('id', 'app', 'token', 'tokenSecret', 'expiresAt')
        excluded = ('account',)
        objects = result['socialaccountSet'][0]['socialtokenSet']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'actionTime',
            'objectId',
            'contentType',
            'objectRepr',
            'actionFlag',
            'changeMessage',
        )
        objects = result['logentrySet']
        self.assertEqual(len(objects), 1)
        excluded = ('user',)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = ('id', 'name')
        excluded = ('permissions',)
        objects = result['groups']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = ('id', 'name', 'contentType', 'codename')
        objects = result['userPermissions']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])

        fields = ('sessionKey', 'expireDate')
        excluded = ('sessionData',)
        obj = result['session']
        for k in fields:
            self.assertIn(k, obj)
        for k in excluded:
            self.assertNotIn(k, obj)
        self.assertEqual(obj['sessionKey'], hidden_msg)

        fields = ('id', 'created', 'lastModified', 'content', 'toDelete')
        excluded = ('user',)
        objects = result['developercomments']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'slug',
            'content',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicalpages']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'prefix',
            'firstName',
            'lastName',
            'suffix',
            'born',
            'bio',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicalauthors']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'title',
            'description',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicallicences']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'key',
            'work',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicaloriginalsegments']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'title',
            'subtitle',
            'abbreviation',
            'type',
            'description',
            'language',
            'private',
            'published',
            'edition',
            'isbn',
            'publisher',
            'trustee',
            'author',
            'licence',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicaloriginalworks']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'title',
            'type',
            'abbreviation',
            'author',
            'published',
            'language',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicalreferences']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'content',
            'relativeId',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicaltranslatedsegments']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'title',
            'subtitle',
            'abbreviation',
            'type',
            'description',
            'language',
            'private',
            'protected',
            'trustee',
            'original',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicaltranslatedworks']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'name',
            'description',
            'code',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyType',
        )
        excluded = ('historyUser',)
        objects = result['historicaltrustees']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'work',
            'position',
            'content',
            'toDelete',
        )
        excluded = ('user',)
        objects = result['segmentcomments']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = ('id', 'created', 'content', 'segment', 'work', 'position')
        excluded = ('owner',)
        objects = result['drafts']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = (
            'id',
            'created',
            'lastModified',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'work',
            'original',
            'lockedBy',
        )
        objects = result['translatedsegmentSet']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        fields = ('id', 'name', 'description', 'code')
        excluded = ('members',)
        objects = result['trusteeMemberships']
        self.assertEqual(len(objects), 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

        owner_fields = (
            'password',
            'lastLogin',
            'isSuperuser',
            'isStaff',
            'isActive',
            'dateJoined',
            'username',
            'firstName',
            'lastName',
            'pseudonym',
            'nameDisplay',
            'email',
            'avatar',
            'avatarCrop',
            'address',
            'address2',
            'zipCode',
            'city',
            'state',
            'country',
            'phone',
            'language',
            'born',
            'historyId',
            'historyChangeReason',
            'historyDate',
            'historyUser',
            'historyType',
        )
        minimal_fields = ('username', 'password', 'historyUser')
        excluded = ('id',)
        objects = result['historicalusers']
        self.assertEqual(len(objects), 2)
        for k in minimal_fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])
        for k in owner_fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])
        self.assertEqual(objects[0]['password'], hidden_msg)

        fields = ('id', 'score', 'language')
        excluded = ('user',)
        objects = result['reputations']
        self.assertEqual(len(objects), len(ACTIVE_LANGUAGES) - 1)
        for k in fields:
            self.assertIn(k, objects[0])
        for k in excluded:
            self.assertNotIn(k, objects[0])

    @skipIf(sys.version_info[:3] < (3, 6, 2), 'Python 3.6.2+ required')
    def test_export_data(self):
        res = self.client.post(f'{self.url}export-data/', {'password': 'pw'})
        self.assertEqual(res.status_code, 200)
        with BytesIO(res.getvalue()) as archive:
            with ZipFile(archive) as folder:
                with folder.open(folder.filelist[0]) as f:
                    data = json.load(f)
        expected = (
            'Literary works and their translations are copyrighted by the '
            'Ellen G. White Estate®. You shall not adversely affect the '
            'rights and freedoms of the Ellen G. White Estate® or others '
            '(see article 20 (4) GDPR).'
        )
        self.assertEqual(data['info'], expected)
        self.assertIn('username', data['data'])


class LittleUserAPITests(APITests):
    url = reverse('little_user')

    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory()

    def test_headers(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 205)
        self.assertTrue(res.has_header('version'))
        self.assertEqual(res['version'], settings.VERSION)
        # This check actually belongs else where but I don't know where to put
        # tests that should be in the 'langify' module
        self.assertGreater(
            settings.RELEASED + datetime.timedelta(365), timezone.now()
        )
        self.assertTrue(res.has_header('released'))
        self.assertEqual(res['released'], settings.RELEASED.isoformat())

        self.client.force_login(self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.has_header('version'))
        self.assertEqual(res['version'], settings.VERSION)
        self.assertTrue(res.has_header('released'))
        self.assertEqual(res['released'], settings.RELEASED.isoformat())

    def test_permissions_serializer(self):
        permissions_en = self.language_permissions.copy()
        permissions_de = self.language_permissions.copy()
        expected = self.permissions.copy()
        expected.update({'de': permissions_de, 'en': permissions_en})

        # ---------------------------------------------------------
        # Right now every user gets a reputuation of 5
        self.assertNotEqual(
            camelize(get_permissions_serializer()(self.user.permissions).data),
            expected,
        )
        self.user.reputations.all().delete()
        # ---------------------------------------------------------

        # No reputation object
        self.assertEqual(
            camelize(get_permissions_serializer()(self.user.permissions).data),
            expected,
        )
        # 1 Reputation object
        models.Reputation.objects.create(
            score=100, language='en', user_id=self.user.pk
        )
        permissions_en.update(
            dict(
                (
                    ('addTranslation', True),
                    ('changeTranslation', True),
                    ('deleteTranslation', True),
                    ('restoreTranslation', True),
                    ('addComment', True),
                    ('changeComment', True),
                    ('flagComment', True),
                    ('flagTranslation', True),
                    ('flagUser', True),
                    ('approveTranslation', True),
                )
            )
        )
        self.assertEqual(
            camelize(get_permissions_serializer()(self.user.permissions).data),
            expected,
        )
        # 3 Reputation objects
        models.Reputation.objects.create(
            score=200, language='de', user_id=self.user.pk
        )
        models.Reputation.objects.create(
            score=300, language='xy', user_id=self.user.pk
        )
        permissions_de.update(
            dict(
                (
                    ('addTranslation', True),
                    ('changeTranslation', True),
                    ('deleteTranslation', True),
                    ('restoreTranslation', True),
                    ('addComment', True),
                    ('changeComment', True),
                    ('deleteComment', True),
                    ('flagComment', True),
                    ('flagTranslation', True),
                    ('flagUser', True),
                    ('approveTranslation', True),
                    ('disapproveTranslation', True),
                    ('restoreTranslation', True),
                )
            )
        )
        self.assertEqual(
            camelize(get_permissions_serializer()(self.user.permissions).data),
            expected,
        )


class UsersAPITests(APITests):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory(
            username='tom123',
            first_name='Tom',
            last_name='Johnson',
            email='tom@example.com',
            address='Street 1',
            address_2='Apartment 3',
            zip_code='12345',
            city='Amsterdam',
            state='Holland',
            phone='+1 2345 6789',
            born=datetime.date(2000, 1, 1),
            language='de',
            country='NL',
        )
        cls.url = reverse('community_user_profile', args=(cls.user.username,))
        cls.data = {
            'id': cls.user.public_id,
            'url': cls.url,
            'username': 'tom123',
            'firstName': '',
            'lastName': '',
            'age': None,
            'language': {'code': 'de', 'name': 'German', 'rtl': False},
            'roles': [],
            'country': {
                'code': None,
                'flag': None,
                'name': None,
                'unicodeFlag': None,
            },
            'thumbnail': cls.get_svg_avatar(cls.user),
            'thumbnails': None,
            'dateJoined': cls.date(cls.user.date_joined),
            'description': '',
            'experience': '',
            'education': '',
            'isVerified': False,
            'showFullName': False,
            'showCountry': False,
            'showAge': False,
            'showDescription': False,
            'showExperience': False,
            'showEducation': False,
        }
        cls.user_2 = factories.UserFactory()

    def test_response(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)
        self.client.force_login(self.user_2)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    @patch(
        'path.models.User.roles',
        [
            OrderedDict(
                (('language', 'Sp'), ('role', 'reviewer'), ('edits', 10))
            ),
            OrderedDict(
                (('language', 'Fr'), ('role', 'trustee'), ('edits', 2))
            ),
        ],
    )
    def test_roles(self):
        self.client.force_login(self.user_2)
        res = self.client.get(self.url)
        data = self.data.copy()
        data['roles'] = [
            {'language': 'Sp', 'role': 'reviewer', 'edits': 10},
            {'language': 'Fr', 'role': 'trustee', 'edits': 2},
        ]
        self.assertEqual(res.json(), data)

    def test_inactive_user(self):
        self.client.force_login(self.user_2)
        models.User.objects.filter(pk=self.user.pk).update(is_active=False)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 404)


class EmailAddressAPITests(APITests):
    basename = 'emailaddress'

    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory(email='jacob@example.com')
        cls.email_address = EmailAddress.objects.create(
            email=cls.user.email, user=cls.user
        )
        cls.url_list = cls.get_url('list')
        cls.url_confirm = cls.url_list + 'send-confirmation/'

    def setUp(self):
        self.client.force_login(self.user)

    def test_send_confirmation(self):
        outbox = MailjetClient.test_outbox
        outbox.clear()
        res = self.client.post(self.url_confirm, {'email': self.user.email})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'detail': 'Confirmation e-mail sent.'})
        self.assertEqual(len(outbox), 1)
        msg = outbox[0][-1]['data']['Messages'][0]
        self.assertIn(
            'https://testserver/auth/confirm-email', msg['Variables']['link']
        )
        self.assertEqual(msg['To'][0]['Email'], self.user.email)

    def test_send_confirmation_404(self):
        res = self.client.post(self.url_confirm, {'email': 'dne@example.com'})
        self.assertEqual(res.status_code, 404)

    def test_send_confirmation_email_verified_already(self):
        EmailAddress.objects.update(verified=True)
        res = self.client.post(self.url_confirm, {'email': self.user.email})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'detail': 'jacob@example.com is verified already.'}
        )


class TransactionalPasswordResetFormTests(SimpleTestCase):
    def test_send_mail(self):
        client = MagicMock()
        with patch('path.api.serializers.MailjetClient', return_value=client):
            TransactionalPasswordResetForm().send_mail(
                None,
                None,
                {'protocol': 't', 'domain': 'e.c', 'uid': '1', 'token': '2-3'},
                None,
                't@e.c',
            )
            client.send_transactional_email.assert_called_once_with(
                533_481,
                't@e.c',
                'Reset password',
                {
                    'heading': 'Password forgotten?',
                    'introduction': 'Don\'t worry.',
                    'task': (
                        'Just click on the green button and enter a new one.'
                    ),
                    'button': 'Reset password',
                    'link': 't://e.c/auth/password-reset-confirmation/1/2-3/',
                    'ignore_note': (
                        'In case you didn\'t request a password reset on '
                        'ellen4all.org you can ignore this e-mail.'
                    ),
                },
            )


class AdapterTests(SimpleTestCase):
    def test_send_mail_success(self):
        client = MagicMock()
        with patch('path.adapter.MailjetClient', return_value=client):
            ctx = {'activate_url': 'https://example.com'}
            RestAdapter().send_mail('send email_confirmation', 't@e.c', ctx)
            client.send_transactional_email.assert_called_once_with(
                533_481,
                't@e.c',
                'Confirm your e-mail address',
                {
                    'heading': 'Please confirm your e-mail address',
                    'introduction': (
                        'You are one final step from using the e-mail address '
                        'for your account at ellen4all.org.'
                    ),
                    'task': (
                        'Please confirm it by clicking on the green button.'
                    ),
                    'button': 'Confirm',
                    'link': 'https://example.com',
                    'ignore_note': (
                        'In case you didn\'t provide this e-mail address on '
                        'ellen4all.org you can ignore this e-mail.'
                    ),
                },
            )

    def test_send_mail_not_implemented(self):
        client = MagicMock()
        with patch('path.adapter.MailjetClient', return_value=client):
            msg = 'No mailing for tmpl implemented.'
            with self.assertRaisesMessage(NotImplementedError, msg):
                RestAdapter().send_mail('tmpl', 'test@example.com', 'context')
            client.send_transactional_email.assert_not_called()


class FlagUserAPITests(APITests):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory()
        cls.user2 = factories.UserFactory()
        cls.work = TranslatedWorkFactory(language='tr')
        cls.flag_user_1_url = reverse(
            'flag_user', kwargs={'public_id': cls.user.public_id}
        )
        cls.flag_user_2_url = reverse(
            'flag_user', kwargs={'public_id': cls.user2.public_id}
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.flag_user_2_url)
        self.assertEqual(res.status_code, 401)

    def test_flag_unflag(self):
        self.set_reputation('flag_user')
        res = self.client.post(self.flag_user_2_url)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.user.flags.count(), 1)
        self.assertEqual(self.user2.flagged_by.count(), 1)

        res = self.client.delete(self.flag_user_2_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.user.flags.count(), 0)
        self.assertEqual(self.user2.flagged_by.count(), 0)

    def test_mutiple_flag_same_user(self):
        self.set_reputation('flag_user')
        res = self.client.post(self.flag_user_2_url)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.user.flags.count(), 1)
        self.assertEqual(self.user2.flagged_by.count(), 1)

        res = self.client.post(self.flag_user_2_url, {'reason': 'test reason'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.user.flags.count(), 1)
        self.assertEqual(self.user2.flagged_by.count(), 1)

        res = self.client.post(
            self.flag_user_2_url, {'reason': 'test reason 2'}
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.user.flags.count(), 1)
        self.assertEqual(self.user2.flagged_by.count(), 1)

    def test_flag_self(self):
        self.set_reputation('flag_user')
        res = self.client.post(self.flag_user_1_url)
        self.assertEqual(res.status_code, 400)

    def test_unflag_self(self):
        self.set_reputation('flag_user')
        res = self.client.delete(self.flag_user_1_url)
        self.assertEqual(res.status_code, 400)
