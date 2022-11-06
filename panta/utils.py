import functools
import json
import operator
from datetime import date, timedelta

import lxml.etree
from docutils.utils.smartquotes import smartyPants
from xmldiff import formatting
from xmldiff.main import diff_texts

from base.constants import SYSTEM_USERS
from django.contrib.auth import get_user_model
from django.db import transaction
from frontend_urls import SEGMENT
from langify.celery import app
from misc.apis import MailjetClient

from . import models
from .constants import (
    BLANK,
    CHANGE_REASONS,
    IMPORTANT_HEADINGS,
    IN_REVIEW,
    IN_TRANSLATION,
    LANGUAGE_SPECIFIC_REPLACE,
    REMOVE_IF_EMPTY,
    REPLACE,
    REVIEW_DONE,
    SMARTY_PANTS_ATTRS,
    SMARTY_PANTS_MAPPING,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)

XSLT = """<?xml version="1.0"?>
    <xsl:stylesheet version="1.0"
       xmlns:diff="http://namespaces.shoobx.com/diff"
       xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

       <xsl:template match="@diff:insert-formatting">
           <xsl:attribute name="class">
             <xsl:value-of select="'insert-formatting'"/>
           </xsl:attribute>
       </xsl:template>

       <xsl:template match="diff:delete">
           <del><xsl:apply-templates /></del>
       </xsl:template>

       <xsl:template match="diff:insert">
           <ins><xsl:apply-templates /></ins>
       </xsl:template>

       <xsl:template match="@* | node()">
         <xsl:copy>
           <xsl:apply-templates select="@* | node()"/>
         </xsl:copy>
       </xsl:template>
    </xsl:stylesheet>
"""

XSLT_TEMPLATE = lxml.etree.fromstring(XSLT)


class HTMLFormatter(formatting.XMLFormatter):
    def render(self, result):
        transform = lxml.etree.XSLT(XSLT_TEMPLATE)
        result = transform(result)
        return super().render(result)


def get_system_user(username):
    """
    Returns the system user with given username.
    """
    assert username in SYSTEM_USERS
    email = '{}@example.com'.format(username.lower())
    user, created = get_user_model().objects.get_or_create(
        username=username, defaults={'email': email}
    )
    assert (
        user.email == email
    ), 'Somebody else has registered with the username "{}"!'.format(username)
    return user


def add_segments_to_deepl_queue(work, language):
    """
    Adds all segments of the given original work to the Deepl translation queue.
    """
    segments = [
        json.dumps({'work': work.pk, 'language': language, 'position': p})
        for p in work.segments.values_list('position', flat=True)
    ]
    key = 'next_deepl_segments'
    redis = app.broker_connection().default_channel.client
    redis.rpush(key, *segments)
    return {'added': len(segments), 'total': redis.llen(key)}


