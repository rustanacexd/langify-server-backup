from io import StringIO
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, tag  # noqa: F401
from panta.factories import OriginalSegmentFactory, OriginalWorkFactory
from panta.models import OriginalWork, TranslatedWork

from . import models
from .constants import EMPTY_WORKS, EXISTING_WORKS, WORKS_WITH_YOUNGER_EDITION
from .utils import OpenTranslations, TextToSentences


@patch('white_estate.utils.EGWWritingsClient')
@patch('sys.stdout', new_callable=StringIO)
class OpenTranslationsTests(TestCase):
    api_data = [
        {'title': t}
        for t in ('Abc',)
        + EMPTY_WORKS
        + WORKS_WITH_YOUNGER_EDITION
        + EXISTING_WORKS['de']
    ]
    msg = (
        'Opened {} books, {} periodicals and {} manuscripts for translation.\n'
    )

    @classmethod
    def setUpTestData(cls):
        cls.owork = OriginalWorkFactory(
            title='Abc', type='book', abbreviation='abc'
        )

    def test_title_is_unique(self, stdout, client):
        msg = (
            'There is not exactly one book "Christ Our Saviour" available but '
            '0.'
        )
        with self.assertRaisesMessage(AssertionError, msg):
            OpenTranslations('de').create()
        self.assertGreater(len(OpenTranslations('de').skip_titles), 20)
        self.assertEqual(
            len(OpenTranslations('de').skip_titles), len(self.api_data) - 1
        )

    @patch.object(OpenTranslations, 'check_title_is_unique', return_value=None)
    def test_books(self, check, stdout, client):
        mock = MagicMock()
        mock.get.return_value = self.api_data
        client.return_value = mock

        OpenTranslations('de').create()
        mock.get.assert_called_once_with(
            'content/books/shortlist', lang='en', type='book'
        )
        self.assertEqual(check.call_count, 3)
        self.assertEqual(stdout.getvalue(), self.msg.format(1, 0, 0))
        self.assertEqual(TranslatedWork.objects.count(), 1)

        # In the DB existing works should be excluded
        OpenTranslations('de').create()
        self.assertIn(self.msg.format(0, 0, 0), stdout.getvalue())
        self.assertEqual(TranslatedWork.objects.count(), 1)

    @patch.object(OpenTranslations, 'check_title_is_unique', return_value=None)
    def test_periodicals(self, check, stdout, client):
        OriginalWork.objects.update(type='periodical')
        OpenTranslations('de', types=('periodical',)).create()
        self.assertEqual(stdout.getvalue(), self.msg.format(0, 1, 0))
        self.assertEqual(TranslatedWork.objects.count(), 1)

    @patch.object(OpenTranslations, 'check_title_is_unique', return_value=None)
    def test_periodicals_not_in_db(self, check, stdout, client):
        OpenTranslations('de', types=('periodical',)).create()
        self.assertEqual(stdout.getvalue(), self.msg.format(0, 0, 0))
        self.assertEqual(TranslatedWork.objects.count(), 0)

    @patch.object(OpenTranslations, 'check_title_is_unique', return_value=None)
    def test_manuscripts(self, check, stdout, client):
        OriginalWork.objects.update(type='manuscript')
        OpenTranslations('de', types=('periodical', 'manuscript')).create()
        self.assertEqual(stdout.getvalue(), self.msg.format(0, 0, 1))
        self.assertEqual(TranslatedWork.objects.count(), 1)

    def test_open_given_titles_only(self, stdout, client):
        OriginalWorkFactory(
            title='w2',
            type='book',
            author=self.owork.author,
            licence=self.owork.licence,
            trustee=self.owork.trustee,
        )
        mock = MagicMock()
        mock.get.return_value = self.api_data + [{'title': 'w2'}]
        client.return_value = mock

        # create_books
        count = OpenTranslations('de', titles=['Abc']).create_books()
        self.assertEqual(count, 1)
        self.assertEqual(TranslatedWork.objects.get().title, 'Abc')
        TranslatedWork.objects.all().delete()

        count = OpenTranslations('de', titles=[('Abc', 'abc')]).create_books()
        self.assertEqual(count, 1)
        self.assertEqual(TranslatedWork.objects.get().title, 'Abc')
        TranslatedWork.objects.all().delete()

        # create_works_of_type
        tye = 'periodical'
        OriginalWork.objects.update(type=tye)
        count = OpenTranslations('de', titles=['Abc']).create_works_of_type(tye)
        self.assertEqual(count, 1)
        self.assertEqual(TranslatedWork.objects.get().title, 'Abc')
        TranslatedWork.objects.all().delete()

        titles = [('Abc', 'abc')]
        count = OpenTranslations('de', titles=titles).create_works_of_type(tye)
        self.assertEqual(count, 1)
        self.assertEqual(TranslatedWork.objects.get().title, 'Abc')

    def test_title_not_in_db(self, stdout, client):
        mock = MagicMock()
        mock.get.return_value = ({'title': 'Does not exist'},)
        client.return_value = mock
        OpenTranslations('de', verbosity=2).create_books()
        self.assertEqual(
            stdout.getvalue(),
            'Warning: "Does not exist" not found in the database.\n',
        )

    def test_exclude_books_with_not_unique_title(self, stdout, client):
        mock = MagicMock()
        mock.get.return_value = self.api_data
        client.return_value = mock
        OriginalWork.objects.update(
            title='Messages to Young People', abbreviation='MYP'
        )
        OpenTranslations('de').create_books()
        self.assertFalse(TranslatedWork.objects.exists())

    def test_existing(self, stdout, client):
        ot = OpenTranslations('sw', existing=True)
        expected = EMPTY_WORKS + WORKS_WITH_YOUNGER_EDITION
        self.assertEqual(ot.skip_titles, expected)

        ot = OpenTranslations('sw')
        self.assertEqual(ot.skip_titles, expected + EXISTING_WORKS.get('sw'))

    def test_protect(self, stdout, client):
        ot = OpenTranslations('fr')
        self.assertEqual(ot.protect, False)

        ot = OpenTranslations('fr', protect=True)
        ot.create_translation(self.owork)
        protected = tuple(
            TranslatedWork.objects.values_list('protected', flat=True)
        )
        self.assertEqual(protected, (True,))


