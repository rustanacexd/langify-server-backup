import datetime
import re
from collections import OrderedDict

from django.utils.translation import gettext_noop

REQUIRED_APPROVALS = {
    'am': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ar': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ber': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'bg': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ckb': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'cs': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'de': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'en': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'es': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'fa': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'fr': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'hi': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'hu': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'id': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'it': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ms': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ksw': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'nb': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'pl': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'pt': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ro': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ru': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'rw': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'sw': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'tl': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'toi': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'tr': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'uk': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'ur': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'zh': {'translator': 0, 'reviewer': 2, 'trustee': 1},
    'vi': {'translator': 0, 'reviewer': 2, 'trustee': 1},
}

LANGUAGE_SPECIFIC_REPLACE = {
    'de': OrderedDict(
        (
            (' - ', ' – '),  # dash to en-dash
            ('....', '...'),
            ('….', ' …'),
            ('.…', ' …'),
        )
    ),
    'hu': OrderedDict((('EGW', 'E. G. W.'),)),
}

# To view them:
# from docutils.utils.smartquotes import smartchars
# pprint(smartchars.quotes)

# q = quote characters (" and ')
# e = ellipses

SMARTY_PANTS_ATTRS = {
    'am': 'qe',
    'ar': 'q',
    'ber': 'q',
    'bg': 'qe',
    'ckb': 'q',
    'cs': 'qe',
    'de': 'qe',
    'en': 'qe',
    'es': 'q',
    'fa': 'q',
    'fr': 'q',
    'hi': 'qe',
    'hu': 'qe',
    'id': 'q',
    'it': 'q',
    'ms': 'q',
    'ksw': 'q',
    'nb': 'q',
    'pl': 'q',
    'pt': 'q',
    'ro': 'q',
    'ru': 'qe',
    'rw': 'qe',
    'sw': 'q',
    'tl': 'q',
    'toi': 'q',
    'tr': 'qe',
    'uk': 'qe',
    'zh': 'e',
    'vi': 'q',
}

SMARTY_PANTS_MAPPING = {
    'am': 'eu',
    'ar': 'en',
    'ber': 'en',
    'bg': 'en',
    'ckb': 'en',
    'cs': 'en',
    'es': 'es-x-altquot',
    'fr': 'en',
    'hi': 'en',
    'hu': 'sr',
    'id': 'en',
    'it': 'en',
    'ms': 'en',
    'nb': 'en',
    'pl': 'en',
    'pt': 'pt-br',
    'ro': 'en',
    'ru': 'en',
    'tl': 'en',
    'uk': 'en',
    'zh': 'zh-tw',
}

HEADINGS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')

IMPORTANT_HEADINGS = ('h1', 'h2', 'h3')

PARAGRAPHS = ('p', 'hr', 'blockquote')

CLASSES = ('indent', 'noindent', 'preface', 'signature', 'date', 'place')

STANDARD_INLINE = {
    'a': {
        'class': ('ref', 'nolink'),
        'href': re.compile(r'^[^<>();]*$'),
        'hreflang': re.compile(r'^[a-z]{2}(_Han(s|t))?$'),
        'name': re.compile(r'^[\w._-]+$'),
    },
    'br': {},
    'em': {},
    'li': {},
    'span': {'class': ('comment', 'note', 'non-author', 'ltplace', 'msdate')},
    'strong': {},
    'sub': {},
    'sup': {},
    'td': {
        'class': ('vtop',),
        'align': ('center', 'right'),
        'colspan': re.compile(r'^\d+$'),
    },
    'th': {'class': ('left',), 'colspan': re.compile(r'^\d+$')},
    'tr': {'class': ('page',)},
    'ul': {},
    'h1': {},
    'h2': {},
    'h3': {},
    'h4': {},
    'h5': {},
    'h6': {},
    'p': {},
}

EGW_INLINE = {
    'span': {
        'data-link': re.compile(r'^[0-9.]+$'),
        'title': re.compile(r'^[\w -—.:?]+$'),
        'value': re.compile(r'^[\w -.,;’]+$'),
        'start': re.compile(r'^[\w -.,]+$'),
        'end': re.compile(r'^[\w -.,]+$'),
        'range': re.compile(r'^[\w]+$'),
    },
    'sup': {'class': None},
}

# todo: copy that as soon as we have multiple organizations
INLINE = STANDARD_INLINE

for k, d in EGW_INLINE.items():
    INLINE[k].update(d)

REPLACE = {'b': 'strong', 'i': 'em', 'div': None, 'p': None}

REMOVE_IF_EMPTY = ('br',)

HISTORICAL_UNIT_PERIOD = datetime.timedelta(minutes=30)
# Time period in which you can
# - edit a segment without creating a new historical record
#   (except you're another user)
# - undo your changes of this historical record and/or of the segment
#
# Considerations:
# You should be able to continue the work
# 1. if you had a short break (15 min)
# 2. after a meal (2 h)
# 3. on the next working day (70 h)
# On the other hand
# 4. others should be able to track changes. Changes should be reconstructable
#    when somebody reads it and comes back later. (30 min)
# Suggestion: We want to detect incomplete translations anyway. If we detect
# it we give a user 72 h time to complete it. If it is complete we give the
# user 30 min. You can undo your changes in a period of 30 min in any case.
# Solution: We just use the 30 min for now. See langify-docs/#9 for details.

CHANGE_REASONS = {
    'new': gettext_noop('New translation'),
    'change': gettext_noop('Edit translation'),
    'delete': gettext_noop('Clear translation'),
    'restore': gettext_noop('Restore #{id}'),
    'automation': gettext_noop('Automated edit'),
    'tm': gettext_noop('Translation memory entry'),
    'DeepL': gettext_noop('DeepL.com translation'),
    'import': gettext_noop('Import translation'),
}
# Note: Part of the restore and delete reasons are used to establish the last
# historical record in conclude_segments
# TODO in serializer:
# change_reason = record.history_change_reason.split('#') or similar
# change_reason = _(CHANGE_REASONS['restore']).format(id=change_reason[1])


# Statistics

# Please always use these variables, not the numbers directly!
# (In order to prevent errors after changes.)

BLANK = 0

IN_TRANSLATION = 1

TRANSLATION_DONE = 2

IN_REVIEW = 3

REVIEW_DONE = 4

TRUSTEE_DONE = 5

RELEASED = 6

LANGUAGE_RATIOS = {
    'de': 0.90,
    'en': 1.0,
    'sw': 0.75,
    # Not calculated
    'am': 0.70,
    'ar': 0.70,
    'ber': 1.0,
    'bg': 1.0,
    'ckb': 0.70,
    'cs': 0.80,
    'es': 0.90,
    'fa': 0.85,
    'fr': 0.85,
    'hi': 0.90,
    'hu': 0.50,  # todo: Bible texts are much shorter in hu but normal text not
    'id': 1.0,
    'it': 0.90,
    'ms': 0.80,
    'ksw': 1.0,
    'nb': 1.0,
    'pl': 0.90,
    'pt': 0.90,
    'ro': 0.90,
    'ru': 0.90,
    'rw': 1.0,
    'tl': 0.75,
    'toi': 0.90,
    'tr': 0.85,
    'uk': 0.90,
    'ur': 1.0,
    'zh': 0.25,
    'vi': 1.0,
}
