import datetime
import random
from copy import deepcopy
from unittest.mock import patch
from urllib import parse

from rest_framework import test

from base.constants import COMMENT_DELETION_DELAY, LANGUAGES_DICT, PERMISSIONS
from base.tests import APITests
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, reset_queries
from django.db.models import ProtectedError, Sum
from django.test import TestCase, override_settings, tag
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from panta import factories, management, models
from panta.api import serializers, views
from panta.constants import (
    BLANK,
    CHANGE_REASONS,
    HISTORICAL_UNIT_PERIOD,
    IN_REVIEW,
    IN_TRANSLATION,
    RELEASED,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)
from path.factories import UserFactory
from path.models import Reputation
from white_estate.models import Class, Tag

User = get_user_model()

required_approvals_patch = patch(
    'panta.models.REQUIRED_APPROVALS',
    {'de': {'translator': 0, 'reviewer': 0, 'trustee': 0}},
)


class APIBaseTests(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_login_required(self):
        res = self.client.get(reverse('api-root'))
        self.assertEqual(res.status_code, 401)

    def test_authenticated_user(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('api-root'))
        self.assertContains(res, 'http://testserver/api/')
        self.assertEqual(res.status_code, 200)

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save_without_historical_record()
        self.client.force_login(self.user)
        res = self.client.get(reverse('api-root'))
        self.assertEqual(res.status_code, 401)


class LanguageTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        original = factories.OriginalWorkFactory()

        def build_work(language):
            work = factories.TranslatedWorkFactory.build(
                language=language,
                trustee_id=original.trustee_id,
                original=original,
            )
            return work

        models.TranslatedWork.objects.bulk_create(
            (
                build_work('de'),
                build_work('de'),
                build_work('de'),
                build_work('sw'),
                build_work('sw'),
                build_work('tr'),
            )
        )

    def test_list(self):
        with self.assertNumQueries(1):
            res = self.client.get(reverse('languages'))
        expected = [
            {'code': 'af', 'name': 'Afrikaans', 'count': 0},
            {'code': 'am', 'name': 'Amharic', 'count': 0},
            {'code': 'ar', 'name': 'Arabic', 'count': 0},
            {'code': 'hy', 'name': 'Armenian', 'count': 0},
            {'code': 'bn', 'name': 'Bengali', 'count': 0},
            {'code': 'ber', 'name': 'Berber', 'count': 0},
            {'code': 'bg', 'name': 'Bulgarian', 'count': 0},
            {'code': 'my', 'name': 'Burmese', 'count': 0},
            {'code': 'ckb', 'name': 'Central Kurdish', 'count': 0},
            {'code': 'zh', 'name': 'Chinese', 'count': 0},
            {'code': 'hr', 'name': 'Croatian', 'count': 0},
            {'code': 'cs', 'name': 'Czech', 'count': 0},
            {'code': 'da', 'name': 'Danish', 'count': 0},
            {'code': 'nl', 'name': 'Dutch', 'count': 0},
            {'code': 'fi', 'name': 'Finnish', 'count': 0},
            {'code': 'fr', 'name': 'French', 'count': 0},
            {'code': 'grt', 'name': 'Garo', 'count': 0},
            {'code': 'de', 'name': 'German', 'count': 3},
            {'code': 'hi', 'name': 'Hindi', 'count': 0},
            {'code': 'hu', 'name': 'Hungarian', 'count': 0},
            {'code': 'is', 'name': 'Icelandic', 'count': 0},
            {'code': 'ilo', 'name': 'Ilocano', 'count': 0},
            {'code': 'id', 'name': 'Indonesian', 'count': 0},
            {'code': 'it', 'name': 'Italian', 'count': 0},
            {'code': 'ja', 'name': 'Japanese', 'count': 0},
            {'code': 'kha', 'name': 'Khasi', 'count': 0},
            {'code': 'rw', 'name': 'Kinyarwanda', 'count': 0},
            {'code': 'ko', 'name': 'Korean', 'count': 0},
            {'code': 'lv', 'name': 'Latvian', 'count': 0},
            {'code': 'lt', 'name': 'Lithuanian', 'count': 0},
            {'code': 'lus2', 'name': 'Lushai', 'count': 0},
            {'code': 'mk', 'name': 'Macedonian', 'count': 0},
            {'code': 'mg', 'name': 'Malagasy', 'count': 0},
            {'code': 'ms', 'name': 'Malay', 'count': 0},
            {'code': 'mr', 'name': 'Marathi', 'count': 0},
            {'code': 'lus', 'name': 'Mizo', 'count': 0},
            {'code': 'nb', 'name': 'Norwegian Bokmål', 'count': 0},
            {'code': 'hil', 'name': 'Panayan', 'count': 0},
            {'code': 'fa', 'name': 'Persian', 'count': 0},
            {'code': 'pl', 'name': 'Polish', 'count': 0},
            {'code': 'pt', 'name': 'Portuguese', 'count': 0},
            {'code': 'ro', 'name': 'Romanian', 'count': 0},
            {'code': 'ru', 'name': 'Russian', 'count': 0},
            {'code': 'ksw', 'name': "S'gaw Karen", 'count': 0},
            {'code': 'sr', 'name': 'Serbian', 'count': 0},
            {'code': 'si', 'name': 'Sinhala', 'count': 0},
            {'code': 'sk', 'name': 'Slovak', 'count': 0},
            {'code': 'es', 'name': 'Spanish', 'count': 0},
            {'code': 'sw', 'name': 'Swahili', 'count': 2},
            {'code': 'sv', 'name': 'Swedish', 'count': 0},
            {'code': 'tl', 'name': 'Tagalog', 'count': 0},
            {'code': 'ta', 'name': 'Tamil', 'count': 0},
            {'code': 'te', 'name': 'Telugu', 'count': 0},
            {'code': 'th', 'name': 'Thai', 'count': 0},
            {'code': 'toi', 'name': 'Tonga (Zambia and Zimbabwe)', 'count': 0},
            {'code': 'ton', 'name': 'Tongan (Tonga Islands)', 'count': 0},
            {'code': 'tr', 'name': 'Turkish', 'count': 1},
            {'code': 'uk', 'name': 'Ukrainian', 'count': 0},
            {'code': 'ur', 'name': 'Urdu', 'count': 0},
            {'code': 'vi', 'name': 'Vietnamese', 'count': 0},
        ]
        self.assertEqual(res.json(), expected)


class TrusteeTests(APITests):
    basename = 'trustee'

    @classmethod
    def setUpTestData(cls):
        cls.factory = test.APIRequestFactory()
        cls.obj = factories.TrusteeFactory(code='abc')
        cls.user = UserFactory()
        # cls.staff = Group.objects.get(name='abc-staff')
        cls.data = {
            'id': cls.obj.pk,
            'url': cls.get_url('detail', cls.obj.pk),
            'name': cls.obj.name,
            'description': cls.obj.description,
            'code': cls.obj.code,
            # 'members': list(cls.obj.members.all()),
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        request = self.factory.get(self.url_list)
        list_view = views.TrusteeViewSet.as_view({'get': 'list'})
        res = list_view(request)
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_add(self):
        # Not allowed
        data = {
            'name': 'New trustee',
            'description': 'A trustee for testing purposes',
            'code': 'nt',
        }
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 405)
        self.user = User.objects.get(pk=self.user.pk)

    def test_update(self):
        # No permission
        res = self.client.patch(self.url_detail, {'name': 'ChangedTrustee'})
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.members.add(self.user)
        res = self.client.patch(self.url_detail, {'name': 'ChangedTrustee'})
        self.assertContains(res, 'ChangedTrustee')
        self.user = User.objects.get(pk=self.user.pk)

    def test_delete(self):
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.members.add(self.user)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        self.user = User.objects.get(pk=self.user.pk)

    def test_read_only_fields(self):
        self.obj.members.add(self.user)
        res = self.client.patch(self.url_detail, {'code': '001'})
        self.assertEqual(res.json()['code'], 'abc')
        self.user = User.objects.get(pk=self.user.pk)


class OriginalWorkTests(APITests):
    basename = 'originalwork'

    @classmethod
    def setUpTestData(cls):
        cls.factory = test.APIRequestFactory()
        cls.obj = factories.create_work(segments=2, translations=0)['original']
        cls.user = UserFactory()
        # group_name = '{}-staff'.format(cls.obj.trustee.code)
        # cls.staff = Group.objects.get(name=group_name)
        cls.data = {
            'url': cls.get_url('detail', cls.obj.pk),
            'id': cls.obj.pk,
            'title': cls.obj.title,
            'subtitle': cls.obj.subtitle,
            'abbreviation': cls.obj.abbreviation,
            'type': cls.obj.type,
            'description': cls.obj.description,
            'language': cls.obj.language,
            'trustee': cls.get_url('trustee-detail', cls.obj.trustee_id),
            'private': cls.obj.private,
            'author': cls.get_url('author-detail', cls.obj.author_id),
            'published': cls.obj.published,
            'edition': cls.obj.edition,
            'licence': cls.get_url('licence-detail', cls.obj.licence_id),
            'isbn': cls.obj.isbn,
            'publisher': cls.obj.publisher,
            'tags': [],
            # 'tableOfContents': list(cls.obj.table_of_contents),
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        # GET is allowed
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 200)
        res = self.client.post(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        request = self.factory.get(self.url_list)
        list_view = views.OriginalWorkViewSet.as_view({'get': 'list'})
        res = list_view(request)
        res = self.client.get(self.url_list)
        res_data = res.json()['results'][0]
        res_data.pop('tableOfContents')
        self.assertEqual(res_data, self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        res_data = res.json()
        res_data.pop('tableOfContents')
        self.assertEqual(res_data, self.data)

    def test_add(self):
        trustee = factories.TrusteeFactory()
        author = factories.AuthorFactory()
        licence = factories.LicenceFactory()
        data = {
            'title': 'New Book',
            'subtitle': 'A book to be translated by lorem',
            'abbreviation': 'nob',
            'type': 'book',
            'description': 'Description of the test book.',
            'language': 'en',
            'trustee': self.get_url('trustee-detail', trustee.pk),
            # 'trustee': {'id': trustee.pk},
            'private': False,
            'author': self.get_url('author-detail', author.pk),
            'published': 1999,
            'edition': 'first',
            'licence': self.get_url('licence-detail', licence.pk),
            'isbn': '1234-5678-9',
            'publisher': 'Test Printing',
        }
        # No permission
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {'trustee': ['You do not have permission to select this trustee.']},
        )
        # Permission
        trustee.members.add(self.user)
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 201)
        self.user = User.objects.get(pk=self.user.pk)

    def test_update(self):
        # No permission
        res = self.client.patch(self.url_detail, {'title': 'Changed Book'})
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.trustee.members.add(self.user)
        res = self.client.patch(self.url_detail, {'title': 'Changed Book'})
        self.assertContains(res, 'Changed Book')
        self.user = User.objects.get(pk=self.user.pk)

    def test_delete(self):
        # They protect the work
        self.obj.segments.all().delete()
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.trustee.members.add(self.user)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        self.user = User.objects.get(pk=self.user.pk)

    def test_read_only_fields(self):
        self.obj.trustee.members.add(self.user)
        res = self.client.patch(self.url_detail, {'abbreviation': 'ooo'})
        self.assertEqual(res.json()['abbreviation'], self.obj.abbreviation)
        self.user = User.objects.get(pk=self.user.pk)

    def test_queryset_limitation_trustee(self):
        trustee = factories.TrusteeFactory()
        foreign_trustee = factories.TrusteeFactory()
        # group_name = '{}-staff'.format(trustee.code)
        # self.user.groups.add(self.staff, Group.objects.get(name=group_name))
        self.obj.trustee.members.add(self.user)
        trustee.members.add(self.user)
        # Permission
        res = self.client.patch(
            self.url_detail,
            {'trustee': self.get_url('trustee-detail', trustee.pk)},
        )
        self.assertEqual(res.status_code, 200)
        # No permission
        res = self.client.patch(
            self.url_detail,
            {'trustee': self.get_url('trustee-detail', foreign_trustee.pk)},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {'trustee': ['You do not have permission to select this trustee.']},
        )

    def test_table_of_contents(self):
        res = self.client.get(self.url_detail)
        res_data = res.json()
        expected = {
            'id',
            'position',
            'number',
            'content',
            'tag',
            'classes',
            'limit',
            'url',
        }
        self.assertEqual(set(res_data['tableOfContents'][0].keys()), expected)


class TranslatedWorkTests(APITests):
    basename = 'translatedwork'

    @classmethod
    def setUpTestData(cls):
        cls.factory = test.APIRequestFactory()
        cls._user = UserFactory()
        cls.owork = factories.OriginalWorkFactory(
            title='Orig', published=1999, segments='h3 p'
        )
        cls.trustee = cls.owork.trustee
        cls.obj = factories.TranslatedWorkFactory(
            title='my lovely book',
            abbreviation='MLB',
            type='book',
            language='de',
            original=cls.owork,
            trustee=cls.trustee,
        )
        factories.TranslatedWorkFactory(
            title='a and MLB',
            abbreviation='a',
            type='periodical',
            language='sw',
            original=cls.owork,
            trustee=cls.trustee,
        )
        # group_name = '{}-staff'.format(cls.obj.trustee.code)
        # cls.staff = Group.objects.get(name=group_name)
        cls.data = {
            'url': cls.get_url('detail', cls.obj.pk),
            'id': cls.obj.pk,
            'title': 'my lovely book',
            'subtitle': cls.obj.subtitle,
            'abbreviation': 'MLB',
            'description': cls.obj.description,
            'language': {
                'code': 'de',
                'name': LANGUAGES_DICT[cls.obj.language],
                'rtl': False,
            },
            'type': cls.obj.type,
            'trustee': cls.get_url('trustee-detail', cls.trustee.pk),
            'private': cls.obj.private,
            'original': {
                'url': cls.get_url('originalwork-detail', cls.owork.pk),
                'title': cls.owork.title,
                'key': '',
            },
            'requiredApprovals': cls.obj.required_approvals,
            'protected': cls.obj.protected,
            'author': cls.obj.original.author.name,
            # 'tableOfContents': list(cls.obj.table_of_contents),
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
            'tags': [],
            'statistics': {
                'pretranslated': 0,
                'translationDone': 0,
                'reviewDone': 0,
                'trusteeDone': 0,
                'contributors': 0,
                'segments': 2,
            },
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.user = deepcopy(self._user)
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        # GET is allowed
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 200)
        res = self.client.post(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        request = self.factory.get(self.url_list)
        list_view = views.TranslatedWorkViewSet.as_view({'get': 'list'})
        res = list_view(request)
        with self.assertNumQueries(7):
            res = self.client.get(self.url_list, {'ordering': '-title'})
        results = res.json()['results']
        self.assertEqual(len(results), 2)
        res_data = results[0]
        res_data.pop('tableOfContents')
        self.assertEqual(res_data, self.data)

    def test_list_with_dummy_work(self):
        original = deepcopy(self.owork)
        original.id = None
        original.title = 'Dummy'
        original.abbreviation = 'Du'
        original.save()
        original.segments.set(models.OriginalSegment.objects.all())
        tag = models.Tag.objects.create(
            name='Growing Together Series', slug='gts'
        )
        original.tags.add(tag)
        res = self.client.get(self.url_list)
        self.assertEqual(len(res.json()['results']), 2)
        params = {'language': self.obj.language}
        res = self.client.get(self.url_list, params)
        self.assertEqual(len(res.json()['results']), 2)
        work_1, work_2 = res.json()['results']
        work_1.pop('tableOfContents')
        self.assertEqual(work_1, self.data)
        contents = work_2.pop('tableOfContents')
        data = self.data.copy()
        data.update(
            {
                'url': self.get_url('detail', original.pk),
                'id': original.pk,
                'title': 'Dummy',
                'subtitle': original.subtitle,
                'abbreviation': 'Du',
                'original': {
                    'url': self.get_url('originalwork-detail', original.pk),
                    'title': original.title,
                    'key': '',
                },
                'protected': True,
                'requiredApprovals': {
                    'translator': 0,
                    'reviewer': 0,
                    'trustee': 0,
                },
                'lastModified': self.date(original.last_modified),
                'created': self.date(original.created),
                'tags': ['Growing Together Series'],
            }
        )
        self.assertEqual(work_2, data)
        if contents:
            for heading in contents:
                self.assertEqual(heading['segments'], 0)
                self.assertEqual(heading['translationDone'], 0)
                self.assertEqual(heading['reviewDone'], 0)
                self.assertEqual(heading['trusteeDone'], 0)

        # Protected filter
        params['protected'] = True
        res = self.client.get(self.url_list, params)
        # Only the dummy work has protected == True
        self.assertEqual(len(res.json()['results']), 1)
        params['protected'] = False
        res = self.client.get(self.url_list, params)
        self.assertEqual(len(res.json()['results']), 1)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        res_data = res.json()
        res_data.pop('tableOfContents')
        self.assertEqual(res_data, self.data)

    def test_add(self):
        # Permission
        res = self.client.post(self.url_list, {})
        self.assertEqual(res.status_code, 400)

    def test_update_put(self):
        # No permission
        res = self.client.put(self.url_detail, self.data)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.trustee.members.add(self.user)
        res = self.client.put(self.url_detail, self.data)
        self.assertEqual(res.status_code, 200)

    def test_update_patch(self):
        self.obj.trustee.members.add(self.user)
        res = self.client.patch(self.url_detail, {'title': 'My first book'})
        self.assertEqual(res.status_code, 200)
        work = models.TranslatedWork.objects.filter(title='My first book')
        self.assertTrue(work.exists())

    def test_delete(self):
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.trustee.members.add(self.user)
        # Protected by segments
        with self.assertRaises(ProtectedError):
            res = self.client.delete(self.url_detail)
            self.assertEqual(res.status_code, 400)
        self.obj.segments.all().delete()
        # Success
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)

    def test_filters_endpoint(self):
        tag = models.Tag.objects.create(
            name='Growing Together Series', slug='gts'
        )
        original = deepcopy(self.owork)
        original.tags.add(tag)
        works = (
            factories.OriginalWorkFactory.build(
                type='manuscript',
                published=2020,
                author=self.owork.author,
                trustee=self.trustee,
                licence=self.owork.licence,
            ),
            factories.OriginalWorkFactory.build(
                type='periodical',
                published=None,
                author=self.owork.author,
                trustee=self.trustee,
                licence=self.owork.licence,
            ),
        )
        models.OriginalWork.objects.bulk_create(works)
        factories.TranslatedWorkFactory(
            language='sw',
            type='periodical',
            original=works[1],
            trustee=self.trustee,
        )
        self.obj.tags.add(factories.TagFactory(name='T2', slug='t2'))
        url = reverse('work_filters')

        # No language
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        expected = {
            'types': [
                {'slug': 'book', 'name': 'Book', 'count': 1},
                {'slug': 'periodical', 'name': 'Periodical', 'count': 2},
                {'slug': 'manuscript', 'name': 'Manuscript', 'count': 0},
            ],
            'tags': [
                {'slug': 'gts', 'name': 'Growing Together Series'},
                {'slug': 't2', 'name': 'T2'},
            ],
            'years': {'min': 1999, 'max': 1999},
        }
        self.assertEqual(res.json(), expected)

        # German
        res = self.client.get(url, {'language': 'de'})
        expected['types'][1]['count'] = 0
        self.assertEqual(res.json(), expected)

        # Swahili
        res = self.client.get(url, {'language': 'sw'})
        expected['types'][0]['count'] = 0
        expected['types'][1]['count'] = 2
        expected['tags'] = [expected['tags'][0]]
        self.assertEqual(res.json(), expected)

        # Turkish
        res = self.client.get(url, {'language': 'tr'})
        expected['types'][0]['count'] = 0
        expected['types'][1]['count'] = 0
        expected['tags'] = []
        expected['years'] = {'min': None, 'max': None}
        self.assertEqual(res.json(), expected)

    def test_tags(self):
        tags = factories.TagFactory.create_batch(3)
        self.obj.tags.set(tags[:2])
        self.owork.tags.set(tags[1:])
        res = self.client.get(self.url_detail)
        self.assertEqual(set(res.json()['tags']), {t.name for t in tags})

    def test_table_of_contents(self):
        res = self.client.get(self.url_detail)
        res_data = res.json()
        expected = {
            'firstPosition',
            'position',
            'number',
            'content',
            'tag',
            'url',
            'pretranslated',
            'translationDone',
            'reviewDone',
            'trusteeDone',
            'segments',
        }
        table_of_contents = res_data['tableOfContents'][0]
        self.assertEqual(set(table_of_contents.keys()), expected)
        self.assertEqual(
            table_of_contents['url'],
            f'{self.url_detail}segments/?limit=2&position=1',
        )

    # Filters

    def test_filters(self):
        """
        Tests that filters are ANDed and that 'abbreviation' is
        case-insensitive.
        """
        models.TranslatedWork.objects.filter(pk=self.obj.pk).update(
            abbreviation='A', language='tr'
        )
        res = self.client.get('{}?abbreviation=a'.format(self.url_list))
        self.assertEqual(len(res.json()['results']), 2)
        res = self.client.get(
            self.url_list, {'abbreviation': 'a', 'language': 'sw'}
        )
        self.assertEqual(len(res.json()['results']), 1)

    def test_filter_type(self):
        res = self.client.get(f'{self.url_list}?type=book')
        self.assertEqual(len(res.json()['results']), 1)
        res = self.client.get(f'{self.url_list}?type=book&type=periodical')
        self.assertEqual(len(res.json()['results']), 2)

    def test_filter_published(self):
        res = self.client.get(self.url_list, {'published_min': 1999})
        self.assertEqual(len(res.json()['results']), 2)
        res = self.client.get(self.url_list, {'published_max': 1998})
        self.assertEqual(len(res.json()['results']), 0)

    def test_filter_tag(self):
        tags = (
            models.Tag(name='Growing Together Series', slug='gts'),
            models.Tag(name='Tag 2', slug='t2'),
        )
        models.Tag.objects.bulk_create(tags)
        tags[0].originalworks.add(self.owork)
        tags[1].translatedworks.add(self.obj)

        # Original and translation
        res = self.client.get(f'{self.url_list}?tag=gts&tag=t2')
        self.assertEqual(len(res.json()['results']), 2)

        # Translation only
        res = self.client.get(f'{self.url_list}?tag=t2')
        self.assertEqual(len(res.json()['results']), 1)

    def test_custom_boolean_filters(self):
        models.WorkStatistics.objects.filter(work=self.obj).update(
            translated_percent=100, reviewed_percent=50
        )
        url = self.url_list
        res = self.client.get(f'{url}?is_translated=true&is_reviewed=false')
        self.assertEqual(len(res.json()['results']), 1)
        res = self.client.get(
            f'{url}?is_authorized=true&is_pretranslated=false'
        )
        self.assertEqual(len(res.json()['results']), 0)

    def test_custom_orderings(self):
        models.WorkStatistics.objects.filter(work=self.obj).update(
            translated_percent=10, reviewed_percent=5, authorized_percent=1
        )
        models.WorkStatistics.objects.exclude(work=self.obj).update(
            reviewed_percent=6
        )
        url = self.url_list

        # Statistics
        res = self.client.get(f'{url}?ordering=-translated,segments')
        results = res.json()['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], self.obj.pk)

        res = self.client.get(
            f'{url}?ordering=reviewed,contributors,pretranslated'
        )
        self.assertEqual(res.json()['results'][0]['id'], self.obj.pk)

        res = self.client.get(f'{url}?ordering=authorized,last_activity')
        self.assertEqual(res.json()['results'][1]['id'], self.obj.pk)

        # Priority
        tag = models.Tag.objects.create(name='P', slug='priority')
        # Tagged originals should not be respected (should not be needed and
        # simplifies the query a bit)
        tag.originalworks.add(self.owork)
        tag.translatedworks.add(self.obj)
        res = self.client.get(url, {'ordering': 'priority'})
        results = res.json()['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], self.obj.pk)

        res = self.client.get(url, {'ordering': '-priority'})
        results = res.json()['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]['id'], self.obj.pk)

    # Search

    def test_search_abbreviation(self):
        res = self.client.get(self.url_list, {'search': 'mlb'})
        results = res.json()['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['abbreviation'], 'MLB')

        res = self.client.get(self.url_list, {'search': 'ml'})
        self.assertEqual(len(res.json()['results']), 0)

    def test_search_translated_title(self):
        res = self.client.get(self.url_list, {'search': 'BOOK'})
        self.assertEqual(len(res.json()['results']), 1)

    def test_search_original_title(self):
        res = self.client.get(self.url_list, {'search': 'orig'})
        self.assertEqual(len(res.json()['results']), 2)

    def test_search_other_language(self):
        models.TranslatedWork.objects.filter(pk=self.obj.pk).update(title='၂၈')
        res = self.client.get(self.url_list, {'search': '၂၈'})
        self.assertEqual(len(res.json()['results']), 1)

    # Other

    def test_read_only_fields(self):
        self.obj.trustee.members.add(self.user)
        data = {
            'abbreviation': 'ooo',
            'type': 'x',
            'language': 'xx',
            'trustee': 99,
            'private': True,
            'original': 1001,
            'protected': 'yes',
        }
        res = self.client.patch(self.url_detail, data)
        for key in data.keys():
            value = getattr(self.obj, key)
            if key == 'trustee':
                value = self.get_url('trustee-detail', value.pk)
            elif key == 'original':
                value = {
                    'url': self.get_url('originalwork-detail', value.pk),
                    'title': value.title,
                    'key': '',
                }
            elif key == 'language':
                value = {
                    'code': value,
                    'name': LANGUAGES_DICT[value],
                    'rtl': False,
                }
            self.assertEqual(res.json()[key], value)


class TranslatedSegmentSwitchedTests(APITests):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.another_user = UserFactory()
        cls.works = factories.create_work(
            segments=2, translations=1, additional_languages=False
        )
        cls.segments = tuple(
            cls.works['translations'][0]
            .segments.select_related('chapter')
            .all()
        )
        cls._segment_1 = cls.segments[0]
        cls._segment_2 = cls.segments[1]
        Reputation.objects.update_or_create(
            user=cls.user,
            language=cls.works['translations'][0].language,
            defaults={'score': PERMISSIONS['change_translation']},
        )
        cls.data = {
            'priorSegmentId': cls._segment_1.pk,
            'currentSegmentId': cls._segment_2.pk,
        }
        cls.url = cls.get_url(
            'translatedwork-switched-segments', cls.works['translations'][0].pk
        )

    def get_response(self, *, prior=True, current=True, **statistics):
        if prior:
            if self.segment_1.content:
                reviewer_can_vote = True
            else:
                reviewer_can_vote = False
            prior = self.get_segment(
                self.segment_1,
                reviewer_can_vote=reviewer_can_vote,
                **statistics,
            )
            # Should always be None
            prior['lockedBy'] = None
            if not statistics:
                del prior['statistics']
        else:
            prior = 'Prior segment not specified or not part of the work.'
        if current:
            if self.segment_2.content:
                reviewer_can_vote = True
            else:
                reviewer_can_vote = False
            current = self.get_segment(
                self.segment_2, reviewer_can_vote=reviewer_can_vote
            )
            if not statistics:
                del current['statistics']
        else:
            current = 'Current segment not specified or not part of the work.'
        return {'prior': prior, 'current': current}

    def setUp(self):
        self.segment_1 = deepcopy(self._segment_1)
        self.segment_2 = deepcopy(self._segment_2)
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.post(self.url, self.data)
        self.assertEqual(res.status_code, 401)

    def test_method_not_allowed(self):
        res = self.client.get(self.url, self.data)
        self.assertEqual(res.status_code, 405)

    def test_both_segments_valid(self):
        self.segment_1.locked_by = self.user
        self.segment_1.save_without_historical_record()
        with self.assertNumQueries(10):
            res = self.client.post(self.url, self.data)
        self.assertEqual(res.status_code, 200)
        self.segment_1.refresh_from_db()
        self.assertEqual(res.json(), self.get_response())
        self.assertIsNone(self.segment_1.locked_by)

    def test_no_current_segment(self):
        self.segment_1.locked_by = self.user
        self.segment_1.save_without_historical_record()
        data = self.data.copy()
        # None
        data['currentSegmentId'] = None
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 200)
        self.segment_1.refresh_from_db()
        self.assertEqual(res.json(), self.get_response(current=False))
        self.segment_1.locked_by = self.user
        self.segment_1.save_without_historical_record()
        # Missing
        del data['currentSegmentId']
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 200)
        self.segment_1.refresh_from_db()
        self.assertEqual(res.json(), self.get_response(current=False))
        self.assertIsNone(self.segment_1.locked_by)

    def test_no_prior_segment(self):
        data = self.data.copy()
        del data['priorSegmentId']
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.get_response(prior=False))

    def test_current_segment_does_not_exist(self):
        self.segment_1.locked_by = self.user
        self.segment_1.save_without_historical_record()
        data = self.data.copy()
        data['currentSegmentId'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 200)
        self.segment_1.refresh_from_db()
        self.assertEqual(res.json(), self.get_response(current=False))
        self.assertIsNone(self.segment_1.locked_by)

    def test_current_segment_invalid(self):
        data = self.data.copy()
        data['currentSegmentId'] = 'invalid'
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'currentSegmentId': ['A valid integer is required.']}
        )

    def test_prior_segment_does_not_exist(self):
        data = self.data.copy()
        data['priorSegmentId'] = -4
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.get_response(prior=False))

    def test_prior_segment_invalid(self):
        data = self.data.copy()
        data['priorSegmentId'] = '-'
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'priorSegmentId': ['A valid integer is required.']}
        )

    def test_prior_segment_not_locked(self):
        res = self.client.post(self.url, self.data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.get_response())

    def test_prior_segment_locked_by_another_user(self):
        self.segment_1.locked_by = self.another_user
        self.segment_1.save_without_historical_record()
        res = self.client.post(self.url, self.data)
        self.assertEqual(res.status_code, 200)
        expected = self.get_response()
        expected['prior']['lockedBy'] = self.get_user_field(self.another_user)
        self.assertEqual(res.json(), expected)
        self.segment_1.refresh_from_db()
        self.assertEqual(self.segment_1.locked_by_id, self.another_user.pk)

    def test_update_history_correctly(self):
        history = models.TranslatedSegment.history.filter(id=self.segment_1.pk)
        self.assertFalse(history.exists())
        self.segment_1._history_user = self.user
        self.segment_1.save()
        self.segment_1._history_user = self.another_user
        self.segment_1.save()
        self.segment_1._history_user = self.user
        self.segment_1.changeReason = 'test'
        self.segment_1.content = 'I love writing text'
        self.segment_1.save()
        self.segment_1.content = 9 * 'I love writing text but tests not so much'
        self.segment_1.locked_by = self.user
        self.segment_1.save_without_historical_record()
        history = models.TranslatedSegment.history.filter(id=self.segment_1.pk)
        self.assertEqual(history.count(), 3)
        self.assertEqual(history.latest().history_change_reason, 'test')
        res = self.client.post(self.url, self.data)
        self.assertEqual(res.status_code, 200)
        self.segment_1.refresh_from_db()
        expected = self.get_response()
        expected['prior'].update(
            {
                'content': 9 * 'I love writing text but tests not so much',
                'progress': TRANSLATION_DONE,
            }
        )
        self.assertEqual(res.json(), expected)
        history = models.TranslatedSegment.history.filter(id=self.segment_1.pk)
        # The last history entry should be updated
        self.assertEqual(history.count(), 3)
        most_recent = history.latest()
        self.assertEqual(most_recent.history_user.pk, self.user.pk)
        self.assertEqual(most_recent.history_change_reason, 'New translation')

    def test_included_statistics(self):
        self.segment_1.content = 't'
        self.segment_1.locked_by = self.user
        self.segment_1.progress = IN_TRANSLATION
        self.segment_1.save_without_historical_record()
        res = self.client.post(self.url, self.data)
        self.segment_1.refresh_from_db()
        self.assertEqual(res.json(), self.get_response(records=1))


