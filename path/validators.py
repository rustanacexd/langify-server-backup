import datetime

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


def html_free(string):
    """
    Validates that the input does not include "<", ">" or "=".
    """
    for c in ('<', '>', '='):
        if c in string:
            msg = _(
                '"{character}" is not allowed in this field. '
                'Please remove it.'
            )
            raise ValidationError(msg.format(character=c))


def contains_captialized_word(words):
    """
    Validates that words contain a capital letter as usual for a name.
    """
    upper = False
    lower = False
    words = words.replace("'", ' ').replace('’', ' ').replace('-', ' ').split()
    for w in words:
        if upper and lower:
            break
        if w[0].isupper():
            upper = True
        for c in w:
            if lower:
                break
            if c.islower():
                lower = True
    if not upper or not lower:
        msg = _('Please take account of upper and lower case.')
        raise ValidationError(msg)


def in_last_5_to_110_years(date_of_birth):
    """
    Validates that the birth of date lays in the last 5 to 110 years.
    """
    current_year = datetime.date.today().year
    birth_year = date_of_birth.year
    if not current_year - 110 < birth_year < current_year - 5:
        raise ValidationError(_('Date of birth cannot be real.'))


class UnicodeUsernameValidator(RegexValidator):
    regex = r'^[\w.+-]+$'
    message = _(
        'Please enter a valid username. It may contain only letters, '
        'numbers and the characters . + - _. Spaces are not allowed.'
    )
    flags = 0
