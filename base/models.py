from django.db import models
from django.utils.translation import gettext_lazy as _


class TimestampsModel(models.Model):
    """
    Abstract model class with dates created and last modified.
    """

    created = models.DateTimeField(_('date created'), auto_now_add=True)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)

    class Meta:
        abstract = True
        # TODO ordering = ['-created']
        get_latest_by = 'created'