class OriginalSegmentTests(APITests):
    basename = 'originalsegment'

    @classmethod
    def setUpTestData(cls):
        cls.obj = factories.OriginalSegmentFactory()
        cls._user = UserFactory()
        # group_name = '{}-staff'.format(cls.obj.work.trustee.code)
        # cls.staff = Group.objects.get(name=group_name)
        cls.data = {
            'id': cls.obj.pk,
            # 'url': cls.get_url(
            #    cls, 'detail', cls.obj.work.pk, cls.obj.position),
            'position': cls.obj.position,
            'page': cls.obj.page,
            'tag': cls.obj.tag,
            'classes': cls.obj.classes,
            'work': cls.obj.work_id,
            'content': cls.obj.content,
            'reference': cls.obj.reference,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list', cls.obj.work_id)
        cls.url_detail = cls.get_url(
            'detail', cls.obj.work_id, cls.obj.position
        )

    def setUp(self):
        self.user = deepcopy(self._user)
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        data = self.data.copy()
        # Not allowed
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 405)
        return  # todo
        # Permission
        self.user.groups.add(self.staff)
        with self.assertRaises(IntegrityError):
            # `position` is a read only field but required
            res = self.client.post(self.url_list, data)
            self.assertEqual(res.status_code, 201)

    def test_update_put(self):
        # No permission
        res = self.client.put(self.url_detail, self.data)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.obj.work.trustee.members.add(self.user)
        res = self.client.put(self.url_detail, self.data)
        self.assertEqual(res.status_code, 200)

    def test_update_patch(self):
        self.obj.work.trustee.members.add(self.user)
        res = self.client.patch(
            self.url_detail, {'content': 'Dear <em>reader</em>,'}
        )
        self.assertEqual(res.status_code, 200)

    def test_delete(self):
        # Not allowed
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 405)

    def test_read_only_fields(self):
        self.obj.work.trustee.members.add(self.user)
        data = {
            'position': 100,
            'page': 200,
            'tag': 'xx',
            'classes': ['p'],
            'content': 'text',
            'reference': 'x1',
            'work': 300,
        }
        res = self.client.patch(self.url_detail, data)
        for key in data.keys():
            value = getattr(self.obj, key)
            if key == 'work':
                value = value.pk
            self.assertEqual(res.json()[key], value)


