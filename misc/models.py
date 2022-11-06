import random
import re
from string import ascii_letters

from base.constants import UNTRUSTED_HTML_WARNING
from base.history import HistoricalRecords
from base.models import TimestampsModel
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _


class Page(TimestampsModel):
    """
    Page for HTML content.
    """

    slug = models.SlugField(_('slug'), unique=True)
    content = models.TextField(
        _('content'),
        help_text=_(
            'Email addresses and numbers beginning with a + are obfuscated.'
        ),
    )
    public = models.BooleanField(_('public'), default=False)
    contact_button = models.BooleanField(_('contact button'), default=False)
    rendered = models.TextField(_('rendered content'))
    protected = ArrayField(models.CharField(max_length=254), default=list)

    history = HistoricalRecords(excluded_fields=('rendered', 'protected'))

    def get_html_id(self):
        return ''.join(random.choice(ascii_letters) for x in range(15))

    def obfuscate_email(self, match):
        """
        Uses CSS to obfuscate an email address and try to stay barrier-free.
        """
        # https://www.hosteurope.de/blog/
        # 15-moeglichkeiten-die-e-mail-adresse-geschuetzt-darzustellen/
        position = len(self.protected)
        self.protected.append(match.group(0).replace('@', '%40'))
        local, domain = match.group(0).split('@')
        host, tld = domain.rsplit('.', maxsplit=1)
        id_local = self.get_html_id()
        id_extra = self.get_html_id()
        id_domain = self.get_html_id()

        email = (
            '<span id="{id_extra}">%3C!-- &lt;!--</span>'
            '<a href="{url}">'
            '<span id="{id_extra}"> {info} </span>'
            '<span id="{id_local}">{local}</span>'
            '<span id="{id_extra}">{extra}-</span>'
            '<span id="{id_domain}">{domain}<!--- - ->.shop <!-- --></span>'
            '<!-- --%gt; : <!-->.<!-- ; ---->{tld}'
            '</a>'
            '<span id="{id_extra}">--%3E</span>'
        )
        styles = (
            'span#{id_extra} {{display: none;}}'
            'span#{id_domain}::before {{content: "@";}}'
            # 'span#{id_domain} {{'
            #    'unicode-bidi:bidi-override; direction: rtl;'
            # '}}'
        )
        self.styles.append(
            styles.format(id_extra=id_extra, id_domain=id_domain)
        )
        return email.format(
            id_extra=id_extra,
            url=reverse('page_contact', args=(self.slug, position)),
            info=_('Click to send a message with your communication programm.'),
            id_local=id_local,
            local=local,
            extra=_('delete-{number}-this').format(
                number=random.randint(100000, 999999)
            ),
            id_domain=id_domain,
            domain=host,
            # domain=host[::-1],
            #          reverse
            tld=tld,
        )

    def obfuscate_phone(self, match):
        """
        Uses CSS to mask spaces and obfuscate a number and stay barrier-free.
        """
        parts = match.group(0).split()
        obfuscated = []
        id_space = self.get_html_id()
        self.styles.append(
            'span#{id_space} {{letter-spacing: 0.3em;}}'.format(
                id_space=id_space
            )
        )
        for p in parts:
            obfuscated.append(
                '{part_1}'
                '<!--- - ->0<!-- -->'
                '<span id="{id_space}">{part_2}</span>'.format(
                    id_space=id_space, part_1=p[:-1], part_2=p[-1]
                )
            )
        return ''.join(obfuscated)

    def save(self, *args, **kwargs):
        """
        Renders and obfuscates the content before saving.
        """
        self.styles = []
        self.protected = []
        rendered = re.sub(
            r'\+[0-9 ]{1}[0-9 /()-]{4,}', self.obfuscate_phone, self.content
        )
        rendered = re.sub(
            # https://www.regular-expressions.info/email.html
            r'[0-9a-z._%+-]+@[0-9a-z.-]+\.[a-z]{2,}',
            self.obfuscate_email,
            rendered,
            flags=re.IGNORECASE,
        )
        if self.styles:
            rendered = '<style type="text/css">{}</style>{}'.format(
                ''.join(self.styles), rendered
            )
        self.rendered = rendered
        super().save(*args, **kwargs)

    def __str__(self):
        return self.slug

    class Meta(TimestampsModel.Meta):
        verbose_name = _('page')
        verbose_name_plural = _('pages')


class Attachment(models.Model):
    """
    Files for pages.
    """

    file = models.FileField(_('file'), upload_to='pages/')
    page = models.ForeignKey(
        Page,
        verbose_name=_('page'),
        related_name='attachments',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.file.name

    class Meta:
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')


class DeveloperComment(TimestampsModel):
    """
    Comment for developers.
    """

    # TODO Markdown
    content = models.TextField(
        'content', max_length=2000, help_text=UNTRUSTED_HTML_WARNING
    )
    user = models.ForeignKey(
        get_user_model(),
        verbose_name=_('user'),
        related_name='developercomments',
        on_delete=models.PROTECT,
    )
    to_delete = models.DateTimeField('to delete', blank=True, null=True)

    def __str__(self):
        return Truncator(self.content).chars(10)

    class Meta(TimestampsModel.Meta):
        verbose_name = _('developer comment')
        verbose_name_plural = _('developer comments')
