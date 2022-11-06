from random import choice

from base import constants
from base.tests import APITests
from path.factories import UserFactory
from path.models import Reputation
from style_guide import factories, utils


class StyleGuideTests(APITests):
    basename = 'styleguide'

    @classmethod
    def setUpTestData(cls):
        active_language = constants.ACTIVE_LANGUAGES[0][0]
        cls.active_language2 = choice(constants.ACTIVE_LANGUAGES[1:])[0]
        cls.obj = factories.StyleGuideFactory(language=active_language)
        cls.user = UserFactory()
        cls.data = {
            'id': cls.obj.pk,
            'title': cls.obj.title,
            'content': cls.obj.content,
            'language': cls.obj.language,
        }
        cls.data2 = {
            'title': utils.get_styleguide_title(cls.active_language2),
            'content': utils.get_styleguide_content_from_template(),
            'language': cls.active_language2,
        }
        cls.url = cls.get_url('detail', active_language)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_retrieve_by_active_language(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

        url = self.get_url('detail', self.active_language2)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        received = res.json()
        received.pop('id')
        self.assertEqual(received, self.data2)

    def test_retrieve_by_inactive_language(self):
        url = self.get_url('detail', choice(constants.ADDITIONAL_LANGUAGES)[0])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)


class IssueTests(APITests):
    basename = 'issues'

    @classmethod
    def setUpTestData(cls):
        language = constants.ACTIVE_LANGUAGES[0][0]
        style_guide = factories.StyleGuideFactory(language=language)
        cls.user = UserFactory()
        cls.other_user = UserFactory()
        issue = factories.IssueFactory(style_guide=style_guide, user=cls.user)
        other_issue = factories.IssueFactory(
            style_guide=style_guide, user=cls.other_user
        )
        cls.data = {
            'id': issue.id,
            'title': issue.title,
            'content': issue.content,
            'tags': [],
            'user': cls.get_user_field(),
            'styleGuide': str(style_guide),
            'created': cls.date(issue.created),
            'lastModified': cls.date(issue.last_modified),
            'hasConflict': False,
            'styleGuideContent': None,
            'reactionsCount': [],
        }
        cls.data2 = {'title': 'New Issue', 'content': 'Content of issue'}
        cls.data_with_new_content = {
            'title': 'New Issue',
            'content': 'Content of issue',
            'styleGuideContent': 'New style guide content\n',
        }
        cls.url = cls.get_url('list', language)
        cls.url_detail = cls.get_url('detail', language, issue.id)
        cls.url_detail_2 = cls.get_url('detail', language, other_issue.id)

        cls.reviewer = UserFactory()
        cls.reviewer.reputations.all().delete()
        Reputation.objects.bulk_create(
            (Reputation(user=cls.reviewer, score=1000, language='am'),)
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        with self.assertNumQueries(8):
            res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_detail(self):
        with self.assertNumQueries(5):
            res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        res = self.client.post(self.url, self.data2)
        self.assertEqual(res.status_code, 201)
        received = res.json()
        self.assertEqual(
            {'title': received['title'], 'content': received['content']},
            self.data2,
        )

    def test_create_with_html(self):
        data = {
            'title': 'New Issue <br>',
            'content': '<span>Content of issue<span>',
        }
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_create_stye_guide_content_with_html(self):
        data = {
            'title': 'New Issue',
            'content': 'Content of issue',
            'style_guide_content': '<span> content </span>',
        }
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_create_title_with_html(self):
        data = {'title': 'New Issue <br>', 'content': 'Content of issue'}
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_create_content_with_html(self):
        data = {
            'title': 'New Issue',
            'content': '<span>Content of issue</span>',
        }
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_create_content_with_js(self):
        data = {
            'title': 'New Issue',
            'content': '<script> alert("aw") </script>',
        }
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_create_title_with_js(self):
        data = {
            'title': '<script> alert("aw") </script>',
            'content': 'Content of issue',
        }
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_create_stye_guide_content_with_js(self):
        data = {
            'title': 'New Issue',
            'content': 'Content of issue',
            'style_guide_content': '<script> alert("aw")</script>',
        }
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, 400)

    def test_update(self):
        res = self.client.put(self.url_detail, self.data2)
        self.assertEqual(res.status_code, 200)
        received = res.json()
        self.assertEqual(
            {'title': received['title'], 'content': received['content']},
            self.data2,
        )

    def test_update_with_html(self):
        data = {
            'title': 'New Issue <br>',
            'content': '<div>Content of issue</div>',
        }
        res = self.client.put(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_update_title_with_html(self):
        data = {'title': 'New Issue <br>', 'content': 'Content of issue'}
        res = self.client.put(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_update_content_with_html(self):
        data = {
            'title': 'New Issue',
            'content': '<span>Content of issue</span>',
        }
        res = self.client.put(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_update_content_with_js(self):
        data = {
            'title': 'New Issue',
            'content': '<script> alert("aw") </script>',
        }
        res = self.client.put(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_update_title_with_js(self):
        data = {
            'title': '<script> alert("aw") </script>',
            'content': 'Content of issue',
        }
        res = self.client.put(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_partial_update(self):
        res = self.client.patch(self.url_detail, {'title': 'New title'})
        self.assertEqual(res.status_code, 200)
        received = res.json()
        self.assertEqual(
            {'title': received['title'], 'content': received['content']},
            {'title': 'New title', 'content': self.data['content']},
        )

    def test_partial_update_title_with_html(self):
        data = {'title': 'New Issue <br>'}
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_partial_update_content_with_html(self):
        data = {'content': '<span>Content of issue</span>'}
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_partial_update_content_with_js(self):
        data = {'content': '<script> alert("aw") </script>'}
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_partial_update_title_with_js(self):
        data = {'title': '<script> alert("aw") </script>'}
        res = self.client.patch(self.url_detail, data)
        self.assertEqual(res.status_code, 400)

    def test_delete(self):
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 404)

    def test_update_other_user(self):
        res = self.client.put(self.url_detail_2, self.data2)
        self.assertEqual(res.status_code, 403)

    def test_partial_update_other_user(self):
        res = self.client.patch(self.url_detail_2, {'title': 'New title'})
        self.assertEqual(res.status_code, 403)

    def test_delete_other_user(self):
        res = self.client.delete(self.url_detail_2)
        self.assertEqual(res.status_code, 403)

    def test_update_reviewer(self):
        self.client.logout()
        self.client.force_login(self.reviewer)
        res = self.client.put(self.url_detail_2, self.data2)
        self.assertEqual(res.status_code, 200)

    def test_partial_update_reviewer(self):
        self.client.logout()
        self.client.force_login(self.reviewer)
        res = self.client.patch(self.url_detail_2, {'title': 'New title'})
        self.assertEqual(res.status_code, 200)

    def test_delete_reviewer(self):
        self.client.logout()
        self.client.force_login(self.reviewer)
        res = self.client.delete(self.url_detail_2)
        self.assertEqual(res.status_code, 204)

    def test_create_with_new_content(self):
        res = self.client.post(self.url, self.data_with_new_content)
        self.assertEqual(res.status_code, 201)
        received = res.json()
        self.assertEqual(
            received['styleGuideContent'],
            self.data_with_new_content['styleGuideContent'],
        )


class IssueCommentTests(APITests):
    basename = 'issuecomment'

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.obj = factories.IssueCommentFactory(user=cls.user)
        language = cls.obj.issue.style_guide.language
        cls.url_list = cls.get_url('list', language, cls.obj.issue.pk)
        cls.url_detail = cls.get_url(
            'detail', language, cls.obj.issue.pk, cls.obj.pk
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['count'], 1)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)

    def test_create(self):
        # Permission
        res = self.client.post(self.url_list, {'content': ':)'})
        self.assertEqual(res.status_code, 201)

    def test_update_put(self):
        # Owner
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.put(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)

    def test_update_patch(self):
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.patch(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)

    def test_delete(self):
        # Owner
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)

    def test_max_length(self):
        res = self.client.post(self.url_list, {'content': 2001 * 'a'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()['content'],
            ['Ensure this field has no more than 2000 characters.'],
        )

    def test_read_only_fields(self):
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.patch(self.url_detail, {'to_delete': 400})
        self.assertEqual(res.status_code, 200)


class IssueReactionTests(APITests):
    basename = 'issuereaction'

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.obj = factories.IssueReactionFactory(user=cls.user)
        language = cls.obj.issue.style_guide.language
        cls.url_list = cls.get_url('list', language, cls.obj.issue.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['count'], 1)

    def test_create(self):
        res = self.client.post(self.url_list, {'content': 'a'})
        self.assertEqual(res.status_code, 201)

        res = self.client.post(self.url_list, {'content': 'b'})
        self.assertEqual(res.status_code, 201)

    def test_create_same_emoji(self):
        res = self.client.post(self.url_list, {'content': 'a'})
        self.assertEqual(res.status_code, 201)

        res = self.client.post(self.url_list, {'content': 'a'})
        self.assertEqual(res.status_code, 400)