class TranslatedSegmentTests(APITests):
    basename = 'translatedsegment'

    @classmethod
    def setUpTestData(cls):
        cls.original_work = factories.OriginalWorkFactory()
        cls.work = factories.TranslatedWorkFactory(
            original=cls.original_work, language='tr'
        )
        cls._obj = factories.TranslatedSegmentFactory(
            progress=IN_TRANSLATION,
            original=factories.OriginalSegmentFactory(work=cls.original_work),
            work=cls.work,
        )
        # Setting this attribute makes also sure that lastEditedBy is correct,
        # i.e. None (see get_segment)
        cls.record = cls._obj.history.get()
        tag = Tag.objects.create(name=cls._obj.tag)
        for cls in cls._obj.classes:
            Class.objects.create(name=cls, tag=tag)
        cls.user, cls.user_2 = UserFactory.create_batch(2)
        cls.data = cls.get_segment(records=1)
        cls.url_list = cls.get_url('list', cls._obj.work_id)
        cls.url_detail = cls.get_url(
            'detail', cls._obj.work_id, cls._obj.position
        )
        cls.url_restore = cls.get_url(
            'restore', cls._obj.work_id, cls._obj.position
        )

    def setUp(self):
        self.obj = deepcopy(self._obj)
        self.client.force_login(self.user)

    # Authentication

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)

    # Read

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_list_without_histroical_record(self):
        self.obj.history.all().delete()
        res = self.client.get(self.url_list)
        data = deepcopy(self.data)
        data['statistics']['records'] = 0
        data['statistics']['lastEdited'] = None
        self.assertEqual(res.json()['results'][0], data)

    def test_retrieve(self):
        with self.assertNumQueries(4):
            res = self.client.get(self.url_detail)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), self.data)

    def test_retrieve_segment_of_right_work(self):
        segment_of_another_work = factories.TranslatedSegmentFactory(
            work__language='tr'
        )
        res = self.client.get(self.url_detail)
        self.assertEqual(res.json(), self.data)
        res = self.client.get(
            self.get_url(
                'detail',
                segment_of_another_work.work_id,
                segment_of_another_work.position,
            )
        )
        data = res.json()
        self.assertEqual(data['work'], segment_of_another_work.work_id)
        self.assertEqual(data['content'], segment_of_another_work.content)

    def test_ai_translation(self):
        # todo: rename the field "ai" to "base" or something
        base_translator = models.BaseTranslator.objects.create(
            name='Test AI', type='ai'
        )
        base_translation = models.BaseTranslation.objects.create(
            translator=base_translator, language='tr'
        )
        models.BaseTranslation.objects.create(
            translator=base_translator, language='fr'
        )
        models.BaseTranslationSegment.objects.create(
            original_id=self.obj.original_id,
            translation=base_translation,
            content='Artificially translated',
        )
        data = self.data.copy()
        data['ai'] = {
            'translator': 'Test AI',
            'info': (
                'This translation was created by Test AI, an artificial '
                'intelligence.'
            ),
            'content': 'Artificially translated',
        }
        with self.assertNumQueries(4):
            res = self.client.get(self.url_detail)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), data)

        # Human being
        base_translator.type = 'hb'
        base_translator.save()
        data['ai']['info'] = 'This translation was created by a third party.'
        res = self.client.get(self.url_detail)
        self.assertEqual(res.json(), data)

        # Translation memory
        base_translator.type = 'tm'
        base_translator.save()
        data['ai']['info'] = (
            'This translation comes from the translation memory. That means '
            'the same or similar text was translated elsewhere already.'
        )
        res = self.client.get(self.url_detail)
        self.assertEqual(res.json(), data)

    def test_can_edit(self):
        res = self.client.get(self.url_detail)
        response_json = res.json()
        self.assertEqual(response_json['translatorCanEdit'], True)
        self.assertEqual(response_json['reviewerCanEdit'], True)

        self.obj.progress = IN_REVIEW
        self.obj.save_without_historical_record()
        res = self.client.get(self.url_detail)
        response_json = res.json()
        self.assertEqual(response_json['translatorCanEdit'], False)
        self.assertEqual(response_json['reviewerCanEdit'], True)

        self.create_vote(role='trustee')
        res = self.client.get(self.url_detail)
        response_json = res.json()
        self.assertEqual(response_json['translatorCanEdit'], False)
        self.assertEqual(response_json['reviewerCanEdit'], False)

    def test_can_vote(self):
        self.obj.progress = IN_REVIEW
        self.obj.save_without_historical_record()
        res = self.client.get(self.url_detail)
        response_json = res.json()
        self.assertEqual(response_json['reviewerCanVote'], True)
        self.assertEqual(response_json['trusteeCanVote'], False)

        models.Vote.objects.bulk_create(
            (
                self.create_vote(value=-1, save=False),
                self.create_vote(role='reviewer', save=False),
                self.create_vote(role='reviewer', user=self.user_2, save=False),
            )
        )
        res = self.client.get(self.url_detail)
        response_json = res.json()
        self.assertEqual(response_json['reviewerCanVote'], False)
        self.assertEqual(response_json['trusteeCanVote'], True)

    def test_statistics(self):
        user = self.user_2
        comments = factories.SegmentCommentFactory.create_batch(
            3, work=self.work, position=self.obj.position, user=user
        )
        # Deleted segments should be excluded
        factories.SegmentCommentFactory(
            work=self.work,
            position=self.obj.position,
            user=user,
            to_delete=timezone.now() + datetime.timedelta(1),
        )
        another_comment = factories.SegmentCommentFactory(
            work=self.work, position=self.obj.position + 1, user=self.user
        )
        # Create this comment last to test that it isn't used for
        # lastCommented
        factories.SegmentCommentFactory(position=self.obj.position, user=user)
        self.obj.progress = IN_TRANSLATION
        self.obj._history_user = self.user
        self.obj.save()
        votes = [self.create_vote(role='trustee', value=-1, save=False)]

        def build_votes(role, accumulated_vote, vote_user):
            current_vote = 0
            count = 0
            while accumulated_vote != current_vote:
                if count < 4:
                    value = random.choice((-2, -1, 1, 2))
                else:
                    value = 1 if current_vote < accumulated_vote else -1
                votes.append(
                    self.create_vote(
                        user=vote_user, role=role, value=value, save=False
                    )
                )
                current_vote += value
                count += 1

        build_votes('translator', 2, user)
        build_votes('reviewer', 2, user)
        build_votes('trustee', 5, user)
        build_votes('translator', -1, self.user)
        build_votes('reviewer', 1, self.user)
        build_votes('trustee', 1, self.user)
        models.Vote.objects.bulk_create(votes)

        data = self.data.copy()
        data['statistics'] = {
            'comments': 3,
            'lastCommented': self.date(comments[-1].created),
            'records': 2,
            'lastEdited': self.date(self.obj.history.latest().history_date),
            'lastEditedBy': self.get_user_field(edits=1),
            'translators': {'vote': 1, 'user': -1},
            'reviewers': {'vote': 3, 'user': 1},
            'trustees': {'vote': 5, 'user': 0},
        }
        data['lastModified'] = self.date(self.obj.last_modified)
        data['translatorCanEdit'] = False
        data['reviewerCanEdit'] = False
        data['trusteeCanVote'] = True
        # The progress isn't updated because this is done in the endpoint logic
        queries = 4
        with self.assertNumQueries(queries):
            res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], data)

        (
            models.Vote.objects.filter(segment=self.obj, role='trustee')
            .exclude(pk=votes[0].pk)
            .delete()
        )
        data['statistics']['trustees'] = {'vote': -1, 'user': -1}
        # Make sure queries don't increase with multiple segments
        original = factories.OriginalSegmentFactory(
            work=self.original_work, position=2
        )
        segment = factories.TranslatedSegmentFactory.build(
            work=self.work, original=original, position=original.position
        )
        segment._history_user = user
        segment.save()
        with self.assertNumQueries(queries):
            res = self.client.get(self.url_list)
        data['reviewerCanEdit'] = True
        self.assertEqual(res.json()['results'][0], data)
        expected = {
            'comments': 1,
            'lastCommented': self.date(another_comment.created),
            'records': 1,
            'lastEdited': self.date(segment.history.latest().history_date),
            'lastEditedBy': self.get_user_field(user, edits=1),
            'translators': {'vote': 0, 'user': 0},
            'reviewers': {'vote': 0, 'user': 0},
            'trustees': {'vote': 0, 'user': 0},
        }
        self.assertEqual(res.json()['results'][1]['statistics'], expected)

    # Create

    def test_create(self):
        self.set_reputation('add_translation')
        res = self.client.post(self.url_list, {})
        self.assertEqual(res.status_code, 405)

    # Update

    def test_put(self):
        """
        Put is not allowed.
        """
        self.set_reputation('trustee')
        res = self.client.put(self.url_detail, {})
        self.assertEqual(res.status_code, 403)

    # Edit content

    def test_edit_content_no_permission_reputation(self):
        self.set_reputation(0)
        data = {
            'content': 'different content',
            'lastModified': self.obj.last_modified,
        }
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)

    def test_edit_content_no_permission_protected(self):
        self.set_reputation('review_translation')
        data = {
            'content': 'different content',
            'lastModified': self.obj.last_modified,
        }
        models.TranslatedWork.objects.update(protected=True)
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)

    def test_edit_content_after_approvals_as_translator(self):
        votes = (
            self.create_vote(value=-1, save=False),
            self.create_vote(value=-1, role='reviewer', save=False),
            self.create_vote(value=-1, role='trustee', save=False),
            self.create_vote(save=False),
            self.create_vote(save=False),
        )
        models.Vote.objects.bulk_create(votes)

        data = {'content': '', 'lastModified': self.obj.last_modified}
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('statistics', res.json())

        # Reviewer vote
        reviewer_vote = self.create_vote(value=2, role='reviewer')
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)
        # Edited
        self.obj.content = 'changed'
        self.obj.progress = IN_REVIEW
        self.obj.save()
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)
        # Revoked
        # Not implemented so far. Maybe offer a button like "allow edits again".

        # Trustee vote
        self.create_vote(value=2, role='trustee')
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)
        # Trustee vote only
        reviewer_vote.delete()
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)

    def test_edit_content_after_approvals_as_non_translator(self):
        data = {'content': '', 'lastModified': timezone.now()}

        # As reviewer
        self.set_reputation('review_translation')

        # No vote
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('statistics', res.json())

        # Reviewer vote
        self.create_vote(role='reviewer')
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 200)
        # Edited
        self.obj.content = 'changed'
        self.obj.progress = IN_REVIEW
        self.obj.save()
        res = self.client.patch(self.url_detail, data)
        # Validation check was temporarily disabled
        # self.assertEqual(res.status_code, 400)
        self.assertEqual(res.status_code, 200)

        # Trustee vote
        self.create_vote(role='trustee')
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)

        # As trustee
        self.set_reputation('trustee')
        self.assertEqual(self.obj.votes.count(), 2)
        self.obj.progress = RELEASED
        self.obj.save_without_historical_record()
        data = {'content': 'This is better', 'lastModified': timezone.now()}
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['statistics']['reviewers']['vote'], 0)
        old_last_modified = self.obj.last_modified
        self.obj.refresh_from_db()
        self.assertLess(old_last_modified, self.obj.last_modified)
        # Now, it should be editable for reviewers, again
        self.assertEqual(self.obj.content, 'This is better')
        self.assertEqual(self.obj.votes.count(), 0)
        self.set_reputation('review_translation')
        res = self.client.patch(self.url_detail, data)
        # The segment is still locked by the user. Therefore, lastModified
        # isn't checked again
        self.assertEqual(res.status_code, 200)
        # But not for translators
        self.set_reputation('change_translation')
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 403)

    def test_edit_content_timestamp_outdated(self):
        # Validation check was temporarily disabled
        return
        timestamp = self.obj.last_modified - datetime.timedelta(minutes=9)
        res = self.client.patch(
            self.url_detail,
            {'content': 'different content', 'lastModified': timestamp},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Somebody worked on this text in the meantime. '
                    'Your data was just updated automatically.'
                ],
                'segment': self.get_segment(records=1),
            },
        )

    def test_edit_content(self):
        # Every call of `save` creates a historical record
        self.assertEqual(self.obj.history.count(), 1)

        queries = 12
        with self.assertNumQueries(queries):
            res = self.client.patch(
                self.url_detail,
                {
                    'content': 'different content',
                    'lastModified': self.obj.last_modified,
                },
            )
            self.assertEqual(res.status_code, 200)
        with self.assertNumQueries(queries):
            res = self.client.patch(
                self.url_detail,
                {
                    'content': 'more content',
                    'lastModified': self.obj.last_modified,
                },
            )
            self.assertEqual(res.status_code, 200)
        response_json = res.json()
        self.assertIn('lastModified', response_json)
        self.assertIn('lockedBy', response_json)
        self.assertEqual(response_json['content'], 'more content')
        drafts = models.SegmentDraft.objects.filter(owner_id=self.user.pk)
        drafts = list(drafts.order_by('-created'))
        self.assertEqual(len(drafts), 3)
        self.assertEqual(drafts[0].content, 'more content')
        self.assertEqual(drafts[1].content, 'different content')
        self.assertEqual(drafts[2].content, self.obj.content)
        self.assertGreater(drafts[0].created, drafts[1].created)
        self.assertGreater(drafts[1].created, drafts[2].created)
        self.assertEqual(self.obj.history.count(), 1)

        # Segment is locked
        self.client.force_login(self.user_2)
        res = self.client.patch(
            self.url_detail,
            {
                'content': self.obj.content,
                'lastModified': self.obj.last_modified,
            },
        )
        self.assertEqual(res.status_code, 400)
        self.obj.refresh_from_db()
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Currently somebody else works on this segment.'
                ],
                'segment': self.get_segment(self.obj, records=1),
            },
        )

    def test_edit_content_empty(self):
        res = self.client.patch(
            self.url_detail,
            {'content': '', 'lastModified': self.obj.last_modified},
        )
        self.assertEqual(res.status_code, 200)

    def test_edit_content_missing(self):
        res = self.client.patch(
            self.url_detail, {'lastModified': timezone.now()}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'content': ['This field is required.']})

    def test_edit_last_modified_missing(self):
        res = self.client.patch(self.url_detail, {'content': ''})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'lastModified': ['This field is required.']}
        )

    def test_edit_without_release_adds_votes_to_history(self):
        self.create_vote()
        # todo: reduce queries
        with self.assertNumQueries(16):
            res = self.client.patch(
                self.url_detail,
                {'content': 'new', 'lastModified': self.obj.last_modified},
            )
        self.assertEqual(res.status_code, 200)
        self.obj.refresh_from_db()
        self.assertTrue(self.obj.votes.exists())
        self.assertEqual(self.record.votes.count(), 1)

    # TODO 'can_edit' is patched because editing after release is not
    # implemented in permissions yet
    @patch('panta.models.TranslatedSegment.can_edit', lambda s, r: True)
    def test_edit_after_release_moves_votes_to_history(self):
        self.obj.progress = RELEASED
        self.obj.save_without_historical_record()
        self.create_vote()
        with self.assertNumQueries(19):
            res = self.client.patch(
                self.url_detail,
                {'content': 'new', 'lastModified': self.obj.last_modified},
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['statistics']['translators']['vote'], 0)
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.votes.exists())
        self.assertEqual(self.record.votes.count(), 1)

    def test_successive_spaces_are_removed(self):
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'we  want   you',
                'lastModified': self.obj.last_modified,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'we want you')

    def test_html_replace_b(self):
        Tag.objects.create(name='strong')
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'hello <b>Lini</b>',
                'lastModified': self.obj.last_modified,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'hello <strong>Lini</strong>')

    def test_validation_error_tag_not_allowed(self):
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'Headline<script>',
                'lastModified': self.obj.last_modified,
            },
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'content': [
                    'HTML tag "script" in "<script></script>" is not allowed.'
                ]
            },
        )
        self.obj.refresh_from_db()
        self.assertNotIn('<script', self.obj.content)

    def test_empty_draft_and_full_draft_in_one_historical_record(self):
        res = self.client.patch(
            self.url_detail,
            {'content': '', 'lastModified': self.obj.last_modified},
        )
        self.assertEqual(res.status_code, 200)
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'New translation',
                'lastModified': self.obj.last_modified,
            },
        )
        self.assertEqual(res.status_code, 200)
        management.Segments().conclude(models.TranslatedSegment.objects.all())
        history = tuple(self.obj.history.all())
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].content, 'New translation')
        self.assertEqual(history[0].history_user_id, self.user.pk)
        self.assertEqual(
            history[0].history_change_reason, CHANGE_REASONS['change']
        )
        self.assertEqual(history[1].content, self.obj.content)
        self.assertEqual(history[1].history_user, None)
        self.assertEqual(history[1].history_change_reason, None)

    def test_empty_draft_in_between(self):
        initial_content = self.obj.content
        res = self.client.patch(
            self.url_detail,
            {'content': 'Edit', 'lastModified': self.obj.last_modified},
        )
        self.assertEqual(res.status_code, 200)
        management.Segments().conclude(models.TranslatedSegment.objects.all())
        self.obj.refresh_from_db()
        res = self.client.patch(
            self.url_detail,
            {'content': 'Another Edit', 'lastModified': self.obj.last_modified},
        )
        self.assertEqual(res.status_code, 200)
        res = self.client.patch(
            self.url_detail,
            {'content': '', 'lastModified': self.obj.last_modified},
        )
        management.Segments().conclude(models.TranslatedSegment.objects.all())
        self.obj.refresh_from_db()
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'New translation',
                'lastModified': self.obj.last_modified,
            },
        )
        self.assertEqual(res.status_code, 200)
        management.Segments().conclude(models.TranslatedSegment.objects.all())
        history = tuple(self.obj.history.all())
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].content, 'New translation')
        self.assertEqual(history[0].history_user_id, self.user.pk)
        self.assertEqual(
            history[0].history_change_reason, CHANGE_REASONS['new']
        )
        self.assertEqual(history[1].content, '')
        self.assertEqual(history[1].history_user_id, self.user.pk)
        self.assertEqual(
            history[1].history_change_reason, CHANGE_REASONS['delete']
        )
        self.assertEqual(history[2].content, initial_content)
        self.assertEqual(history[2].history_user, None)
        self.assertEqual(history[2].history_change_reason, None)

    def test_read_only_fields(self):
        last_modified = self.obj.last_modified
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'write...',
                'lastModified': last_modified,
                'created': 0,
                'work': '-',
                'position': '-',
                'owner': '-',
            },
        )
        self.assertEqual(res.status_code, 200)
        self.obj.refresh_from_db()
        self.assertGreater(self.obj.last_modified, last_modified)

    # Delete

    def test_destroy(self):
        # Permission
        self.assertTrue(self.obj.content != '')
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        deleted_segment = models.TranslatedSegment.objects.get(pk=self.obj.pk)
        self.assertEqual(deleted_segment.content, '')
        self.assertEqual(self.obj.created, deleted_segment.created)
        self.assertTrue(self.obj.last_modified < deleted_segment.last_modified)
        self.assertEqual(self.obj.history.count(), 2)
        # No permission
        self.set_reputation(0)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)

    def test_destroy_no_content(self):
        """
        Shouldn't add a historical record.
        """
        self.obj.content = ''
        self.obj.save()
        self.set_reputation('delete_translation')
        self.assertEqual(self.obj.history.count(), 2)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self.obj.history.count(), 2)

    def test_destroy_locked_by_user_not_editing(self):
        self.set_reputation('delete_translation')
        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, '')
        self.assertEqual(self.obj.history.count(), 2)
        self.assertIsNone(self.obj.locked_by)

    def test_destroy_locked_by_user_while_editing(self):
        self.set_reputation('delete_translation')
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'Let me write something =)',
                'lastModified': self.date(self.obj.last_modified),
            },
        )
        self.assertEqual(res.status_code, 200)
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'Let me write something more...',
                'lastModified': self.date(self.obj.last_modified),
            },
        )
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, '')
        self.assertEqual(self.obj.history.count(), 2)
        delete_record = self.obj.history.latest()
        self.assertEqual(
            delete_record.history_change_reason, 'Clear translation'
        )
        self.assertEqual(delete_record.history_user_id, self.user.pk)
        management.Segments().conclude(models.TranslatedSegment.objects.all())
        self.assertEqual(self.obj.history.count(), 2)
        self.assertIsNone(self.obj.locked_by)
        res = self.client.patch(
            self.url_detail,
            {
                'content': 'Now I have a new chance ;-)',
                'lastModified': self.date(self.obj.last_modified),
            },
        )
        management.Segments().conclude(models.TranslatedSegment.objects.all())
        self.assertEqual(self.obj.history.count(), 3)

    def test_destroy_locked_by_another_user(self):
        self.set_reputation('delete_translation')
        self.obj.locked_by = self.user_2
        self.obj.save_without_historical_record()
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 400)
        self.obj.refresh_from_db()
        self.assertNotEqual(self.obj.content, '')
        self.assertEqual(self.obj.history.count(), 1)
        self.assertIsNotNone(self.obj.locked_by)

    # History

    def test_history(self):
        # Currently updates are not allowed
        # res = self.client.patch(
        #    self.url_detail,
        #    {'content': 'Dear <em>reader</em>,'},
        # )
        self.obj.content = 'Dear <em>reader</em>,'
        self.obj._history_user = self.user
        self.obj.save()

        vote = factories.VoteFactory(user=self.user)
        historical_obj = self.obj.history.latest()
        historical_obj.votes.add(vote)
        data = {
            'id': historical_obj.pk,
            'relativeId': 2,
            'date': self.date(historical_obj.history_date),
            'expires': self.date(
                historical_obj.history_date + HISTORICAL_UNIT_PERIOD
            ),
            'type': 'record',
            'changeReason': None,  # TODO
            'user': self.get_user_field(edits=1),
            'content': 'Dear <em>reader</em>,',
            'votes': [
                {
                    'id': vote.pk,
                    'type': 'vote',
                    'role': vote.role,
                    'action': vote.action,
                    'assessment': vote.assessment,
                    'date': self.date(vote.date),
                    'user': self.get_user_field(edits=1),
                }
            ],
        }
        res = self.client.get(
            self.get_url(
                'historicaltranslatedsegment-list',
                self.obj.work.pk,
                self.obj.position,
            )
        )
        # One object for creation, one for edit
        self.assertEqual(res.json()['count'], 2)
        self.assertEqual(res.json()['results'][0], data)
        self.assertEqual(res.json()['results'][1]['expires'], None)
        self.assertEqual(res.json()['results'][1]['relativeId'], 1)

    def test_history_login_required(self):
        self.client.logout()
        res = self.client.get(
            self.get_url(
                'historicaltranslatedsegment-list',
                self.obj.work.pk,
                self.obj.position,
            )
        )
        self.assertEqual(res.status_code, 401)

    def test_history_methods_not_allowed(self):
        # Post
        res = self.client.post(
            self.get_url(
                'historicaltranslatedsegment-list',
                self.obj.work.pk,
                self.obj.position,
            ),
            {},
        )
        self.assertEqual(res.status_code, 405)
        # Put, patch, delete
        with self.assertRaises(NoReverseMatch):
            self.get_url(
                'historicaltranslatedsegment-detail',
                self.obj.work.pk,
                self.obj.position,
                self.obj.history.first().pk,
            )

    def test_history_inactive_user(self):
        self.client.force_login(self.user_2)
        self.obj._history_user = self.user
        self.obj.save()
        self.user.is_active = False
        self.user.save_without_historical_record()
        res = self.client.get(
            self.get_url(
                'historicaltranslatedsegment-list',
                self.obj.work.pk,
                self.obj.position,
            )
        )
        history_user = {
            'id': None,
            'url': None,
            'username': '(deleted user)',
            'firstName': '',
            'lastName': '',
            'contributions': {},
            'thumbnail': self.get_svg_avatar(color='#e6e6e6'),
        }
        self.assertEqual(res.json()['results'][0]['user'], history_user)
        self.user.is_active = True

    def test_get_expires(self):
        serializer = serializers.TranslatedSegmentHistorySerializer()
        obj = self.obj.history.latest()

        self.assertIsNone(serializer.get_expires(obj))

        obj._most_recent = True
        self.assertEqual(
            serializer.get_expires(obj),
            obj.history_date + HISTORICAL_UNIT_PERIOD,
        )

        # A new historical segment is created when it has votes
        # even if they are 0 or negative!
        self.create_vote()
        self.assertIsNone(serializer.get_expires(obj))

    # Pagination

    def test_position_higher_than_count(self):
        """
        The model is a limit/offset pagination with `position` as offset.
        But it is no real offset, it's a database lookup field.
        """
        self.obj.position = 11
        self.obj.save_without_historical_record()
        res = self.client.get('{}?position=10'.format(self.url_list))
        results = res.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.obj.pk)

    def test_position_in_results_less_or_equal_limit(self):
        """
        Limit is the highest possible position value.
        """
        relations = {
            'work_id': self.obj.work_id,
            'original_id': self.obj.original_id,
        }
        segment_2 = factories.TranslatedSegmentFactory(position=9, **relations)
        factories.TranslatedSegmentFactory(position=10, **relations)
        factories.TranslatedSegmentFactory(position=11, **relations)
        res = self.client.get('{}?position=2&limit=9'.format(self.url_list))
        results = res.json()['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], segment_2.pk)

    # Query parameters

    def test_get_segments_since_date_content(self):
        # TODO Test different time zones
        timestamp = timezone.now()
        self.obj.content += ' update'
        self.obj.save()

        # Current time zone, i.e. UTC
        res = self.client.get(
            '{}?last_modified__gt={}'.format(
                self.url_list, self.date(timestamp)
            )
        )
        results = res.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.obj.pk)

        # Time zone + 3 h
        tz = datetime.timezone(datetime.timedelta(hours=3))
        res = self.client.get(
            '{}?last_modified__gt={}'.format(
                self.url_list,
                parse.quote(timezone.localtime(timestamp, tz).isoformat()),
            )
        )
        results = res.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.obj.pk)

    def test_get_segments_since_date_locked_by(self):
        # TODO Test different time zones
        timestamp = timezone.now()
        self.obj.locked_by_id = self.user.pk
        self.obj.save_without_historical_record()
        res = self.client.get(
            '{}?last_modified__gt={}'.format(
                self.url_list, self.date(timestamp)
            )
        )
        results = res.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.obj.pk)

    # Restore

    def test_restore_old_version(self):
        self.set_reputation('add_translation')
        self.obj.content = 'first change'
        self.obj.history.update(
            history_date=timezone.now() - datetime.timedelta(days=10)
        )
        self.obj._history_user = self.user
        self.obj._history_date = timezone.now() - datetime.timedelta(days=2)
        self.obj.changeReason = 'first change'
        self.obj.save()  # 2
        restore_record = self.obj.history.get(relative_id=2)
        vote = factories.VoteFactory(role='translator')
        restore_record.votes.add(vote)

        self.obj.content = 'second change'
        self.obj._history_date = timezone.now() - datetime.timedelta(days=1)
        self.obj._history_user = self.user
        self.obj.changeReason = 'second change'
        self.obj.save()  # 3
        vote_user = UserFactory()
        segment_vote = factories.VoteFactory.build(
            segment=self.obj, user=vote_user
        )
        history_vote = factories.VoteFactory.build(user=vote_user)
        models.Vote.objects.bulk_create((history_vote, segment_vote))
        history_vote.historical_segments.add(restore_record)

        # No permission
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            res.json(),
            {'detail': 'You do not have permission to perform this action.'},
        )
        # Permission
        self.set_reputation('restore_translation')
        self.assertEqual(self.obj.history.count(), 3)
        self.assertEqual(self.obj.content, 'second change')
        # todo: reduce queries
        with self.assertNumQueries(25):
            res = self.client.post(self.url_restore, {'relativeId': 2})
        response_json = res.json()
        self.assertEqual(response_json['segment']['content'], 'first change')
        self.assertIn('comments', response_json['segment']['statistics'])
        self.assertEqual(response_json['segment']['statistics']['records'], 4)

        reviewer_trustee = ('reviewer', 'trustee')
        if history_vote.value >= 1 and history_vote.role in reviewer_trustee:
            if history_vote.role == 'reviewer':
                if history_vote.value == 1:
                    expected = IN_REVIEW
                else:
                    expected = REVIEW_DONE
            else:
                expected = TRUSTEE_DONE
        else:
            expected = IN_TRANSLATION
        self.assertEqual(response_json['segment']['progress'], expected)

        record = self.obj.history.latest()
        expected = {
            'changeReason': 'Restore #2',
            'content': 'first change',
            'date': self.date(record.history_date),
            'expires': None,
            'id': record.pk,
            'relativeId': 4,
            'type': 'record',
            'user': self.get_user_field(edits=3),
            'votes': [
                {
                    'action': segment_vote.action,
                    'assessment': segment_vote.assessment,
                    'date': self.date(segment_vote.date),
                    'id': segment_vote.pk,
                    'role': segment_vote.role,
                    'type': 'vote',
                    'user': self.get_user_field(segment_vote.user),
                }
            ],
        }
        self.assertEqual(response_json['record'], expected)
        self.assertIsNone(response_json['deletedRelativeId'])
        # TODO
        # self.assertEqual(len(response_json['segment']['votes']), 1)
        # self.assertEqual(
        #    response_json['segment']['votes'][0]['role'],
        #    vote.role)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'first change')
        self.assertEqual(self.obj.history.count(), 4)
        votes = self.obj.votes.values_list('pk', flat=True)
        self.assertEqual(set(votes), {vote.pk, history_vote.pk})
        most_recent_record = self.obj.history.latest()
        self.assertEqual(most_recent_record.content, 'first change')
        self.assertEqual(most_recent_record.history_change_reason, 'Restore #2')
        self.assertEqual(most_recent_record.history_user_id, self.user.pk)
        self.assertEqual(most_recent_record.votes.count(), 1)
        # Not authenticated
        self.client.logout()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 401)

        self.assertEqual(models.Vote.objects.count(), 3)

    def test_restore_set_user(self):
        self.set_reputation('restore_translation')
        self.obj.save()  # 2
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            self.obj.history.latest().history_user_id, self.user.pk
        )

    def test_restore_nothing_changed(self):
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Nothing to restore.')

    def test_restore_invalid_lookup_value(self):
        res = self.client.post(self.url_restore, {'relativeId': 'invalid'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'relativeId': ['A valid integer is required.']}
        )

    def test_restore_segment_locked(self):
        self.set_reputation('restore_translation')
        self.obj.locked_by = self.user
        self.obj.save()
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )

    def test_restore_old_historical_record_multiple_times(self):
        self.set_reputation('restore_translation')
        self.obj.save()  # 2
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['segment']['id'], self.obj.pk)
        self.assertEqual(self.obj.history.count(), 3)
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.obj.history.count(), 3)
        self.assertEqual(res.json(), 'Historical record restored already.')

    def test_restore_newest_cold_historical_record_multiple_times(self):
        self.obj._history_user = self.user
        self.obj.save()  # 2
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.obj.history.count(), 1)
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.obj.history.count(), 1)
        self.assertEqual(res.json(), 'Nothing to restore.')

    def test_restore_to_empty(self):
        # This is equal to using the delete endpoint
        self.obj._history_user = self.user
        self.obj.locked_by = self.user_2
        self.obj.save()  # 2
        vote = self.create_vote()
        vote.historical_segments.set(self.obj.history.all())

        self.set_reputation(1)
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 403)
        self.set_reputation('delete_translation')
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )

        self.obj.locked_by = None
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, '')
        self.assertEqual(self.obj.history.count(), 3)
        self.assertEqual(
            self.obj.history.latest().history_change_reason, 'Clear translation'
        )
        self.assertTrue(self.obj.votes.exists())

        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Content was removed already.')
        self.assertEqual(self.obj.history.count(), 3)

    def test_restore_to_empty_when_reviewed(self):
        self.obj.progress = REVIEW_DONE
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 400)
        msg = (
            'Sorry, you cannot delete the content because the segment was '
            'reviewed already.'
        )
        self.assertEqual(res.json(), [msg])

    def test_restore_undo_without_record(self):
        self.obj.history.all().delete()
        self.obj.content = 'recent edit'
        self.obj.locked_by = self.user_2
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )

        self.obj.locked_by = None
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Nothing to restore.')

        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['deletedRelativeId'], 1)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, '')
        self.assertFalse(self.obj.history.exists())

    def test_restore_undo_first_record(self):
        self.obj.history.update(history_user=self.user)

        self.obj.locked_by = self.user_2
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )

        self.obj.locked_by = None
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        response_json = res.json()
        self.assertEqual(response_json['deletedRelativeId'], 1)
        self.obj.refresh_from_db()
        self.assertEqual(response_json['segment'], self.get_segment(self.obj))
        self.assertEqual(self.obj.content, '')
        self.assertFalse(self.obj.history.exists())

    def test_restore_undo_first_record_not_owned_by_user(self):
        content = self.obj.content
        assert content != ''

        self.obj.locked_by = self.user_2
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )

        self.obj.locked_by = None
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Nothing to restore.')

        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        # An ID for deletion is sent even if the content is the same
        self.assertEqual(res.json()['deletedRelativeId'], 2)
        self.assertEqual(self.obj.history.count(), 1)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)

    def test_restore_undo_first_record_not_owned_by_user_with_edit(self):
        content = self.obj.content
        self.obj.content = 'abc'
        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()

        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['deletedRelativeId'], 2)
        self.assertEqual(self.obj.history.count(), 1)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)

    def test_restore_undo_first_record_with_new_edit(self):
        self.obj.content = 'recent edit'
        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        self.obj.history.update(history_user=self.user)
        res = self.client.post(self.url_restore, {'relativeId': None})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['deletedRelativeId'], 1)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, '')
        self.assertFalse(self.obj.history.exists())

    def test_restore_undo_new_edit(self):
        content = self.obj.content
        self.obj.content = 'recent edit'
        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['deletedRelativeId'], 2)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)
        self.assertEqual(self.obj.history.count(), 1)

    def test_restore_undo_restored_historical_record(self):
        self.set_reputation('restore_translation')
        self.obj.save()  # 2
        record_2 = self.obj.history.latest()
        # Restore version 1
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        record_3 = self.obj.history.select_related('history_user').latest()
        self.obj.refresh_from_db()
        self.assertEqual(
            res.json()['segment'],
            self.get_segment(self.obj, record_3, records=3),
        )
        # Undo version 3
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        response_json = res.json()
        self.assertEqual(response_json['deletedRelativeId'], 3)
        self.obj.refresh_from_db()
        self.assertEqual(
            response_json['segment'],
            self.get_segment(self.obj, record_2, records=2),
        )
        # Try again
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Nothing to restore.')

    def test_restore_undo_delete_historical_record(self):
        self.set_reputation('delete_translation')
        self.obj.save()  # 2
        record = self.obj.history.latest()
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self.obj.history.count(), 3)
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.obj.history.count(), 2)
        response_json = res.json()
        self.assertIsNone(response_json['record'])
        self.assertEqual(response_json['deletedRelativeId'], 3)
        self.obj.refresh_from_db()
        self.assertEqual(
            response_json['segment'],
            self.get_segment(self.obj, record, records=2),
        )

    def test_restore_most_recent_while_hot_for_user_not_locked_changed(self):
        # This case actually can't happen
        self.obj.history.update(
            history_date=timezone.now() - datetime.timedelta(hours=1)
        )
        self.obj._history_user = self.user
        minutes_10 = datetime.timedelta(minutes=10)
        self.obj._history_date = timezone.now() - minutes_10
        self.obj.save()
        self.obj.content = 'some edit'
        self.obj._history_date = timezone.now() - datetime.timedelta(minutes=5)
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Nothing to restore.')

    def test_restore_newest_cold_record_not_locked_no_current_changes(self):
        self.set_reputation('add_translation')
        self.obj.history.update(
            history_date=timezone.now() - datetime.timedelta(hours=1)
        )
        content = self.obj.content
        self.obj._history_user = self.user
        minutes_10 = datetime.timedelta(minutes=10)
        self.obj._history_date = timezone.now() - minutes_10
        self.obj.content = 'some edit'
        self.obj.save()  # 2
        self.obj.content = 'another edit'
        self.obj._history_date = timezone.now() - datetime.timedelta(minutes=5)
        self.obj.save()  # 3
        res = self.client.post(self.url_restore, {'relativeId': 1})
        # Only the latest historical record is hot. (You need more pivileges
        # to perfrom a restore.)
        self.assertEqual(res.status_code, 403)
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['segment']['content'], 'some edit')
        res = self.client.post(self.url_restore, {'relativeId': 1})
        # Note: It actually isn't possible that there are several historical
        # records in the hot period (except in the time we increase the period).
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['segment']['content'], content)
        # Last historical record is deleted both times
        self.assertEqual(self.obj.history.count(), 1)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)

    def test_restore_newest_cold_record_not_locked_with_current_changes(self):
        # Delete last historical record and segment edits
        self.obj.history.update(
            history_date=timezone.now() - datetime.timedelta(hours=1)
        )
        content = self.obj.content
        self.obj._history_user = self.user
        minutes_10 = datetime.timedelta(minutes=10)
        self.obj._history_date = timezone.now() - minutes_10
        self.obj.content = 'some edit'
        self.obj._history_date = timezone.now() - datetime.timedelta(minutes=5)
        self.obj.save()  # 2
        self.obj.content = 'another edit'
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['segment']['content'], content)
        # Last historical record is deleted
        self.assertEqual(self.obj.history.count(), 1)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)

    def test_restore_most_recent_while_hot_for_user_locked_by_user(self):
        content = self.obj.content
        self.obj._history_user = self.user
        self.obj.save()
        self.obj.content = 'some edit'
        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        response_json = res.json()
        self.assertEqual(response_json['segment']['content'], content)
        self.assertIsNone(response_json['deletedRelativeId'])
        self.assertEqual(self.obj.history.count(), 2)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)
        self.assertIsNone(self.obj.locked_by_id)

    def test_restore_most_recent_while_hot_for_user_locked_by_another(self):
        self.obj._history_user = self.user
        self.obj.save()  # 2
        self.obj.content = 'some edit'
        self.obj.locked_by = self.user_2
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )
        self.assertEqual(self.obj.history.count(), 2)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'some edit')
        self.assertIsNotNone(self.obj.locked_by_id)

    def test_restore_most_recent_while_hot_for_another_user_not_locked(self):
        # This case actually can't happen
        self.set_reputation('restore_translation')
        self.obj._history_user = self.user_2
        self.obj.save()
        self.obj.content = 'some edit'
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 'Nothing to restore.')
        self.assertEqual(self.obj.history.count(), 2)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'some edit')

    def test_restore_newest_cold_r_while_hot_for_another_user_not_locked(self):
        self.set_reputation('restore_translation')
        self.obj.content = 'some edit'
        self.obj._history_user = self.user
        self.obj.save()  # 2
        self.obj.content = 'another edit'
        self.obj._history_user = self.user_2
        self.obj.save()  # 3
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['segment']['id'], self.obj.pk)
        self.assertEqual(self.obj.history.count(), 4)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'some edit')

    def test_restore_most_recent_while_hot_for_another_locked_by_user(self):
        self.set_reputation('restore_translation')
        content = self.obj.content
        self.obj._history_user = self.user_2
        self.obj.save()
        self.obj.content = 'some edit'
        self.obj.locked_by = self.user
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['segment']['content'], content)
        self.assertEqual(self.obj.history.count(), 2)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, content)
        self.assertIsNone(self.obj.locked_by_id)

    def test_restore_most_recent_while_hot_for_another_locked_by_another(self):
        self.obj._history_user = self.user_2
        self.obj.save()
        self.obj.content = 'some edit'
        self.obj.locked_by = self.user_2
        self.obj.save_without_historical_record()
        res = self.client.post(self.url_restore, {'relativeId': 2})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), 'Operation failed. The segment is currently locked.'
        )
        self.assertEqual(self.obj.history.count(), 2)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.content, 'some edit')
        self.assertEqual(self.obj.locked_by_id, self.user_2.pk)