def notify_users(to=None, sandbox=False):
    """
    Notifies users about segments they voted and that have been edited recently.

    Uses Mailjet to send the e-mails. Considered edits are from yesterday.
    """
    # Get all segments that were edited yesterday
    records = (
        models.TranslatedSegment.history.filter(
            history_date__date=date.today() - timedelta(1)
        )
        .order_by('history_date')
        .prefetch_related('votes__user')
    )

    # Get the newest votes of each user
    newest_votes = {r.id: {} for r in records}
    for record in records:
        for vote in record.votes.all():
            if vote.user.subscribed_edits:
                newest_votes[record.id][vote.user_id] = vote.date
    current_votes = models.Vote.objects.filter(
        segment_id__in=records.values('id'), user__subscribed_edits=True
    )
    for vote in current_votes:
        newest_votes[vote.segment_id][vote.user_id] = vote.date

    # Find out if the user voted again
    notify_users = {}
    last_votes = {}
    for record in records:
        for vote in record.votes.all():
            send = vote.user.subscribed_edits
            if send and newest_votes[record.id][vote.user_id] == vote.date:
                # The user didn't vote after the edit again
                try:
                    notify_users[vote.user_id].append(record.id)
                except KeyError:
                    notify_users[vote.user_id] = [record.id]

                try:
                    last_votes[vote.user_id][record.id] = record.content
                except KeyError:
                    last_votes[vote.user_id] = {record.id: record.content}

    # Create the e-mail messages
    users = get_user_model().objects.filter(pk__in=notify_users)
    segments = (
        models.TranslatedSegment.objects
        # https://stackoverflow.com/a/45323085
        .filter(
            pk__in=functools.reduce(operator.iconcat, notify_users.values(), [])
        )
        # Segments of the same chapter should be near each other in the e-mail
        .order_by('work', 'position').select_related('work')
    )
    headings_qs = models.TranslatedSegment.objects.filter(
        work_id__in=segments.values('work_id'), tag__in=IMPORTANT_HEADINGS[1:]
    ).only('work_id', 'position')
    headings = {}
    for heading in headings_qs:
        try:
            headings[heading.work_id].append(heading.position)
        except KeyError:
            headings[heading.work_id] = [heading.position]

    mailjet = MailjetClient()
    formatter = HTMLFormatter(
        text_tags=('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'),
        formatting_tags=('a', 'em', 'span', 'strong', 'sub', 'sup', 'u'),
    )
    p = '<p>{}</p>'  # Required to generate valid XML
    url = 'https://www.ellen4all.org/{}'
    segment_attrs = ('diff', 'reference', 'url', 'button')
    for user in users:
        # TODO Translate
        subject = 'Edits of translations you voted for'
        heading = 'List of edited texts'
        introduction = (
            'We are excited that people like you were diligent and reviewed '
            'our translations! Below you find the texts that were edited '
            'recently. Help us by coming over and vote for the edits!'
        )
        button = 'Open chapter {}'
        unsubscribe_note = (
            'You received this e-mail because you voted for translations on '
            'Ellen4all.org. Therefore, we assume you want to get this '
            'notification. If you do not want this type of e-mail '
            'notification anymore, please reply to this message with a short '
            'note saying so.'
        )

        works = {}
        for segment in segments:
            if segment.pk not in notify_users[user.pk]:
                continue
            segment.diff = diff_texts(
                p.format(last_votes[user.pk][segment.pk]),
                p.format(segment.content),
                formatter=formatter,
            )
            chapter = 1
            for i, position in enumerate(headings[segment.work_id], start=1):
                if position > segment.position:
                    break
                chapter = i
            segment.button = button.format(chapter)
            segment.url = url.format(
                SEGMENT.format(
                    work_language=segment.work.language,
                    work_id=segment.work.pk,
                    # TODO Use 'ImportantHeading' here
                    chapter=chapter,
                    # TODO Use
                    # 'segment.position - ImportantHeading.first_position' here
                    position_in_chapter=1,
                )
            )
            try:
                works[segment.work].append(segment)
            except KeyError:
                works[segment.work] = [segment]

        works = [
            {
                'title': w.title,
                'segments': [
                    {k: getattr(s, k) for k in segment_attrs} for s in ss
                ],
            }
            for w, ss in works.items()
        ]

        mailjet.create_email(
            id=640_058,
            to=to or user.email,
            subject=subject,
            context={
                'heading': heading,
                'introduction': introduction,
                'works': works,
                'unsubscribe_note': unsubscribe_note,
            },
        )

    # Send e-mails
    if mailjet.messages:
        mailjet.send(sandbox=sandbox)

    return users, segments


