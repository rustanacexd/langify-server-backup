import datetime
import time
from random import randint
from unittest import skip

from base.tests import SeleniumTests
from django.test import tag  # noqa: F401
from panta import factories
from path.factories import UserFactory

try:
    from selenium.webdriver.common.keys import Keys
except ImportError:
    pass


class JavaScriptTests(SeleniumTests):
    def setUp(self):
        self.user = UserFactory(username='ellen')
        self.works = factories.create_work(
            segments=20, translations=1, languages=['de_DE']
        )

    def go_to_editor(self):
        self.login()
        self.selenium.get(self.live_server_url + '/dashboard')
        self.selenium.find_element_by_class_name('c-btn--primary').click()

    def select_first_segment(self):
        body = self.selenium.find_element_by_tag_name('body')
        # TODO The sleep should actually be a WebDriverWait waiting that
        # the segments are loaded I think.
        time.sleep(0.2)
        segment = body.find_element_by_class_name('c-p__translation')
        segment.click()
        return segment

    def type_text(self, element, text, sleep=None):
        for c in text:
            element.send_keys(c)
            if sleep is None:
                time.sleep(randint(0, 30) / 100)
            else:
                time.sleep(sleep)

    @skip(reason='update needed because frontend changed')
    def test_typing(self):
        self.go_to_editor()
        segment = self.select_first_segment()
        locale = self.works['translations'][0].language
        text_factory = factories.Faker('paragraph', locale, nb_sentences=4)
        texts = [text_factory.generate({}) for i in range(5)]
        self.type_text(segment, texts[0])
        segment.send_keys(Keys.RETURN)
        self.type_text(segment, texts[1])
        segment.send_keys(Keys.RETURN)
        segment.send_keys(Keys.RETURN)
        self.type_text(segment, texts[2], sleep=0)
        segment.send_keys(Keys.RETURN)
        self.type_text(segment, texts[3], sleep=0)
        segment.send_keys(Keys.RETURN)
        self.type_text(segment, texts[4], sleep=0)

        # segments = models.TranslatedSegment.objects.all()[:5]
        # TODO Not working because of Firefox incompatibility
        # for s, t in zip(segments, texts):

    @skip(reason='update needed because frontend changed')
    def test_history(self):
        segment = self.works['translations'][0].segments.first()
        segment.content = 'Dear <em>reader</em>,'
        segment._history_user = self.user
        segment.save()
        segment.save()

        dates = ((10, 10, 10), (10, 10, 9), (2, 20, 12))
        for record, date in zip(segment.history.all(), dates):
            record.history_date = datetime.datetime(
                2010, *date, tzinfo=datetime.timezone.utc
            )
            record.save()

        self.go_to_editor()
        self.select_first_segment()
        time.sleep(0.2)
        history = self.selenium.find_element_by_class_name('c-aside__list')
        self.assertRegex(
            history.get_attribute('innerHTML'),
            # Frontend doesn't show initial record
            r'#1.+Oct 10, 10:00 AM.+#2.+Oct 10, 09:00 AM',
        )