class SegmentsTests(APITests):
    @classmethod
    def setUpTestData(cls):
        original_segment = factories.OriginalSegmentFactory(reference='p :3')
        factories.TranslatedWorkFactory(
            original=original_segment.work, language='de'
        )
        cls.user = UserFactory()
        obj = (
            models.TranslatedSegment.objects.select_related(
                'chapter', 'original', 'work'
            )
            .add_stats(cls.user)
            .get()
        )
        cls.data = [cls.get_segment(obj, reviewer_can_vote=False)]
        cls.url = reverse(
            'segment_by_reference',
            kwargs={
                'language': obj.work.language,
                'reference': obj.original.reference,
            },
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_segment_by_reference(self):
        with self.assertNumQueries(7):
            res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['results'], self.data)


class VoteTests(APITests):
    basename = 'translatedsegment'

    @classmethod
    def setUpTestData(cls):
        works = factories.create_work(2, 1, languages=['de'])
        cls.work = works['translations'][0]
        segment = cls.work.segments.select_related('chapter').first()
        segment.content = 't'
        segment.progress = IN_TRANSLATION
        segment.save_without_historical_record()
        cls._segment = segment
        cls.user, cls.user_2, cls.user_3 = UserFactory.create_batch(3)
        cls.set_reputation('approve_translation')
        cls.translator_vote = {
            'role': 'translator',
            'setTo': 1,
            'segment': cls._segment.pk,
            'timestamp': cls.date(cls._segment.last_modified),
        }
        cls.reviewer_vote = cls.translator_vote.copy()
        cls.reviewer_vote['role'] = 'reviewer'
        cls.trustee_vote = cls.translator_vote.copy()
        cls.trustee_vote['role'] = 'trustee'

        cls.url = '{}vote/'.format(
            cls.get_url('detail', cls._segment.work_id, cls._segment.position)
        )

    def setUp(self):
        self.segment = deepcopy(self._segment)
        self.client.force_login(self.user)

    # VoteRequestSerializer.validate

    def test_invalid_data(self):
        data = self.translator_vote.copy()
        data['role'] = 'user'
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'role': ['"user" is not a valid choice.']}
        )

    def test_segment_locked(self):
        self.segment.locked_by = self.user
        self.segment.save_without_historical_record()
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Somebody is currently working on this paragraph. During '
                    'that time, you can\'t vote it.'
                ]
            },
        )

    def test_permission_role_translator_set_to_plus_1(self):
        self.set_reputation('approve_translation', -1)
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 403)

        self.set_reputation('approve_translation')
        # todo: reduce queries
        with self.assertNumQueries(16):
            res = self.client.post(self.url, self.translator_vote)
            self.assertEqual(res.status_code, 201)
        vote = models.Vote.objects.get()
        self.segment.refresh_from_db()
        expected = {
            'comment': None,
            'vote': {
                'id': vote.pk,
                'action': 'approved',
                'assessment': 1,
                'date': self.date(vote.date),
                'role': 'translator',
                'type': 'vote',
                'user': self.get_user_field(),
            },
            'segment': self.get_segment(
                self.segment, translators_vote=1, translators_user=1
            ),
        }
        self.assertEqual(res.json(), expected)

    def test_permission_role_translator_set_to_minus_1(self):
        self.set_reputation('disapprove_translation', -1)
        vote = self.translator_vote.copy()
        vote['setTo'] = -1
        res = self.client.post(self.url, vote)
        self.assertEqual(res.status_code, 403)

        self.set_reputation('disapprove_translation')
        res = self.client.post(self.url, vote)
        self.assertEqual(res.status_code, 201)
        vote = models.Vote.objects.get()
        self.segment.refresh_from_db()
        expected = {
            'comment': None,
            'vote': {
                'id': vote.pk,
                'action': 'disapproved',
                'assessment': -1,
                'date': self.date(vote.date),
                'role': 'translator',
                'type': 'vote',
                'user': self.get_user_field(),
            },
            'segment': self.get_segment(
                self.segment,
                reviewer_can_vote=False,
                trustee_can_vote=False,
                translators_vote=-1,
                translators_user=-1,
            ),
        }
        self.assertEqual(res.json(), expected)

    def test_role_reviewer(self):
        # user = factories.UserFactory()
        # factories.VoteFactory(
        #    user=user,
        #    role='translator',
        #    value=1,
        #    segment=self.segment,
        # )
        # No permission
        self.set_reputation('review_translation', -1)
        res = self.client.post(self.url, self.reviewer_vote)
        self.assertEqual(res.status_code, 403)
        # Required votes missing
        self.set_reputation('review_translation')
        # Currently, 0 translator votes are required. Therefore, I don't test
        # this:
        # res = self.client.post(self.url, self.reviewer_vote)
        # self.assertEqual(res.status_code, 400)
        # self.assertEqual(res.json(), [
        #    'Operation failed. There are not enough votes from translators '
        #    '(currently 0 of required 1).'
        # ])
        # Success
        # factories.VoteFactory.create_batch(
        #    2,
        #    user=user,
        #    role='translator',
        #    value=1,
        #    segment=self.segment,
        # )
        res = self.client.post(self.url, self.reviewer_vote)
        self.assertEqual(res.status_code, 201)
        vote = models.Vote.objects.get(role='reviewer')
        self.segment.refresh_from_db()
        expected = {
            'comment': None,
            'vote': {
                'id': vote.pk,
                'action': 'approved',
                'assessment': 1,
                'date': self.date(vote.date),
                'role': 'reviewer',
                'type': 'vote',
                'user': self.get_user_field(),
            },
            'segment': self.get_segment(
                self.segment,
                reviewers_vote=1,
                reviewers_user=1,
                translator_can_edit=False,
            ),
        }
        self.assertEqual(res.json(), expected)

    def test_role_trustee(self):
        user = factories.UserFactory()
        factories.VoteFactory.create_batch(
            1, user=user, role='reviewer', value=1, segment=self.segment
        )
        # No permission
        self.set_reputation('trustee', -1)
        res = self.client.post(self.url, self.trustee_vote)
        self.assertEqual(res.status_code, 403)
        # Required votes missing
        self.set_reputation('trustee')
        res = self.client.post(self.url, self.trustee_vote)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Operation failed. There are not enough votes from '
                    'reviewers (currently 1 of required 2).'
                ]
            },
        )
        # Success
        self.create_vote(user=user, role='reviewer')
        res = self.client.post(self.url, self.trustee_vote)
        self.assertEqual(res.status_code, 201)
        vote = models.Vote.objects.get(role='trustee')
        self.segment.refresh_from_db()
        expected = {
            'comment': None,
            'vote': {
                'id': vote.pk,
                'action': 'approved',
                'assessment': 1,
                'date': self.date(vote.date),
                'role': 'trustee',
                'type': 'vote',
                'user': self.get_user_field(),
            },
            'segment': self.get_segment(
                self.segment,
                reviewers_vote=2,
                trustees_vote=1,
                trustees_user=1,
                translator_can_edit=False,
                reviewer_can_edit=False,
                trustee_can_vote=True,
            ),
        }
        self.assertEqual(res.json(), expected)

    def test_segment_empty(self):
        self.segment.progress = BLANK
        self.segment.save_without_historical_record()
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {'nonFieldErrors': ['Sorry, you can\'t vote empty paragraphs.']},
        )

    def test_timestamp(self):
        self.segment.save_without_historical_record()
        data = self.translator_vote.copy()
        data['date'] = self.date(self.segment.created)
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'timestamp': [
                    'Somebody worked on this text in the meantime. '
                    'Your data was just updated automatically.'
                ]
            },
        )

    # Test matrix for the second part of validate()
    # ---------------------------------
    # Tested | Last vote      | Request
    # -------|----------------|--------
    #      x | No vote        | -1
    #      x | No vote        |  0
    #      x | No vote        |  1
    #        |                |
    #        | Value | Revoke |
    #        |-------|--------|
    #      x | -2    | False  | -1
    #      x | -2    | False  |  0
    #      x | -2    | False  |  1
    #      x | -1    | True   | -1
    #      x | -1    | True   |  0
    #      x | -1    | True   |  1
    #      x | -1    | False  | -1
    #      x | -1    | False  |  0
    #      x | -1    | False  |  1
    #      x |  1    | True   | -1
    #      x |  1    | True   |  0
    #      x |  1    | True   |  1
    #      x |  1    | False  | -1
    #      x |  1    | False  |  0
    #      x |  1    | False  |  1
    #      x |  2    | False  | -1
    #      x |  2    | False  |  0
    #      x |  2    | False  |  1

    @required_approvals_patch
    def test_other_votes_are_filtered_out_correctly(self):
        # Segments
        segment = self.work.segments.last()
        votes = [self.create_vote(save=False, segment=segment, role='trustee')]
        # Roles
        votes.append(self.create_vote(save=False, role='reviewer'))
        # Users
        user = User.objects.exclude(pk=self.user.pk).last()
        votes.append(self.create_vote(save=False, user=user, role='trustee'))

        models.Vote.objects.bulk_create(votes)
        self.set_reputation('trustee')
        res = self.client.post(self.url, self.trustee_vote)
        self.assertEqual(res.status_code, 201)
        vote = res.json()['vote']
        self.assertEqual(vote['role'], 'trustee')
        self.assertEqual(vote['action'], 'approved')

    def test_latest_vote_is_used(self):
        """
        Tests that the last vote is used to calculate the value of the new vote.
        """
        self.set_reputation('disapprove_translation')
        votes = [
            self.create_vote(save=False, value=-1),
            self.create_vote(save=False, revoke=True),
        ]
        models.Vote.objects.bulk_create(votes)
        assert votes[0].date < votes[1].date
        data = self.translator_vote.copy()
        data['setTo'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        vote = res.json()['vote']
        self.assertEqual(vote['role'], 'translator')
        self.assertEqual(vote['action'], 'disapproved')

    def test_first_vote_is_a_revoke(self):
        self.set_reputation('review_translation')
        # --, 0
        data = self.reviewer_vote.copy()
        data['setTo'] = 0
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'nonFieldErrors': ['There is no vote to revoke.']}
        )

    def test_approve_twice(self):
        self.set_reputation('review_translation')
        error_messages = {
            'nonFieldErrors': [
                'Sorry, you voted already and have one vote only.'
            ]
        }
        # 1, False, 1
        self.create_vote(role='reviewer')
        res = self.client.post(self.url, self.reviewer_vote)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), error_messages)
        # 2, False, 1
        self.create_vote(role='reviewer', value=2)
        res = self.client.post(self.url, self.reviewer_vote)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), error_messages)

    def test_disapprove_twice(self):
        self.set_reputation('disapprove_translation')
        error_messages = {
            'nonFieldErrors': [
                'Sorry, you voted already and have one vote only.'
            ]
        }
        # -1, False, -1
        self.create_vote(value=-1)
        data = self.translator_vote.copy()
        data['setTo'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), error_messages)
        # -2, False, -1
        self.create_vote(value=-2)
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), error_messages)

    def test_revoke_twice(self):
        self.set_reputation('review_translation')
        error_messages = {'nonFieldErrors': ['There is no vote to revoke.']}
        # 1, True, 0
        # 1. -1 -> -1
        # 2.  0 ->  1
        self.create_vote(revoke=True)
        # 3.  0 -> error
        data = self.reviewer_vote.copy()
        data['setTo'] = 0
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), error_messages)
        # -1, True, 0
        self.create_vote(value=-1, revoke=True)
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), error_messages)

    def test_approve_after_revoke(self):
        self.set_reputation('review_translation')
        # 1, True, 1
        models.Vote.objects.bulk_create(
            (
                self.create_vote(role='reviewer', value=-1, save=False),
                self.create_vote(role='reviewer', revoke=True, save=False),
            )
        )
        res = self.client.post(self.url, self.reviewer_vote)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        # 2, True, 1 is not possible (assertion in Vote.action)
        # (Testing it here just for completeness)
        self.create_vote(role='reviewer', value=2, revoke=True)
        data = self.reviewer_vote.copy()
        data['timestamp'] = self.date(timezone.now())
        with self.assertRaises(AssertionError):
            self.client.post(self.url, data)

    def test_disapprove_after_revoke(self):
        self.set_reputation('disapprove_translation')
        # -1, True, -1
        models.Vote.objects.bulk_create(
            (
                self.create_vote(save=False),
                self.create_vote(value=-1, revoke=True, save=False),
            )
        )
        data = self.translator_vote.copy()
        data['setTo'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        # -2, True, -1 is not possible (assertion in Vote.action)
        # (Testing it here just for completeness)
        self.create_vote(value=-2, revoke=True)
        data['timestamp'] = self.date(timezone.now())
        with self.assertRaises(AssertionError):
            self.client.post(self.url, data)

    @required_approvals_patch
    def test_revoke_approval(self):
        self.set_reputation('trustee')
        # 1, False, 0
        self.create_vote(role='trustee')
        data = self.trustee_vote.copy()
        data['setTo'] = 0
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        vote = res.json()['vote']
        self.assertEqual(vote['role'], 'trustee')
        self.assertEqual(vote['action'], 'revoked approval')
        self.assertEqual(vote['assessment'], 0)
        self.assertEqual(models.Vote.objects.count(), 2)
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, -1)
        self.assertEqual(vote.revoke, True)
        # 2, False, 0
        self.create_vote(role='trustee', value=2)
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        vote = res.json()['vote']
        self.assertEqual(vote['role'], 'trustee')
        self.assertEqual(vote['action'], 'revoked approval')
        self.assertEqual(vote['assessment'], 0)
        self.assertEqual(models.Vote.objects.count(), 4)
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, -1)
        self.assertEqual(vote.revoke, True)

    def test_revoke_disapproval(self):
        # -2, False, 0
        self.create_vote(value=-2)
        data = self.translator_vote.copy()
        data['setTo'] = 0
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        vote = res.json()['vote']
        self.assertEqual(vote['role'], 'translator')
        self.assertEqual(vote['action'], 'revoked disapproval')
        self.assertEqual(vote['assessment'], 0)
        self.assertEqual(models.Vote.objects.count(), 2)
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, 1)
        self.assertEqual(vote.revoke, True)
        # -1, False, 0
        self.create_vote(value=-1)
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        vote = res.json()['vote']
        self.assertEqual(vote['role'], 'translator')
        self.assertEqual(vote['action'], 'revoked disapproval')
        self.assertEqual(vote['assessment'], 0)
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, 1)
        self.assertEqual(vote.revoke, True)

    def test_no_revoke(self):
        # Indicates that there is no vote existing
        self.set_reputation('disapprove_translation')
        # --, -1
        data = self.translator_vote.copy()
        data['setTo'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        vote = models.Vote.objects.get()
        self.assertEqual(vote.segment_id, self.segment.pk)
        self.assertEqual(vote.user_id, self.user.pk)
        self.assertEqual(vote.value, -1)
        self.assertEqual(vote.revoke, False)
        # --, 1
        models.Vote.objects.all().delete()
        data = self.translator_vote.copy()
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        vote = models.Vote.objects.get()
        self.assertEqual(vote.segment_id, self.segment.pk)
        self.assertEqual(vote.user_id, self.user.pk)
        self.assertEqual(vote.value, 1)
        self.assertEqual(vote.revoke, False)

    def test_opposite_vote(self):
        # -2, False, 1
        self.create_vote(value=-2)
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        self.assertEqual(models.Vote.objects.count(), 2)
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.segment_id, self.segment.pk)
        self.assertEqual(vote.user_id, self.user.pk)
        self.assertEqual(vote.value, 2)
        self.assertEqual(vote.revoke, False)
        # -1, False, 1
        self.create_vote(value=-1)
        data = self.translator_vote.copy()
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, 2)
        self.assertEqual(vote.revoke, False)
        # 1, False, -1
        self.set_reputation('disapprove_translation')
        self.create_vote()
        data = self.translator_vote.copy()
        data['setTo'] = -1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.segment_id, self.segment.pk)
        self.assertEqual(vote.user_id, self.user.pk)
        self.assertEqual(vote.value, -2)
        self.assertEqual(vote.revoke, False)
        # 2, False, -1
        self.create_vote(value=2)
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, -2)
        self.assertEqual(vote.revoke, False)

    def test_opposite_vote_after_revoke(self):
        # -1, True, 1
        self.create_vote(value=-1, revoke=True)
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.value, 1)
        self.assertEqual(vote.revoke, False)
        # 1, True, -1
        self.set_reputation('disapprove_translation')
        self.create_vote(revoke=True)
        data = self.translator_vote.copy()
        data['setTo'] = -1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        vote = models.Vote.objects.latest()
        self.assertEqual(vote.segment_id, self.segment.pk)
        self.assertEqual(vote.user_id, self.user.pk)
        self.assertEqual(vote.value, -1)
        self.assertEqual(vote.revoke, False)

    def test_multiple_votes_in_succession(self):
        def get_vote():
            result = models.Vote.objects.filter(
                user=self.user, segment=self.segment, role='translator'
            ).aggregate(vote=Sum('value'))
            return result['vote']

        data = self.translator_vote.copy()

        # Approval
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        self.assertEqual(get_vote(), 1)

        # Revoke approval
        data['setTo'] = 0
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'revoked approval')
        self.assertEqual(get_vote(), 0)

        # Approval
        data['setTo'] = 1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        self.assertEqual(get_vote(), 1)

        # Disapproval
        self.set_reputation('disapprove_translation')
        data['setTo'] = -1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        self.assertEqual(get_vote(), -1)

        # Revoke disapproval
        data['setTo'] = 0
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'revoked disapproval')
        self.assertEqual(get_vote(), 0)

        # Disapproval
        data['setTo'] = -1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        self.assertEqual(get_vote(), -1)

        # Approval
        data['setTo'] = 1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'approved')
        self.assertEqual(get_vote(), 1)

        # Disapproval
        data['setTo'] = -1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['vote']['action'], 'disapproved')
        self.assertEqual(get_vote(), -1)

    def test_voting_updates_segment_progress(self):
        # "progress" shouldn't be changed if the vote doesn't have an effect
        self.set_reputation('trustee')
        data = self.reviewer_vote.copy()
        data['setTo'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.progress, IN_TRANSLATION)
        # In review
        data['setTo'] = 1
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.progress, IN_REVIEW)
        # Trustee done
        votes = models.Vote.objects.bulk_create(
            (
                self.create_vote(role='reviewer', user=self.user_2, save=False),
                self.create_vote(role='reviewer', user=self.user_3, save=False),
            )
        )
        data['role'] = 'trustee'
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.progress, TRUSTEE_DONE)
        # Review done after revoke
        data['setTo'] = 0
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.progress, REVIEW_DONE)
        # In translation after revoke
        self.segment.progress = IN_REVIEW
        self.segment.save_without_historical_record()
        models.Vote.objects.filter(pk__in=[v.pk for v in votes]).delete()
        data['role'] = 'reviewer'
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.progress, IN_TRANSLATION)

    def test_voting_updates_segment_last_modified(self):
        last_modified = self.segment.last_modified
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        self.assertGreater(self.segment.last_modified, last_modified)

    # Comment

    def test_save_vote(self):
        res = self.client.post(self.url, self.translator_vote)
        self.assertEqual(res.status_code, 201)
        vote = models.Vote.objects.get()
        self.assertEqual(vote.segment_id, self.segment.pk)
        self.assertEqual(vote.user_id, self.user.pk)
        self.assertEqual(vote.role, 'translator')
        self.assertEqual(vote.value, 1)
        self.assertFalse(models.SegmentComment.objects.exists())
        # You can't vote twice
        data = self.translator_vote.copy()
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Sorry, you voted already and have one vote only.'
                ]
            },
        )

    def test_create_comment(self):
        def get_expected_objects(action, **kwargs):
            vote = models.Vote.objects.latest()
            comment = models.SegmentComment.objects.latest()
            if 'revoke' in action:
                assessment = 0
            elif 'dis' in action:
                assessment = -1
            else:
                assessment = 1
            expected = {
                'vote': {
                    'id': vote.pk,
                    'action': action,
                    'assessment': assessment,
                    'date': self.date(vote.date),
                    'role': 'translator',
                    'type': 'vote',
                    'user': self.get_user_field(),
                },
                'comment': {
                    'id': comment.pk,
                    'type': 'comment',
                    'role': 'translator',
                    'content': 'Comments should add useful information',
                    'toDelete': None,
                    'belongsTo': {'id': vote.pk, 'type': 'vote'},
                    'created': self.date(comment.created),
                    'lastModified': self.date(comment.last_modified),
                    'user': self.get_user_field(),
                },
                'segment': self.get_segment(
                    self.segment, comment=comment, **kwargs
                ),
            }
            return expected, vote, comment

        # todo: Test add_comment permission
        data = self.translator_vote.copy()
        data['comment'] = 'Comments should add useful information'
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        expected, vote, comment = get_expected_objects(
            'approved', comments=1, translators_vote=1, translators_user=1
        )
        self.assertEqual(res.json(), expected)
        self.assertEqual(models.SegmentComment.objects.count(), 1)
        self.assertEqual(comment.content, data['comment'])
        self.assertEqual(comment.role, 'translator')
        self.assertEqual(comment.work_id, self.segment.work_id)
        self.assertEqual(comment.position, 1)
        self.assertEqual(comment.user_id, self.user.pk)
        self.assertEqual(comment.vote, vote)
        # Don't create a comment in case the user voted already
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'nonFieldErrors': [
                    'Sorry, you voted already and have one vote only.'
                ]
            },
        )
        # Opposite vote and comment at the same time
        self.set_reputation('disapprove_translation')
        data['setTo'] = -1
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        expected, vote, comment = get_expected_objects(
            'disapproved',
            reviewer_can_vote=False,
            comments=2,
            translators_vote=-1,
            translators_user=-1,
        )
        self.assertEqual(res.json(), expected)
        self.assertEqual(models.SegmentComment.objects.count(), 2)
        # Undo vote and comment at the same time
        data['setTo'] = 0
        data['timestamp'] = self.date(timezone.now())
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)
        self.segment.refresh_from_db()
        expected, vote, comment = get_expected_objects(
            'revoked disapproval', comments=3
        )
        self.assertEqual(res.json(), expected)

    # Misc

    def test_read_only_fields(self):
        data = self.translator_vote.copy()
        data['date'] = 'some day last year'
        data['user'] = 'Does he exist?'
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 201)


