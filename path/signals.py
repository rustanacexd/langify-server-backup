import hashlib
import logging

from base.constants import ACTIVE_LANGUAGES
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from . import models

# Information about logging:
# https://www.owasp.org/index.php/Logging_Cheat_Sheet
# http://arctecgroup.net/pdf/howtoapplogging.pdf
# https://www.codeproject.com/Articles/42354/The-Art-of-Logging


logger = logging.getLogger(__name__)

log_message = (
    '{timestamp} '
    'priority={priority}, '
    'system=mainserver, '
    'module={module}, '
    'source={url}, '
    'service={protocol}, '
    'method={method}, '
    'user={user}, '
    'sessionhash={session}, '
    'ipaddress={ip_address}, '
    'useragent={user_agent}, '
    'action={action}, '
    'object=user account, '
    'status={status}, '
    'reason={reason}'
)


def log_authentication(sender, user, request, level, action, status, reason):
    log = getattr(logger, level)
    if level == 'info':
        priority = 1
    elif level == 'warning':
        priority = 3
    if request:
        try:
            url = request.get_raw_uri()
        except KeyError:
            url = request.get_full_path()
        if request.session.session_key:
            session_hash = hashlib.md5().hexdigest()
        else:
            session_hash = ''
        log(
            log_message.format(
                timestamp=timezone.now(),
                priority=priority,
                module=sender,
                url=url,  # todo: add port?
                protocol=request.META.get('SERVER_PROTOCOL', ''),
                method=request.method,
                user=user,
                session=session_hash,
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                action=action,
                status=status,
                reason=reason,
            )
        )
    else:
        log(
            log_message.format(
                timestamp=timezone.now(),
                priority=priority,
                module=sender,
                url='',
                protocol='',
                method='',
                user=user,
                session='',
                ip_address='',
                user_agent='',
                action=action,
                status=status,
                reason=reason,
            )
        )


@receiver(user_logged_in, dispatch_uid='logged_in')
def log_login(sender, user, request, **kwargs):
    log_authentication(
        sender.__module__,
        user.pk,
        request,
        level='info',
        action='login',
        status='success',
        reason='',
    )


@receiver(user_logged_out, dispatch_uid='logged_out')
def log_logout(sender, user, request, **kwargs):
    if user:
        user = user.pk
        status = 'success'
        reason = ''
    else:
        user = ''
        status = 'useless'
        reason = 'user was not logged in'

    log_authentication(
        sender.__module__,
        user,
        request,
        level='info',
        action='logout',
        status=status,
        reason=reason,
    )


@receiver(user_login_failed, dispatch_uid='login_failed')
def log_login_failed(sender, credentials, request, **kwargs):
    log_authentication(
        sender,
        credentials.get('username') or credentials['email'],
        request,
        level='warning',
        action='login',
        status='fail',
        reason='user not authenticated in database check',
    )


@receiver(post_save, sender=models.User, dispatch_uid='assign_reputations')
def assign_reputations(sender, instance, created, raw, **kwargs):
    """
    Assigns a reputation of 5 automatically until we support it otherwise.
    """
    if created and not raw:
        reputations = []
        for code, name in ACTIVE_LANGUAGES:
            if code != 'en':
                reputations.append(
                    models.Reputation(score=5, language=code, user=instance)
                )
        models.Reputation.objects.bulk_create(reputations)
