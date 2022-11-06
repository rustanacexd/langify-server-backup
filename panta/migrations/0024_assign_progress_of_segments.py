from bs4 import BeautifulSoup

from django.db import migrations
from panta.constants import LANGUAGE_RATIOS

BLANK = "blank"
IN_REVIEW = "in_review"
IN_TRANSLATION = "in_translation"
TRANSLATION_DONE = "translation_done"


def determine_progress(segment):
    """
    Returns the progress state of the segment.
    """
    if segment.content == "":
        return BLANK

    # Remove HTML tags because we don't have a feature to set reference links
    # yet.
    original = BeautifulSoup(segment.original.content, "html.parser")
    translation = BeautifulSoup(segment.content, "html.parser")

    length_original = len(original.get_text())
    required = LANGUAGE_RATIOS[segment.work.language]
    if length_original <= 50:
        required /= 2
    if len(translation.get_text()) / length_original <= required:
        return IN_TRANSLATION
    return TRANSLATION_DONE


def assign_progress(queryset):
    """
    Determines and assigns the current progress state for queryset's segments.

    Returns the updated segments. The segments' works and originals should be
    included (with 'select_related').
    """
    states = {
        BLANK: [],
        IN_TRANSLATION: [],
        TRANSLATION_DONE: [],
        IN_REVIEW: [],
    }
    for segment in queryset:
        states[determine_progress(segment)].append(segment.pk)

    count = 0
    for state, pks in states.items():
        count += queryset.filter(pk__in=pks).update(progress=state)

    return count


def assign_segment_progress(apps, schema_editor):
    TranslatedSegment = apps.get_model("panta", "TranslatedSegment")
    assign_progress(TranslatedSegment.objects.exclude(content=""))


class Migration(migrations.Migration):

    dependencies = [("panta", "0023_translatedsegment_progress")]

    operations = [migrations.RunPython(assign_segment_progress)]