@override_settings(DEBUG=True)
class SegmentTransactionTests(test.APITransactionTestCase):
    maxDiff = None

    def test_update_segment(self):
        user = UserFactory()
        segment = factories.TranslatedSegmentFactory(work__language='sw')
        self.client.force_login(user)
        res = self.client.patch(
            reverse(
                'translatedsegment-detail',
                args=(segment.work_id, segment.position),
            ),
            {'content': 'different', 'lastModified': segment.last_modified},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('FOR UPDATE', connection.queries[3]['sql'])

    def test_restore_database_object_blocked(self):
        user = UserFactory()
        segment = factories.TranslatedSegmentFactory(work__language='sw')
        reputation = Reputation.objects.get(
            user=user, language=segment.work.language
        )
        reputation.score = PERMISSIONS['restore_translation']
        reputation.save()
        self.client.force_login(user)
        segment.save()
        reset_queries()
        res = self.client.post(
            reverse(
                'translatedsegment-restore',
                args=(segment.work_id, segment.position),
            ),
            {'relativeId': 1},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('FOR UPDATE', connection.queries[3]['sql'])
        # When you override a class attribute in an instance you don't
        # alter the class attribute (tested with Python 3.6).
        # Therefore there is no need to restore the `queryset` attribute
        # in TranslatedSegmentViewSet.restore.
        # TODO However, this might get an issue using django-realtime-api.


class SegmentDraftTests(APITests):
    basename = 'historicalsegmentdraft'

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.reader = UserFactory()
        cls.works = factories.create_work(segments=2, translations=1)
        cls.segment = cls.works['translations'][0].segments.first()
        cls.url = cls.get_url('list', cls.segment.work_id, cls.segment.position)
        for segment in cls.works['original'].segments.all():
            try:
                tag = Tag.objects.create(name=segment.tag)
            except IntegrityError:
                # Duplicate key value violates unique constraint
                continue
            for cls in segment.classes:
                Class.objects.create(name=cls, tag=tag)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.post(self.url, {})
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['results'], [])
        contents = ['Initial version', 'First edit', 'Most recent edit']
        for c in contents:
            models.SegmentDraft.objects.create(
                owner_id=self.user.pk,
                work_id=self.segment.work_id,
                segment_id=self.segment.pk,
                position=self.segment.position,
                content=c,
            )
        res = self.client.get(self.url)
        results = res.json()['results']
        self.assertEqual(len(results), len(contents))
        contents.reverse()
        for obj, c in zip(results, contents):
            self.assertEqual(obj['content'], c)

        # Show drafts of the segment only
        another_segment = self.works['translations'][0].segments.last()
        models.SegmentDraft.objects.create(
            owner_id=self.user.pk,
            work_id=self.segment.work_id,
            segment_id=another_segment.pk,
            position=another_segment.position,
            content='Draft of another segment',
        )
        res = self.client.get(self.url)
        results = res.json()['results']
        self.assertEqual(len(results), len(contents))

        url = self.get_url(
            'list', self.segment.work_id, another_segment.position
        )
        res = self.client.get(url)
        results = res.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'Draft of another segment')

        # Another user should not see the draft
        self.client.force_login(self.reader)
        res = self.client.get(self.url)
        self.assertEqual(res.json()['results'], [])

    def test_methods_not_allowed(self):
        # Post
        res = self.client.post(self.url, {})
        self.assertEqual(res.status_code, 405)
        # Put, patch, delete
        with self.assertRaises(NoReverseMatch):
            self.get_url(
                'detail', self.segment.work_id, self.segment.position, 1
            )