@patch('sys.stdout', new_callable=StringIO)
class SimpleSplitToSentencesTests(SimpleTestCase):
    maxDiff = None
    divider = TextToSentences()
    data = (
        # Foreword
        # CCH 5.1
        (
            """
            <span class="non-egw-foreword">As the Seventh-day Adventist movement
            church throughout the world. It is not possible to publish in each
            the many other spirit of prophecy books. There is presented in this
            church.</span>
            """,
            [
                'As the Seventh-day Adventist movement church throughout the '
                'world.',
                #
                'It is not possible to publish in each the many other spirit '
                'of prophecy books.',
                #
                'There is presented in this church.',
            ],
        ),
        # Extract little headings
        # -----------------------
        # m-dash
        # PAM 51.2
        (
            """
            <strong>Ellen White's writings were filed and indexed during her
            Australian years</strong>—For some months Sister Peck has devoted a
            typewriter.
            """,
            [
                '<strong>Ellen White\'s writings were filed and indexed during '
                'her Australian years</strong>',
                #
                'For some months Sister Peck has devoted a typewriter.',
            ],
        ),
        # PAM 59.1
        (
            """
            <strong>Acquire moral stamina by saying, “I will not dishonor my
            Redeemer</strong>”—You ask me if you shall make a public confession.
            """,
            [
                '<strong>Acquire moral stamina by saying, “I will not dishonor '
                'my Redeemer</strong>”',
                #
                'You ask me if you shall make a public confession.',
            ],
        ),
        # colon, MM p1509
        (
            """
            <span class="non-egw-comment"><strong>Ellen White's writings were
            filed and indexed during her Australian years</strong>—For some
            manuscripts that were never copied on the typewriter. In these she
            with the rest.—4BIO 451</span>.
            """,
            [
                '<strong>Ellen White\'s writings were filed and indexed during '
                'her Australian years</strong>',
                #
                'For some manuscripts that were never copied on the '
                'typewriter.',
                #
                'In these she with the rest.—4BIO 451.',
            ],
        ),
        # CHL 14.3
        (
            """
            <strong>A Fatal Deception-</strong>-There is a most fearful, fatal
            deception upon human minds.
            """,
            [
                '<strong>A Fatal Deception-</strong>',
                #
                'There is a most fearful, fatal deception upon human minds.',
            ],
        ),
        # <em>
        # CHS 270.6
        (
            """
            <em>Health</em>—Doing good is an excellent remedy for disease.
            """,
            [
                '<em>Health</em>',
                #
                'Doing good is an excellent remedy for disease.',
            ],
        ),
        # Don't split
        # CCH 31.9
        (
            """
            <span class="non-egw-intro">The counsels that follow are drawn from
            a number of the E. G. White books—but mainly from the three volumes
            of Testimony Treasures, the world edition of the <em>Testimonies for
            the Church</em>—and represent</span> <span class="non-egw-intro">the
            to publish more than a single volume of moderate size.
            """,
            [
                '<span class="non-egw-intro">The counsels that follow are '
                'drawn from a number of the E. G. White books—but mainly from '
                'the three volumes of Testimony Treasures, the world edition '
                'of the <em>Testimonies for the Church</em>—and represent the '
                'to publish more than a single volume of moderate size.'
            ],
        ),
        # Remove page breaks
        # ------------------
        # CH 1.5
        (
            """
            <span class="non-egw-preface">Lord Lister, by applying the
            principles of Pasteur to the operating room, made surgery safe for
            mankind. His</span> <span class="non-egw-preface">genius transformed
            insignificant figure.</span>
            """,
            [
                'Lord Lister, by applying the principles of Pasteur to the '
                'operating room, made surgery safe for mankind.',
                #
                'His genius transformed insignificant figure.',
            ],
        ),
        # Regular split
        # -------------
        # B.C.
        # GC 326.3
        (
            """
            In its completest form it was issued by Artaxerxes, king of Persia,
            457 B.C. But in <span class="egwlink egwlink_bible"
            data-link="1965.24757" title="ezra 6:14">Ezra 6:14</span> the house
            of the Lord at Jerusalem is said to have been built “according to
            the commandment [“decree,” margin] of Cyrus, and Darius, and
            Artaxerxes king of Persia.”
            """,
            [
                'In its completest form it was issued by Artaxerxes, king of '
                'Persia, 457 B.C.',
                #
                'But in <span class="egwlink egwlink_bible" '
                'data-link="1965.24757" title="ezra 6:14">Ezra 6:14</span> '
                'the house of the Lord at Jerusalem is '
                'said to have been built “according to the commandment '
                '[“decree,” margin] of Cyrus, and Darius, and Artaxerxes king '
                'of Persia.”',
            ],
        ),
        # R.V.
        # AA 312.2
        (
            """
            <span class="egwlink egwlink_bible" data-link="1965.50172"
            title="mark 9:43">Mark 9:43-45,</span> R.V. If to save the body from
            away sin, which brings death to the soul!
            """,
            [
                '<span class="egwlink egwlink_bible" data-link="1965.50172" '
                'title="mark 9:43">Mark 9:43-45,</span> R.V.',
                #
                'If to save the body from away sin, which brings death to the '
                'soul!',
            ],
        ),
        # A.R.V.
        # GC 269.2
        (
            """
            <span class="egwlink egwlink_bible" data-link="1965.3328"
            title="exodus 5:2">Exodus 5:2</span>, A.R.V. This is atheism, and
            unbelief and defiance.
            """,
            [
                '<span class="egwlink egwlink_bible" data-link="1965.3328" '
                'title="exodus 5:2">Exodus 5:2</span>, A.R.V.',
                #
                'This is atheism, and unbelief and defiance.',
            ],
        ),
        # R. V.
        # DA 190.5
        (
            """
            <span class="egwlink egwlink_bible" data-link="1965.53427"
            title="john 4:34">John 4:34</span>, R. V. As His words to the woman
            had aroused her conscience, Jesus rejoiced.
            """,
            [
                '<span class="egwlink egwlink_bible" data-link="1965.53427" '
                'title="john 4:34">John 4:34</span>, R. V.',
                #
                'As His words to the woman had aroused her conscience, Jesus '
                'rejoiced.',
            ],
        ),
        # DA 181.2
        (
            """
            <span class="egwlink egwlink_bible" data-link="1965.53352"
            title="john 3:33">John 3:33</span>, R. V. “He that believeth on the
            Son hath everlasting life.”
            """,
            [
                '<span class="egwlink egwlink_bible" data-link="1965.53352" '
                'title="john 3:33">John 3:33</span>, R. V.',
                #
                'He that believeth on the Son hath everlasting life.',
            ],
        ),
        # </em>
        # CCH 23.1
        (
            """
            Just after they dispersed for what they thought was their last
            meeting, the mail arrived and among the letters was the <em>Review
            and Herald.</em> In the itinerary section was a notice that James
            1867.
            """,
            [
                'Just after they dispersed for what they thought was their '
                'last meeting, the mail arrived and among the letters was the '
                '<em>Review and Herald.</em>',
                #
                'In the itinerary section was a notice that James 1867.',
            ],
        ),
        # <br/>
        # -----
        # COL 81.2
        (
            """
            Thou visitest the earth, and waterest it;<br/>Thou greatly enrichest
            it;<br/>The river of God is full of water;<br/>Thou providest them
            corn when<br/> Thou hast so prepared the earth.<br/>Thou waterest
            her furrows abundantly;<br/>Thou settlest the ridges
            thereof;<br/>Thou makest it soft with showers;<br/>Thou blessest the
            springing thereof.<br/>Thou crownest the year with Thy
            goodness;<br/>And Thy paths drop fatness.
            """,
            [
                'Thou visitest the earth, and waterest it;<br/>Thou greatly '
                'enrichest it;<br/>The river of God is full of water;<br/>Thou '
                'providest them corn when<br/> Thou hast so prepared the '
                'earth.',
                #
                'Thou waterest her furrows abundantly;<br/>Thou settlest the '
                'ridges thereof;<br/>Thou makest it soft with '
                'showers;<br/>Thou blessest the springing thereof.',
                #
                'Thou crownest the year with Thy goodness;<br/>And Thy paths '
                'drop fatness.',
            ],
        ),
        # DA 672.4 (tests also quotation marks with quotations)
        (
            """
            “O praise the Lord, all ye nations:<br/>Praise Him, all ye
            people.<br/>For His merciful kindness is great toward us:<br/>And
            the truth of the Lord endureth forever.<br/>Praise ye the Lord.”
            <span class="egwlink egwlink_bible" data-link="1965.32353"
            title="psalm 117:1">Psalm 117</span>.
            """,
            [
                'O praise the Lord, all ye nations:',
                #
                'Praise Him, all ye people.',
                #
                'For His merciful kindness is great toward us:',
                #
                'And the truth of the Lord endureth forever.',
                #
                'Praise ye the Lord.',
            ],
        ),
        # MH 456.3
        (
            """
            “Incline thine ear unto wisdom, ... <br/>Apply thy heart to
            understanding; ... <br/>Seek her as silver, ... <br/>Search for her
            as for hid treasures: <br/>Then shalt thou understand the fear of
            Jehovah, <br/>And find the knowledge of God.... <br/>Then shalt thou
            understand righteousness and justice, <br/>And equity, yea, every
            good path. <br/>For wisdom shall enter into thy heart, <br/>And
            knowledge shall be pleasant unto thy soul; <br/>Discretion shall
            watch over thee; <br/>Understanding shall keep thee.” <br/>Wisdom
            “is a tree of life to them that lay hold upon her: <br/>And happy is
            everyone that retaineth her.”
            """,
            [
                'Incline thine ear unto wisdom,',
                #
                'Apply thy heart to understanding;',
                #
                'Seek her as silver,',
                #
                'Search for her as for hid treasures:',
                #
                'Then shalt thou understand the fear of Jehovah, '
                '<br/>And find the knowledge of God.',
                #
                'Then shalt thou understand righteousness and justice, '
                '<br/>And equity, yea, every good path.',
                #
                'For wisdom shall enter into thy heart, '
                '<br/>And knowledge shall be pleasant unto thy soul; '
                '<br/>Discretion shall watch over thee; '
                '<br/>Understanding shall keep thee.',
                #
                'Wisdom “is a tree of life to them that lay hold upon her:',
                #
                'And happy is everyone that retaineth her.',
            ],
        ),
        # For more tests of this kind see below 'test_br'
        #
        # Abbreviations
        # -------------
        # art.
        # GC 679.4
        (
            """
            For discussion see, for the Roman Catholic view, <em>The Catholic
            Encyclopedia,</em> Vol. 7, art. “Infallibility,” by Patrick J.
            Toner, 790ff.; James Cardinal Gibbons, <em>The Faith of our
            Fathers</em> (Baltimore: John Murphy Company, 110th ed., 1917), chs.
            7, 11.
            """,
            [
                'For discussion see, for the Roman Catholic view, <em>The '
                'Catholic Encyclopedia,</em> Vol. 7, art. “Infallibility,” by '
                'Patrick J. Toner, 790ff.; James Cardinal Gibbons, <em>The '
                'Faith of our Fathers</em> (Baltimore:',
                #
                'John Murphy Company, 110th ed., 1917), chs. 7, 11.',
            ],
        ),
        # st.
        # GC 684.2
        (
            """
            See also H. G. Schroeder, <em>Canons and Decrees of the Council of
            Trent</em> (St. Louis, Missouri: B. Herder, 1941).</span>
            """,
            [
                'See also H. G. Schroeder, <em>Canons and Decrees of the '
                'Council of Trent</em> (St. Louis, Missouri:',
                #
                'B. Herder, 1941).</span>',
            ],
        ),
        # th.
        # GC 686.2
        (
            """
            <span class="non-egw-appendix">More recent publications on the
            council are K. Zahringer, <em>Das Kardinal Kollegium auf dem
            Konstanzer Konzil</em> (Munster, 1935); Th. F. Grogau, <em>The
            Conciliar Theory as it Manifested itself at the Council of
            Constance</em> (Washington, 1949); Fred A. Kremple, <em>Cultural
            Aspects of the Council of Constance and Basel</em> (Ann Arbor,
            1955); John Patrick McGowan, <em>D'ailly and the Council of
            Constance</em> (Washington: Catholic University, 1936).</span>
            """,
            [
                'More recent publications on the council are K. Zahringer, '
                '<em>Das Kardinal Kollegium auf dem Konstanzer Konzil</em> '
                '(Munster, 1935); Th. F. Grogau, <em>The Conciliar Theory as '
                'it Manifested itself at the Council of Constance</em> '
                '(Washington, 1949); Fred A. Kremple, <em>Cultural Aspects of '
                'the Council of Constance and Basel</em> (Ann Arbor, 1955); '
                'John Patrick McGowan, <em>D\'ailly and the Council of '
                'Constance</em> (Washington:',
                #
                'Catholic University, 1936).',
            ],
        ),
        # not tested: Rev., Vol., vols., pp
        #
        # Remove brackets and non-egw-comment
        # -----------------------------------
        # PP 664.5
        (
            """
            And now I have heard that thou hast shearers: now thy shepherds
            which were with us, we hurt them not, neither was there aught
            missing unto them, all the while they were in Carmel.
            [<span class="non-egw-comment">Not Mount Carmel, but a place in the
            territory of Judah, near the hill town of Maon.</span>] Ask thy
            young men, and they will show thee.
            """,
            [
                'And now I have heard that thou hast shearers: now thy '
                'shepherds which were with us, we hurt them not, neither was '
                'there aught missing unto them, all the while they were in '
                'Carmel.',
                #
                'Not Mount Carmel, but a place in the territory of Judah, near '
                'the hill town of Maon.',
                #
                'Ask thy young men, and they will show thee.',
            ],
        ),
        # Citations
        # ---------
        # CHL 14.5
        (
            """
            Every worker alike is to hold himself amenable to the requirements
            and instructions of God.-<span class="egwlink egwlink_book"
            data-link="115.1519" title="9t 270.1">Testimonies for the Church
            9:270</span>.
            """,
            [
                'Every worker alike is to hold himself amenable to the '
                'requirements and instructions of God.'
            ],
        ),
        # Not at the end of a paragraph
        # COL 152.2
        (
            """
            When Christ on the eve of His betrayal forewarned His disciples,
            “All ye shall be offended because of Me this night,” Peter
            confidently declared, “Although all shall be offended, yet will not
            I.” <span class="egwlink egwlink_bible" data-link="1965.50577"
            title="mark 14:27">Mark 14:27, 29</span>. Peter did not know his own
            danger.
            """,
            [
                'When Christ on the eve of His betrayal forewarned His '
                'disciples, “All ye shall be offended because of Me this '
                'night,” Peter confidently declared, “Although all shall be '
                'offended, yet will not I.”',
                #
                'Peter did not know his own danger.',
            ],
        ),
        # WM 189.1
        (
            """
            By our churches there is a work to be done of which many have little
            idea, a work as yet almost untouched. “I was an hungred,” Christ
            says, “and ye gave Me meat: I was thirsty, and ye gave Me drink: I
            was a stranger, and ye took Me in: naked, and ye clothed Me: I was
            sick, and ye visited Me: I was in prison, and ye came unto Me.”
            <span class="egwlink egwlink_bible" data-link="1965.49083"
            title="matthew 25:35">Matthew 25:35, 36</span>. Some think that if
            they give money to this work, it is all they are required to do, but
            this is an error. Donations of money cannot take the place of
            personal ministry. It is right to give our means, and many more
            should do this; but according to their strength and opportunities,
            personal service is required of all.
            """,
            [
                'By our churches there is a work to be done of which many have '
                'little idea, a work as yet almost untouched.',
                #
                '“I was an hungred,” Christ says, “and ye gave Me meat:',
                #
                'I was thirsty, and ye gave Me drink:',
                #
                'I was a stranger, and ye took Me in: naked, and ye clothed '
                'Me:',
                #
                'I was sick, and ye visited Me:',
                #
                'I was in prison, and ye came unto Me.',
                #
                'Some think that if they give money to this work, it is all '
                'they are required to do, but this is an error.',
                #
                'Donations of money cannot take the place of personal '
                'ministry.',
                #
                'It is right to give our means, and many more should do this; '
                'but according to their strength and opportunities, personal '
                'service is required of all.',
            ],
        ),
        # Don't split
        # on
        # PP p1747
        (
            """
            <span class="non-egw-comment">This chapter is based on <span
            class="egwlink egwlink_bible" data-link="1965.14004" title="judges
            13:1">Judges 13</span> to <span class="egwlink egwlink_bible"
            data-link="1965.14137" title="judges 16:1">16</span></span>.
            """,
            [
                'This chapter is based on <span class="egwlink egwlink_bible" '
                'data-link="1965.14004" title="judges 13:1">Judges 13</span> '
                'to <span class="egwlink egwlink_bible" data-link="1965.14137" '
                'title="judges 16:1">16</span>.'
            ],
        ),
        # See
        # PP 760.3
        (
            """
            The Ten Commandments in all their details are “all these words,”
            <em>concerning which</em> the covenant was made. See <span
            class="egwlink egwlink_bible" data-link="1965.4449" title="exodus
            24:8">Exodus 24:8</span></span>.
            """,
            [
                'The Ten Commandments in all their details are “all these '
                'words,” <em>concerning which</em> the covenant was made.',
                #
                'See <span class="egwlink egwlink_bible" data-link="1965.4449" '
                'title="exodus 24:8">Exodus 24:8</span></span>.',
            ],
        ),
        # See also
        # PP 761.2
        (
            """
            In a holy place shall it be eaten, in the court of the tent of
            meeting.” <span class="egwlink egwlink_bible" data-link="1965.5852"
            title="leviticus 6:26">Leviticus 6:26</span>, R.V. See also <span
            class="egwlink egwlink_bible" data-link="1965.5734" title="leviticus
            4:22">Leviticus 4:22-35</span></span>.
            """,
            [
                'In a holy place shall it be eaten, in the court of the tent '
                'of meeting.',
                #
                '<span class="egwlink egwlink_bible" data-link="1965.5852" '
                'title="leviticus 6:26">Leviticus 6:26</span>, R.V.',
                #
                'See also <span class="egwlink egwlink_bible" '
                'data-link="1965.5734" title="leviticus 4:22">Leviticus '
                '4:22-35</span></span>.',
            ],
        ),
        # Not tested: and, in, ,
        # <em>
        # CE 242.3
        (
            """
            Angels will come close to your side, and help you to lift up the
            standard against the enemy, and instead of cutting off the erring
            one, you may be enabled to gain a soul for Christ.—<em>Extract from
            an article in the Sabbath-school Worker for December, 1892.</em>
            """,
            [
                'Angels will come close to your side, and help you to lift up '
                'the standard against the enemy, and instead of cutting off '
                'the erring one, you may be enabled to gain a soul for Christ.',
                #
                '<em>Extract from an article in the Sabbath-school Worker for '
                'December, 1892.</em>',
            ],
        ),
        # GC 210.1
        (
            """
            All this matter is Thine, and it is only by Thy constraint that we
            have put our hands to it. Defend us, then, O
            Father!”—<em>Ibid.,</em> b. 14, ch. 6.
            """,
            [
                'All this matter is Thine, and it is only by Thy constraint '
                'that we have put our hands to it.',
                #
                'Defend us, then, O Father!',
                #
                '<em>Ibid.,</em> b. 14, ch. 6.',
            ],
        ),
        # Separate footnote into its own sentence
        # ---------------------------------------
        # CCH 56.5
        (
            """
            He is acquainted with all our weaknesses and infirmities, and He
            will help us.<sup class="footnote"><a class="footnote">28<span
            class="footnote"><span class="egwlink egwlink_book"
            data-link="98.2018" title="1sm 350.1">Selected Messages 1:350, 351,
            353</span></span></a></sup> Darkness and discouragement will
            sometimes come upon the soul and threaten to overwhelm us, but we
            should not cast away our confidence.
            """,
            [
                'He is acquainted with all our weaknesses and infirmities, and '
                'He will help us.',
                #
                '<sup class="footnote"><a class="footnote">28<span '
                'class="footnote"><span class="egwlink egwlink_book" '
                'data-link="98.2018" title="1sm 350.1">Selected Messages '
                '1:350, 351, 353</span></span></a></sup>',
                #
                'Darkness and discouragement will sometimes come upon the soul '
                'and threaten to overwhelm us, but we should not cast away our '
                'confidence.',
            ],
        ),
    )

    def test_basics(self, stdout):
        self.assertEqual(
            self.divider.split(
                'Yes.  What happens e.g. to B.C. “This is” me and you. '
                'Änd "this." Welcome! Mr.—D. R. Smith". '
                'What about a "question"? Seems to ... work!'
            ),
            [
                'Yes.',
                'What happens e.g. to B.C.',
                '“This is” me and you.',
                'Änd "this."',
                'Welcome!',
                'Mr.—D. R. Smith.',
                'What about a "question"?',
                'Seems to ... work!',
            ],
        )

    def test_nbsp(self, stdout):
        self.assertEqual(
            self.divider.split('Hi.\xa0This is Tom.'), ['Hi.', 'This is Tom.']
        )

    def test_strip_spaces(self, stdout):
        # WM 21.1
        text = [
            'And His disciples asked Him, saying, Master, who did sin, '
            'this man, or his parents, that he was born blind?',
            #
            'Jesus answered, Neither hath this man sinned, nor his '
            'parents: but that the works of God should be made manifest in '
            'him.',
        ]
        self.assertEqual(self.divider.split('{} {}\xa0'.format(*text)), text)

    def test_br(self, stdout):
        # MH 107.5
        text = (
            '“Break forth into joy, sing together, ye waste places:...\r\n'
            '<br/>For the Lord hath comforted His people....\r\n'
            '<br/>The Lord hath made bare His holy arm\r\n'
            '<br/>In the eyes of all the nations;\r\n'
            '<br/>And all the ends of the earth\r\n'
            '<br/>Shall see the salvation of our God.” '
            '<span class="sameasprevious"><span class="egwlink egwlink_bible" '
            'data-link="1965.38167" title="isaiah 52:9">Verses 9, '
            '10</span>.</span>'
        )
        expected = [
            'Break forth into joy, sing together, ye waste places:',
            #
            'For the Lord hath comforted His people.',
            #
            'The Lord hath made bare His holy arm\r\n'
            '<br/>In the eyes of all the nations;\r\n'
            '<br/>And all the ends of the earth\r\n'
            '<br/>Shall see the salvation of our God.',
            #
            '<span class="egwlink egwlink_bible" '
            'data-link="1965.38167" title="isaiah 52:9">Verses 9, '
            '10</span>.</span>',
        ]
        self.assertEqual(self.divider.split(text), expected)

        # MH 417.4
        text = (
            '“The way of man is not in himself:\r\n'
            '<br/>It is not in man that walketh to direct his steps.”'
        )
        expected = [
            'The way of man is not in himself:',
            #
            'It is not in man that walketh to direct his steps.',
        ]
        self.assertEqual(self.divider.split(text), expected)

        # MH 418.1
        text = (
            '“The earth, O Jehovah, is full of Thy loving-kindness.”\r\n'
            '<br/>Thou lovest “righteousness and justice.”\r\n'
            '<br/>Thou “art the confidence of all the ends of the earth,\r\n'
            '<br/>And of them that are afar off upon the sea:\r\n'
            '<br/>Who by His strength setteth fast the mountains,\r\n'
            '<br/>Being girded about with might;\r\n'
            '<br/>Who stilleth the roaring of the seas, ...\r\n'
            '<br/>And the tumult of the peoples.”'
        )
        expected = [
            'The earth, O Jehovah, is full of Thy loving-kindness.',
            #
            'Thou lovest “righteousness and justice.”',
            #
            'Thou “art the confidence of all the ends of the earth,\r\n'
            '<br/>And of them that are afar off upon the sea:',
            #
            'Who by His strength setteth fast the mountains,\r\n'
            '<br/>Being girded about with might;\r\n'
            '<br/>Who stilleth the roaring of the seas,',
            #
            'And the tumult of the peoples.',
        ]
        self.assertEqual(self.divider.split(text), expected)

    def test_examples(self, stdout):
        """
        Tests exceptions with original texts and thereby also standard cases.
        """
        expected = []
        result = []
        for t, s in self.data:
            expected.append(s)
            result.append(self.divider.split(' '.join(t.split())))
        self.assertEqual(result, expected)

    def test_handle_footnotes(self, stdout):
        text = 'We want Mr.<sup c>you</sup> m. It is!<sup c>yes</sup> "Next." '
        expected = [
            'We want Mr.<sup c>you</sup> m.',
            'It is!',
            '<sup c>yes</sup>',
            'Next.',
        ]
        self.assertEqual(self.divider.split(text), expected)
        self.assertEqual(self.divider.split(3 * text), 3 * expected)
        text = 'It is!<sup c>yes</sup>'
        self.assertEqual(self.divider.split(text), expected[1:3])
        text = '<sup c>yes</sup> "Next.'
        self.assertEqual(self.divider.split(text), expected[2:])

    def test_ends_with_abbreviation(self, stdout):
        self.assertFalse(self.divider.ends_with_abbreviation('No!'))
        self.assertTrue(self.divider.ends_with_abbreviation('Bro.'))
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(self.divider.split('A B.C. B.'), ['A B.C.', 'B.'])
        self.assertEqual(
            stdout.getvalue(),
            'Warning: A sentence is split with an abbreviation or ellipsis at '
            'the end but we are not sure if the sentence ends here:\n'
            '    A B.C.\n'
            '    B.\n'
            'Warning: "B." is a very short sentence. Please check '
            'if it is an abbreviation instead.\n',
        )


