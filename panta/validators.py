import regex as re
from bs4 import BeautifulSoup

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from panta.constants import INLINE

# http://www.regular-expressions.info/unicode.html

ALPHABET_CHARACTER_PATTERN = re.compile(r'^[\p{Ll}\p{Lo}]$')

ASCII_ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9]{2,4}$')

ROMAN_NUMERAL_PATTERN = re.compile(
    """
    ^                   # beginning of string
    M{0,4}              # thousands - 0 to 4 M's
    (CM|CD|D?C{0,3})    # hundreds - 900 (CM), 400 (CD), 0-300 (0 to 3 C's),
                        #            or 500-800 (D, followed by 0 to 3 C's)
    (XC|XL|L?X{0,3})    # tens - 90 (XC), 40 (XL), 0-30 (0 to 3 X's),
                        #        or 50-80 (L, followed by 0 to 3 X's)
    (IX|IV|V?I{0,3})    # ones - 9 (IX), 4 (IV), 0-3 (0 to 3 I's),
                        #        or 5-8 (V, followed by 0 to 3 I's)
    $                   # end of string
    """,
    re.VERBOSE,
)


def is_alphabet_character(value):
    if not ALPHABET_CHARACTER_PATTERN.match(value):
        msg = _('%(value)s is no alphabet character.')
        raise ValidationError(msg, params={'value': value})


def is_ascii_alphanumeric_character(value):
    # We need a function here because Django cannot serialize the compiled
    # regex if used as validator directly running a db migration (because
    # it's Python's re).
    if not ASCII_ALPHANUMERIC_PATTERN.match(value):
        msg = _('%(value)s is no ASCII alphanumeric character.')
        raise ValidationError(msg, params={'value': value})


def get_bullet_format(sequence, raise_error=True):
    """
    Distinguish between Arabic or Roman numeral or alphabet characters.
    """
    if re.match(r'^\d+$', sequence):
        return 'arabic'
    elif ROMAN_NUMERAL_PATTERN.match(sequence):
        return 'roman'
    elif ALPHABET_CHARACTER_PATTERN.match(sequence):
        return 'alphabetical'
    elif re.match(r'^\d+[a-z]+$', sequence):
        return 'arabic/alphabetical'
    if raise_error:
        msg = _(
            '%(sequence)s is neither an Arabic, nor a Roman numeral, '
            'nor a character of the alphabet.'
        )
        raise ValidationError(msg, params={'sequence': sequence})


def valid_tag(tag):
    from white_estate.models import Tag

    if not Tag.objects.filter(name=tag).exists():
        raise ValidationError(_('"{tag}" is not a valid tag.'.format(tag=tag)))


def valid_classes(classes):
    from white_estate.models import Class

    for c in classes:
        if not Class.objects.filter(name=c).exists():
            raise ValidationError(
                _('"{klass}" is not a valid class.'.format(klass=c))
            )


def valid_segment(content):
    from white_estate.models import Class, Tag

    if content == '':
        return

    #    soup = BeautifulSoup(content, 'lxml')
    #    # TODO tell lxml to not wrap content into
    #    # <html><body><p>...</p></body></html>
    #    html = soup.find('html')
    #    html.unwrap() # remove <html>
    #    body = soup.find('body')
    #    body.unwrap() # remove <body>
    #    if not content.startswith('<span'):
    #        p = soup.find('p')
    #        p.unwrap() # remove <p>
    soup = BeautifulSoup(content, 'html.parser')

    allowed_tags = {t.name: t for t in Tag.objects.all()}

    for e in soup.descendants:
        if e.name is not None:

            # Tag
            if e.name not in allowed_tags:
                msg = _('HTML tag "{tag}" in "{html}" is not allowed.')
                raise ValidationError(msg.format(tag=e.name, html=e))

            # Attributes
            allowed_attrs = INLINE[e.name].keys()
            remainder = set(e.attrs.keys()) - set(allowed_attrs)
            if remainder:
                msg = _(
                    'HTML attribute(s) "{attrs}" in "{html}" '
                    'is/are not allowed.'
                )
                raise ValidationError(
                    msg.format(attrs=', '.join(remainder), html=e)
                )

            # Values
            allowed_attrs = INLINE[e.name]
            for attr, allowed in allowed_attrs.items():
                value = e.get(attr)
                if value:
                    error_value = False
                    if attr == 'class':
                        classes = Class.objects.filter(
                            tag=allowed_tags[e.name], name__in=value
                        )
                        if classes.count() != len(value):
                            error_value = value
                    elif isinstance(allowed, tuple):
                        remainder = {value} - set(allowed)
                        if remainder:
                            error_value = remainder
                    else:
                        if not allowed.match(value):
                            error_value = value

                    if error_value:
                        msg = _(
                            'HTML value(s) "{values}" for attribute "{attr}" '
                            'in "{html}" is/are not allowed.'
                        )
                        raise ValidationError(
                            msg.format(values=error_value, attr=attr, html=e)
                        )

    # TODO SECURITY Check that you cannot save code anywhere!
    # Esspecially in href.

    # TODO Check that the original segment has the equivalent
    # tags, attrs, classes in same number (but not order) and that it
    # contains the same references (in TranslatedSegment.clean)
    # Move all the validation done in import to here (valid_segment)