class TimelineTests(APITests):
    basename = 'timeline'

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        segment = factories.TranslatedSegmentFactory()
        cls.comment = factories.SegmentCommentFactory(
            work_id=segment.work_id, position=segment.position
        )
        factories.VoteFactory(user=cls.user)
        segment.content = 'Dear <em>reader</em>,'
        segment._history_user = cls.user
        segment.save()
        vote = factories.VoteFactory(user=cls.user, segment=segment)
        first_record = segment.history.earliest()
        second_record = segment.history.latest()
        second_record.votes.add(vote)
        vote_json = {
            'id': vote.pk,
            'type': 'vote',
            'role': vote.role,
            'action': vote.action,
            'assessment': vote.assessment,
            'date': cls.date(vote.date),
            'user': cls.get_user_field(edits=1),
        }
        cls.data = [
            vote_json,
            {
                'id': second_record.pk,
                'relativeId': 2,
                'date': cls.date(second_record.history_date),
                'expires': None,
                'type': 'record',
                'changeReason': None,
                'user': cls.get_user_field(edits=1),
                'content': 'Dear <em>reader</em>,',
                'votes': [vote_json],
            },
            {
                'id': cls.comment.pk,
                'type': 'comment',
                'role': cls.comment.role,
                'user': cls.get_user_field(cls.comment.user),
                'content': cls.comment.content,
                'belongsTo': {'type': 'vote', 'id': None},
                'toDelete': None,
                'created': cls.date(cls.comment.created),
                'lastModified': cls.date(cls.comment.last_modified),
            },
            {
                'id': first_record.pk,
                'relativeId': 1,
                'date': cls.date(first_record.history_date),
                'expires': None,
                'type': 'record',
                'changeReason': None,
                'user': None,
                'content': first_record.content,
                'votes': [],
            },
        ]
        cls.record_expires = cls.date(
            second_record.history_date + HISTORICAL_UNIT_PERIOD
        )
        cls.url = cls.get_url('list', segment.work_id, segment.position)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_retrieve(self):
        # Make sure other comments and historical records are excluded
        factories.SegmentCommentFactory()
        with self.assertNumQueries(8):
            res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        response_json = res.json()
        self.assertEqual(len(response_json), 4)
        self.assertEqual(response_json, self.data)

    def test_historical_votes_are_included(self):
        models.Vote.objects.update(segment=None)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 4)

    def test_retrieve_without_votes(self):
        """
        Tests that 'expires' is set.
        """
        models.Vote.objects.all().delete()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        data = self.data[1:]
        data[0]['expires'] = self.record_expires
        data[0]['votes'] = []
        self.assertEqual(res.json(), data)

    def test_retrieve_no_objects(self):
        models.SegmentComment.objects.all().delete()
        models.TranslatedSegment.history.all().delete()
        models.Vote.objects.all().delete()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_deleted_comments_are_excluded(self):
        factories.SegmentCommentFactory(
            work_id=self.comment.work_id,
            position=self.comment.position,
            to_delete=timezone.now(),
        )
        res = self.client.get(self.url)
        self.assertEqual(res.json(), self.data)

    def test_deleted_comments_are_visible_for_owner(self):
        now = timezone.now()
        comment = factories.SegmentCommentFactory(
            work_id=self.comment.work_id,
            position=self.comment.position,
            user=self.user,
            to_delete=now,
        )
        res = self.client.get(self.url)
        response_json = res.json()
        self.assertEqual(len(response_json), 5)
        data = self.data.copy()
        data.insert(
            0,
            {
                'id': comment.pk,
                'type': 'comment',
                'role': comment.role,
                'user': self.get_user_field(edits=1),
                'content': comment.content,
                'belongsTo': {'type': 'vote', 'id': None},
                'toDelete': self.date(now),
                'created': self.date(comment.created),
                'lastModified': self.date(comment.last_modified),
            },
        )
        self.assertEqual(response_json, data)