@patch('sys.stdout', new_callable=StringIO)
class DatabaseSplitToSentencesTests(TestCase):
    divider = TextToSentences()

    @classmethod
    def setUpTestData(cls):
        cls.segment = OriginalSegmentFactory(content='One. Two! Three?')

    def test_process_work(self, stdout):
        self.divider.process_works([self.segment.work], save=False)
        self.assertFalse(models.OriginalSentence.objects.exists())
        self.divider.process_works([self.segment.work])
        self.assertEqual(models.OriginalSentence.objects.count(), 3)
        self.assertEqual(
            models.OriginalSegmentSentenceRelation.objects.count(), 3
        )

    def test_find_changes(self, stdout):
        sentences = models.OriginalSentence.objects.bulk_create(
            (
                models.OriginalSentence(content='One.'),
                models.OriginalSentence(content='Two!'),
                models.OriginalSentence(content='None'),
            )
        )
        models.OriginalSegmentSentenceRelation.objects.bulk_create(
            (
                models.OriginalSegmentSentenceRelation(
                    segment=self.segment, sentence=sentences[0], number=1
                ),
                models.OriginalSegmentSentenceRelation(
                    segment=self.segment, sentence=sentences[2], number=3
                ),
            )
        )
        self.divider.find_changes([self.segment.work])
        expected = (
            'Checking "{title}"\n'
            'Warning: "One." is a very short sentence. '
            'Please check if it is an abbreviation instead.\n'
            'New relation found in {abbreviation} :1:\nTwo!\n\n'
            'New sentence found in {abbreviation} :1:\nThree?\n\n'
            'Stale relation found in {abbreviation} :1:\nNone\n\n'
        )
        self.assertEqual(
            stdout.getvalue(),
            expected.format(
                title=self.segment.work.title,
                abbreviation=self.segment.work.abbreviation,
            ),
        )

    def test_delete_unrelated_sentences(self, stdout):
        models.OriginalSentence.objects.create()
        self.divider.delete_unrelated_sentences()
        result = stdout.getvalue()
        self.assertIn('estate.OriginalSegmentSentenceRelation\': 0', result)
        self.assertIn('white_estate.OriginalSentence\': 1', result)