def sanitize_content(text, language='en'):
    """
    Replaces and removes HTML and text characters and strings.
    """
    # Articles
    # - https://csswizardry.com/2017/02/typography-for-developers/
    # - https://en.wikipedia.org/wiki/Ellipsis
    # - https://en.wikipedia.org/wiki/Non-English_usage_of_quotation_marks
    # - https://www.duden.de/sprachwissen/rechtschreibregeln
    # - https://sprachenquilt.com/2009/03/26/
    #   gedankenstrich-und-bindestrich-en-dash-und-em-dash-und-die-leertaste/
    # - https://daringfireball.net/projects/smartypants/
    #
    # Other smartypants packages (seem to support English only but might be
    # more sophisticated)
    # - https://pythonhosted.org/smartypants/ seems to be
    #   https://github.com/leohemsted/smartypants.py
    # - https://python-markdown.github.io/extensions/smarty/
    #
    # Autoquote
    # This might be an interesting addition or alternative (less languages)
    # - https://www.scribus.net/websvn/filedetails.php?repname=Scribus
    #   &path=%2Ftrunk%2FScribus%2Fscribus%2Fplugins%2Fscriptplugin%2F
    #   scripts%2FAutoquote2.py
    # - https://wiki.scribus.net/canvas/
    #   Convert_Typewriter_Quotes_to_Typographic_Quotes
    # - https://wiki.scribus.net/canvas/Autoquote2
    # - https://opensource.com/article/17/3/python-scribus-smart-quotes

    # Replace nbsps
    while '&nbsp;' in text:
        text = text.replace('&nbsp;', ' ')

    # Replace and remove HTML tags
    wraps = ('<{}>', '</{}>')
    for old, new in REPLACE.items():
        for wrap in wraps:
            old_tag = wrap.format(old)
            new_tag = wrap.format(new) if new else ''
            while old_tag in text:
                text = text.replace(old_tag, new_tag)

    # Replace language specific strings
    for find, replace in LANGUAGE_SPECIFIC_REPLACE.get(language, {}).items():
        while find in text:
            text = text.replace(find, replace)

    # Strip spaces
    text = text.strip()

    # Remove superfluous (white) spaces
    # http://stackoverflow.com/a/15913564
    while '  ' in text:
        text = text.replace('  ', ' ')

    # Remove HTML tags if text is empty
    modified_content = text
    wraps = ('<{}>', '<{}/>', '<{} />')
    for tag in REMOVE_IF_EMPTY:
        for wrap in wraps:
            remove = wrap.format(tag)
            while remove in modified_content:
                modified_content = modified_content.replace(remove, '')

    if modified_content == '':
        return ''

    # Transform quotes and create ellipses
    text = smartyPants(
        text,
        SMARTY_PANTS_ATTRS.get(language, '0'),
        SMARTY_PANTS_MAPPING.get(language, language),
    )

    return text


@transaction.atomic
def sanitize_content_of_queryset(queryset, save=True):
    """
    Sanitizes the content of given segments skipping locked ones.

    For use in the console. Prints messages.
    """
    user = get_system_user('Automation')

    for segment in queryset.select_related('work').select_for_update():
        sanitized = sanitize_content(segment.content, segment.work.language)
        if sanitized != segment.content:
            segment._history_user = user
            segment.changeReason = CHANGE_REASONS['automation']
            segment.content = sanitized
            if segment.locked_by_id:
                print(
                    'Skipped sanitizing {} because it is locked!'.format(
                        str(segment)
                    )
                )
                continue
            if save:
                segment.save()
            print('Sanitized {}'.format(str(segment)))

    return queryset


def assign_progress(queryset):
    """
    Determines and assigns the current progress state for queryset's segments.

    Returns the updated segments.
    """
    states = {
        state: []
        for state in (
            BLANK,
            IN_TRANSLATION,
            TRANSLATION_DONE,
            IN_REVIEW,
            REVIEW_DONE,
            TRUSTEE_DONE,
        )
    }
    for segment in queryset.add_2_votes().select_related('work', 'original'):
        states[segment.determine_progress()].append(segment.pk)

    count = 0
    for state, pks in states.items():
        count += queryset.filter(pk__in=pks).update(progress=state)

    return count