class SegmentCommentTests(APITests):
    basename = 'segmentcomment'

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.work = factories.TranslatedWorkFactory(language='tr')
        cls.segment = factories.TranslatedSegmentFactory(
            work=cls.work, content='abc', progress=IN_TRANSLATION
        )
        cls.obj = factories.SegmentCommentFactory(
            work=cls.work, position=cls.segment.position, role='translator'
        )
        # todo: Delete following line as soon as reputations aren't auto
        # assigned at creation time anymore
        cls.obj.user.reputations.all().delete()
        cls.data = {
            # 'url': cls.get_url(
            #    'detail',
            #    cls.obj.work_id,
            #    cls.obj.position,
            #    cls.obj.pk,
            # ),
            'id': cls.obj.pk,
            'type': 'comment',
            'role': 'translator',
            'user': cls.get_user_field(cls.obj.user),
            'content': cls.obj.content,
            'belongsTo': {'type': 'vote', 'id': None},
            'toDelete': None,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list', cls.obj.work_id, cls.obj.position)
        cls.url_detail = cls.get_url(
            'detail', cls.obj.work_id, cls.obj.position, cls.obj.pk
        )

    def get_response_data(self, comments=1):
        comment = models.SegmentComment.objects.select_related('user').latest()
        segment = models.TranslatedSegment.objects.select_related(
            'chapter'
        ).get(pk=self.segment.pk)
        expected = {
            'comment': {
                'id': comment.pk,
                'type': 'comment',
                'role': 'translator',
                'user': self.get_user_field(comment.user),
                'content': ':)',
                'belongsTo': {'type': 'vote', 'id': None},
                'toDelete': None,
                'created': self.date(comment.created),
                'lastModified': self.date(comment.last_modified),
            },
            'segment': self.get_segment(
                segment, comments=comments, records=1, comment=comment
            ),
        }
        return expected

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 401)

    def test_not_found_post(self):
        self.set_reputation('add_comment')
        res = self.client.post(
            self.get_url('list', self.obj.work_id, 1_000_000), {'content': ':)'}
        )
        self.assertEqual(res.status_code, 404)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['count'], 1)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        # Permission
        self.set_reputation('add_comment')
        res = self.client.post(self.url_list, {'content': ':)'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json(), self.get_response_data(comments=2))
        # No permission
        self.user.reputations.update(score=1)
        res = self.client.post(self.url_list, {'content': ':)'})
        self.assertEqual(res.status_code, 403)

    def test_update_put(self):
        owner = self.obj.user
        # No permission
        self.set_reputation('change_comment')
        self.set_reputation(1, user=owner)
        res = self.client.put(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 403)
        # Owner
        self.client.force_login(owner)
        res = self.client.put(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 403)
        # Permission
        self.set_reputation('change_comment', user=owner)
        res = self.client.put(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.get_response_data())

    def test_update_patch(self):
        owner = self.obj.user
        self.client.force_login(owner)
        self.set_reputation('change_comment', user=owner)
        res = self.client.patch(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.get_response_data())

    def test_delete(self):
        # This endpoint was removed, therefore 405 everywhere
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 405)
        # Owner
        # Permission
        owner = self.obj.user
        self.client.force_login(owner)
        # A reputation of 1 required which is the default
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 405)

    def test_mark_to_delete(self):
        owner = self.obj.user
        self.client.force_login(owner)
        self.set_reputation('change_comment', user=owner)
        # The current date plus a delay should be saved
        before_deletion = timezone.now() + COMMENT_DELETION_DELAY
        res = self.client.patch(self.url_detail, {'delete': True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            models.SegmentComment.objects.filter(
                pk=self.obj.pk,
                to_delete__gt=before_deletion,
                to_delete__lt=timezone.now() + COMMENT_DELETION_DELAY,
            ).exists()
        )
        # Delete shouldn't be deleted when updating the content
        res = self.client.put(self.url_detail, {'content': 'like it'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            models.SegmentComment.objects.filter(
                pk=self.obj.pk,
                to_delete__gt=before_deletion,
                to_delete__lt=timezone.now() + COMMENT_DELETION_DELAY,
            ).exists()
        )
        # You should see the date when you retreive the object
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['content'], 'like it')
        self.assertEqual(
            res.json()['toDelete'][:3], before_deletion.isoformat()[:3]
        )
        # Finally remove the mark
        res = self.client.patch(self.url_detail, {'delete': 0})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            models.SegmentComment.objects.filter(
                pk=self.obj.pk, to_delete__isnull=True
            ).exists()
        )

    def test_deleted_comments_are_excluded(self):
        factories.SegmentCommentFactory(
            work_id=self.obj.work_id,
            position=self.obj.position,
            to_delete=timezone.now(),
        )
        res = self.client.get(self.url_detail)
        self.assertEqual(res.json(), self.data)
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'], [self.data])

    def test_deleted_comments_are_visible_for_owner(self):
        now = timezone.now()
        comment = factories.SegmentCommentFactory(
            work_id=self.obj.work_id,
            position=self.obj.position,
            user=self.user,
            to_delete=now,
        )
        res = self.client.get(
            self.get_url(
                'detail', comment.work_id, comment.position, comment.pk
            )
        )
        self.assertEqual(res.status_code, 200)
        expected = {
            'id': comment.pk,
            'type': 'comment',
            'role': comment.role,
            'user': self.get_user_field(),
            'content': comment.content,
            'belongsTo': {'type': 'vote', 'id': None},
            'toDelete': self.date(now),
            'created': self.date(comment.created),
            'lastModified': self.date(comment.last_modified),
        }
        self.assertEqual(res.json(), expected)

    def test_max_length(self):
        self.set_reputation('add_comment')
        res = self.client.post(self.url_list, {'content': 2001 * 'a'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()['content'],
            ['Ensure this field has no more than 2000 characters.'],
        )

    def test_role_reviewer(self):
        self.set_reputation('add_comment')
        data = self.data.copy()
        data['role'] = 'reviewer'
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 403)
        self.set_reputation('review_translation')
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['comment']['role'], 'reviewer')

    def test_role_trustee(self):
        # self.set_reputation(10 ** 5)
        self.set_reputation('add_comment')
        data = self.data.copy()
        data['role'] = 'trustee'
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 403)
        self.set_reputation('trustee')
        # self.user.user_permissions.add(
        #    Permission.objects.get(codename='vote_as_trustee'))
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['comment']['role'], 'trustee')

    def test_commenting_touches_segment(self):
        last_modified = self.segment.last_modified
        self.set_reputation('add_comment')
        res = self.client.post(self.url_list, {'content': ':)'})
        self.assertEqual(res.status_code, 201)
        segment = models.TranslatedSegment.objects.get(pk=self.segment.pk)
        self.assertGreater(segment.last_modified, last_modified)

    def test_read_only_fields(self):
        owner = self.obj.user
        self.client.force_login(owner)
        self.set_reputation('change_comment', user=owner)
        res = self.client.patch(
            self.url_detail,
            {'work': 100, 'position': 200, 'user': 300, 'to_delete': 400},
        )
        self.assertEqual(res.status_code, 200)


