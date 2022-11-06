from django.db import migrations, transaction
from django.db.models import Case, OuterRef, Q, Subquery, When
from panta import queries
from panta.constants import (
    IMPORTANT_HEADINGS,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)


def get_headings(work):
    """
    Returns a queryset of segments containing headings.
    """
    headings = (
        work.segments.filter(tag__in=IMPORTANT_HEADINGS)
        .order_by("-position")
        .only("pk", "position", "tag", "classes", "work", "last_modified")
    )
    return headings


def get_statistics_subquery(TranslatedSegment, progress):
    subquery = Case(
        When(
            ~Q(first_position=None),
            then=queries.SubqueryCount(
                TranslatedSegment.objects.filter(
                    important_headings=OuterRef("pk"), progress__gte=progress
                )
            ),
        )
    )
    return subquery


def update_headings(TranslatedSegment, queryset):
    """
    Updates the content and the statistics.

    To update more fields, simply delete all rows of the work.
    """
    count = queryset.update(
        content=Subquery(
            TranslatedSegment.objects.filter(pk=OuterRef("segment_id"))
            .annotate(
                proper_content=Case(
                    When(~Q(content=""), then="content"),
                    default="original__content",
                )
            )
            .values("proper_content")[:1]
        ),
        translation_done=get_statistics_subquery(
            TranslatedSegment, TRANSLATION_DONE
        ),
        review_done=get_statistics_subquery(TranslatedSegment, REVIEW_DONE),
        trustee_done=get_statistics_subquery(TranslatedSegment, TRUSTEE_DONE),
        date=Case(
            When(
                ~Q(first_position=None),
                then=Subquery(
                    TranslatedSegment.objects.filter(
                        important_headings=OuterRef("pk")
                    )
                    .order_by("-last_modified")
                    .values("last_modified")[:1]
                ),
            ),
            default=Subquery(
                TranslatedSegment.objects.filter(
                    important_heading=OuterRef("pk")
                ).values("last_modified")[:1]
            ),
        ),
    )
    return count


def insert_headings(ImportantHeading, TranslatedSegment, work):
    """
    Creates important headings for given work.
    """
    # Prepare segments
    chapters = []
    prev_heading = None
    prev_position = work.segments.count() + 1
    prev_level = 0
    headings = tuple(get_headings(work))
    h1_count = len([True for h in headings if h.tag == "h1"])
    few = 3

    for h in headings:
        # Don't include the title
        if h.tag == "h1" and h1_count == 1 and h is headings[-1]:
            prev_heading.segments_count += prev_position - 1
            prev_heading.first_position = 1
            continue

        # Include segments of the previous chapter in the current chapter
        # if these are a few only and the current heading is higher in
        # hierarchy
        level = int(h.tag[1])
        if h.position < prev_position - few or level >= prev_level:
            h.segments_count = prev_position - h.position
            h.first_position = h.position
            prev_heading = h
        else:
            prev_heading.segments_count += prev_position - h.position
            prev_heading.first_position = h.position
            h.segments_count = None
            h.first_position = None

        chapters.append(h)
        prev_position = h.position
        prev_level = level

    # Build headings
    chapters.reverse()
    objects = []
    last_number = 0

    for h in chapters:
        if h.first_position:
            last_number += 1
            number = last_number
        else:
            number = None
        objects.append(
            ImportantHeading(
                segment=h,
                number=number,
                first_position=h.first_position,
                position=h.position,
                tag=h.tag,
                classes=h.classes,
                work_id=work.pk,
                segments_count=h.segments_count,
                date=h.last_modified,
            )
        )

    with transaction.atomic():
        # Save headings
        objects = ImportantHeading.objects.bulk_create(objects)

        # Add segments
        for obj in objects:
            if obj.first_position:
                # Add all segments from 'first_position' to the end of the
                # chapter
                obj.segments.add(
                    *work.segments.filter(
                        position__gte=obj.first_position,
                        position__lt=obj.first_position + obj.segments_count,
                    )
                )

        # Add content and statistics
        update_headings(
            TranslatedSegment,
            ImportantHeading.objects.filter(pk__in=[o.pk for o in objects]),
        )


def create_headings(apps, schema_editor):
    ImportantHeading = apps.get_model("panta", "ImportantHeading")
    TranslatedSegment = apps.get_model("panta", "TranslatedSegment")
    TranslatedWork = apps.get_model("panta", "TranslatedWork")

    for work in TranslatedWork.objects.all():
        insert_headings(ImportantHeading, TranslatedSegment, work)


class Migration(migrations.Migration):
    dependencies = [("panta", "0036_auto_20190319_0233")]
    operations = [migrations.RunPython(create_headings)]
