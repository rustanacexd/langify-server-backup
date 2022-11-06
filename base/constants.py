import datetime
from collections import OrderedDict

from django.utils.translation import gettext, gettext_noop

# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# https://en.wikipedia.org/wiki/List_of_ISO_639-2_codes

# Language codes and names according to ISO 639-1 if not mentioned otherwise.
# They should equal ISO 639 in any case.
# Alternative language names should be listed in a comment.

ACTIVE_LANGUAGES = (
    ('am', gettext_noop('Amharic')),
    ('ar', gettext_noop('Arabic')),
    ('ber', gettext_noop('Berber')),
    ('bg', gettext_noop('Bulgarian')),
    ('ckb', gettext_noop('Central Kurdish')),  # ISO 639-3, Sorani
    ('zh', gettext_noop('Chinese')),  # There is simplified and traditional
    ('cs', gettext_noop('Czech')),
    ('en', gettext_noop('English')),
    ('fr', gettext_noop('French')),
    ('de', gettext_noop('German')),
    ('hi', gettext_noop('Hindi')),
    ('hu', gettext_noop('Hungarian')),
    ('id', gettext_noop('Indonesian')),
    ('it', gettext_noop('Italian')),
    ('ms', gettext_noop('Malay')),
    ('nb', gettext_noop('Norwegian Bokmål')),
    ('fa', gettext_noop('Persian')),  # Farsi
    ('pl', gettext_noop('Polish')),
    ('pt', gettext_noop('Portuguese')),
    ('ro', gettext_noop('Romanian')),  # Moldavian; Moldovan
    ('ru', gettext_noop('Russian')),
    ('rw', gettext_noop('Kinyarwanda')),
    ('ksw', gettext_noop("S'gaw Karen")),  # ISO 639-3
    ('es', gettext_noop('Spanish')),  # Castilian
    ('sw', gettext_noop('Swahili')),
    ('tl', gettext_noop('Tagalog')),
    ('toi', gettext_noop('Tonga (Zambia and Zimbabwe)')),
    ('tr', gettext_noop('Turkish')),
    ('uk', gettext_noop('Ukrainian')),
    ('ur', gettext_noop('Urdu')),
    ('vi', gettext_noop('Vietnamese')),
)

ADDITIONAL_LANGUAGES = (
    ('af', gettext_noop('Afrikaans')),
    ('hy', gettext_noop('Armenian')),
    ('bn', gettext_noop('Bengali')),  # Bangla
    ('my', gettext_noop('Burmese')),
    ('hr', gettext_noop('Croatian')),
    ('da', gettext_noop('Danish')),
    ('nl', gettext_noop('Dutch')),  # Flemish
    ('fi', gettext_noop('Finnish')),
    ('grt', gettext_noop('Garo')),  # ISO 639-3
    ('is', gettext_noop('Icelandic')),
    ('ilo', gettext_noop('Ilocano')),  # Iloko, ISO 639-2
    ('ja', gettext_noop('Japanese')),
    ('kha', gettext_noop('Khasi')),  # ISO 639-2
    ('ko', gettext_noop('Korean')),
    ('lv', gettext_noop('Latvian')),
    ('lt', gettext_noop('Lithuanian')),
    ('lus2', gettext_noop('Lushai')),  # Mizo, ISO 639-2 + 2
    ('mk', gettext_noop('Macedonian')),
    ('mg', gettext_noop('Malagasy')),
    ('mr', gettext_noop('Marathi')),
    # TODO clashes with Lushai, see https://en.wikipedia.org/wiki/Mizo_language
    ('lus', gettext_noop('Mizo')),  # ISO ??
    # TODO Is hil correct here? ISO 639-2 name is Hiligaynon
    # https://www.alsintl.com/resources/languages/Ilonggo/
    ('hil', gettext_noop('Panayan')),  # Hiligaynon, Ilonggo
    ('sr', gettext_noop('Serbian')),
    ('si', gettext_noop('Sinhala')),  # Sinhalese
    ('sk', gettext_noop('Slovak')),
    ('sv', gettext_noop('Swedish')),
    ('ta', gettext_noop('Tamil')),
    ('te', gettext_noop('Telugu')),
    ('th', gettext_noop('Thai')),
    ('ton', gettext_noop('Tongan (Tonga Islands)')),
)


LANGUAGES = sorted(ACTIVE_LANGUAGES + ADDITIONAL_LANGUAGES, key=lambda x: x[1])


def get_languages(lazy=False, exclude=(), additional=True):
    """
    Returns language code and translation managed name pairs as a list.

    Translation currently deactivated.
    """
    # if lazy:
    #     translated = gettext_lazy
    # else:
    #     translated = gettext
    translated = lambda x: x
    if additional:
        languages = LANGUAGES
    else:
        languages = ACTIVE_LANGUAGES
    return [(c, translated(n)) for c, n in languages if c not in exclude]


LANGUAGES_DICT = {code: gettext(name) for code, name in LANGUAGES}


PERMISSIONS = OrderedDict(
    (
        ('add_translation', 3),
        # Has to be the same as above (the system can't distinguish between an
        # add and change right now because both are put/patch)
        ('change_translation', 3),
        # Has to be the same as above (you can delete a translation by the
        # delete endpoint and by sending an emtpy draft -> there is no delete
        # check)
        ('delete_translation', 3),
        ('restore_translation', 4),
        ('add_comment', 3),
        ('change_comment', 3),
        ('delete_comment', 1),
        ('flag_comment', 3),
        ('flag_translation', 3),
        ('flag_user', 3),
        ('approve_translation', 100),
        ('disapprove_translation', 150),
        ('hide_comment', 500),
        ('review_translation', 1000),
        ('trustee', 1000000),
    )
)


ROLES = (
    ('translator', gettext('translator')),
    ('reviewer', gettext('reviewer')),
    ('trustee', gettext('trustee')),
)


COMMENT_DELETION_DELAY = datetime.timedelta(minutes=10)


_AVATAR = """<svg
        xmlns='http://www.w3.org/2000/svg'
        width='120'
        height='120'
        viewBox='0 0 120 120'
      >
      <rect width='100%' height='100%' fill='{color}'/>
      <path
          fill='white'
          d='M39.954 71.846c6.948-2.788 13.629-4.185 20.048-4.185 6.413 0
              13.094 1.396 20.043 4.185 6.947 2.793 10.424 6.444 10.424
              10.961v7.662H29.53v-7.662c0-4.517 3.475-8.168
              10.424-10.961zm30.734-16.303C67.724 58.514 64.156 60 60.002
              60c-4.16
              0-7.721-1.486-10.692-4.457-2.973-2.967-4.454-6.532-4.454-10.688
              0-4.16 1.48-7.75 4.454-10.782 2.971-3.03 6.532-4.542 10.692-4.542
              4.154 0 7.721 1.512 10.686 4.542 2.973 3.032 4.457 6.622 4.457
              10.782.001 4.156-1.484 7.721-4.457 10.688z'
      />
    </svg>"""


AVATAR = ' '.join(l.strip() for l in _AVATAR.split('\n'))


SYSTEM_USERS = (
    'AI',
    'AnonymousUser',
    'Automation',
    'egwwritings',
    'third-party',
    'TM',
)


UNTRUSTED_HTML_WARNING = gettext(
    'Warning: This field might contain HTML from untrusted sources!'
)
ALLOWED_HTML_TAGS = [
    'h1',
    'h2',
    'h3',
    'p',
    'ol',
    'ul',
    'li',
    'q',
    'code',
    'blockquote',
    'b',
    'u',
    'i',
    'strong',
    'strike',
]