class AuthorTests(APITests):
    basename = 'author'

    @classmethod
    def setUpTestData(cls):
        cls.factory = test.APIRequestFactory()
        cls.obj = factories.AuthorFactory()
        cls.user = UserFactory()
        cls.admin = UserFactory(admin=True)
        cls.data = {
            'url': cls.get_url('detail', cls.obj.pk),
            'name': cls.obj.name,
            'prefix': cls.obj.prefix,
            'firstName': cls.obj.first_name,
            'lastName': cls.obj.last_name,
            'suffix': cls.obj.suffix,
            'born': cls.date(cls.obj.born),
            'bio': cls.obj.bio,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        request = self.factory.get(self.url_list)
        list_view = views.AuthorViewSet.as_view({'get': 'list'})
        res = list_view(request)
        res.render()
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        data = self.data.copy()
        data['lastName'] = 'Abcdef'
        # No permission
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 201)

    def test_update(self):
        # No permission
        res = self.client.patch(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.patch(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)

    def test_delete(self):
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)


class LicenceTests(APITests):
    basename = 'licence'

    @classmethod
    def setUpTestData(cls):
        cls.obj = factories.LicenceFactory()
        cls.user = UserFactory()
        cls.admin = UserFactory(admin=True)
        cls.data = {
            'url': cls.get_url('detail', cls.obj.pk),
            'title': cls.obj.title,
            'description': cls.obj.description,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        data = self.data.copy()
        data['title'] = 'CC'
        # No permission
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.post(self.url_list, data)
        self.assertEqual(res.status_code, 201)

    def test_update(self):
        # No permission
        res = self.client.patch(self.url_detail, {'destription': ':)'})
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.patch(self.url_detail, {'description': ':)'})
        self.assertEqual(res.status_code, 200)

    def test_delete(self):
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)


class ReferenceTests(APITests):
    basename = 'reference'

    @classmethod
    def setUpTestData(cls):
        cls.obj = factories.ReferenceFactory()
        cls.user = UserFactory()
        cls.admin = UserFactory(admin=True)
        cls.data = {
            'url': cls.get_url('detail', cls.obj.pk),
            'title': cls.obj.title,
            'type': cls.obj.type,
            'abbreviation': cls.obj.abbreviation,
            'author': cls.obj.author,
            'published': cls.obj.published,
            'language': cls.obj.language,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        # No permission
        res = self.client.post(self.url_list, self.data)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.post(self.url_list, self.data)
        self.assertEqual(res.status_code, 201)

    def test_update(self):
        # No permission
        res = self.client.patch(self.url_detail, {'title': 'How to ...'})
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.patch(self.url_detail, {'title': 'How to ...'})
        self.assertEqual(res.status_code, 200)

    def test_delete(self):
        # No permission
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Permission
        self.client.force_login(self.admin)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)


class ComplexTests(APITests):
    @tag('slow')
    def test_create_work(self):
        works = factories.create_work()
        self.assertEqual(len(works['translations']), 3)

    def test_create_small_work(self):
        with self.assertNumQueries(29):
            factories.create_work(2, 1)


class LastActivitiesTests(APITests):
    basename = 'lastactivities'

    @classmethod
    def setUpTestData(cls):
        cls.user_1, cls.user_2 = UserFactory.create_batch(2)
        owork = factories.OriginalWorkFactory(segments='h3 p h3 p')
        #                                                1 2  3 4
        twork = factories.TranslatedWorkFactory(original=owork)
        cls.comments = []
        cls.votes = []
        history_items = []
        history_model = models.TranslatedSegment.history.model
        cls.segments = tuple(twork.segments.all())
        for segment in cls.segments:
            if segment.position == 1:
                user = cls.user_2
            else:
                user = cls.user_1
            event_date = timezone.now() - datetime.timedelta(
                days=4 - segment.position
            )
            cls.comments.append(
                factories.SegmentCommentFactory.build(
                    work=twork, position=segment.position, user=user
                )
            )
            cls.votes.append(
                factories.VoteFactory.build(
                    user=user, segment=segment, value=1, date=event_date
                )
            )
            segment.add_to_history(
                history_date=event_date, history_user=user, add_to=history_items
            )

        models.SegmentComment.objects.bulk_create(cls.comments)
        models.Vote.objects.bulk_create(cls.votes)
        history_model.objects.bulk_create(history_items)
        cls.url = cls.get_url('list')

    def setUp(self):
        self.client.force_login(self.user_1)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_last_activities(self):
        with self.assertNumQueries(19):
            res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Test edits of segments
        self.assertEqual(len(data['segments']), 2)
        self.assertEqual(data['segments'][0]['id'], self.segments[-1].pk)
        self.assertEqual(data['segments'][1]['id'], self.segments[-3].pk)
        # Test votes
        self.assertEqual(len(data['votes']), 2)
        self.assertEqual(data['votes'][0]['vote']['id'], self.votes[-1].pk)
        self.assertEqual(data['votes'][1]['vote']['id'], self.votes[-3].pk)
        self.assertEqual(
            data['votes'][0]['segment']['id'], self.segments[-1].pk
        )
        self.assertEqual(
            data['votes'][1]['segment']['id'], self.segments[-3].pk
        )
        # Test comments
        self.assertEqual(len(data['comments']), 3)
        expected = tuple(
            (comment.pk, segment.pk)
            for comment, segment in zip(
                self.comments[:0:-1], self.segments[:0:-1]
            )
        )
        received = tuple(
            (obj['comment']['id'], obj['segment']['id'])
            for obj in data['comments']
        )
        self.assertEqual(received, expected)

    def test_segments(self):
        url = '{}?days=2'.format(self.get_url('segments'))
        with self.assertNumQueries(4):
            res = self.client.get(url)
        data = res.json()
        self.assertEqual(len(data), 2)
        expected = tuple(segment.pk for segment in self.segments[:-3:-1])
        received = tuple(segment['id'] for segment in data)
        self.assertEqual(received, expected)

    def test_votes(self):
        url = '{}?days=2'.format(self.get_url('votes'))
        with self.assertNumQueries(6):
            res = self.client.get(url)
        data = res.json()
        self.assertEqual(len(data), 2)
        expected = tuple(
            (vote.pk, segment.pk)
            for vote, segment in zip(self.votes[:-3:-1], self.segments[:-3:-1])
        )
        received = tuple(
            (obj['vote']['id'], obj['segment']['id']) for obj in data
        )
        self.assertEqual(received, expected)

    def test_comments(self):
        url = '{}?days=2'.format(self.get_url('comments'))
        with self.assertNumQueries(11):
            res = self.client.get(url)
        data = res.json()
        self.assertEqual(len(data), 3)
        expected = tuple(
            (comment.pk, segment.pk)
            for comment, segment in zip(
                self.comments[:0:-1], self.segments[:0:-1]
            )
        )
        received = tuple(
            (obj['comment']['id'], obj['segment']['id']) for obj in data
        )
        self.assertEqual(received, expected)
