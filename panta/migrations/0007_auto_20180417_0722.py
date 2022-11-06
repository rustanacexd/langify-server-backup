from django.db import migrations


def set_relative_ids(apps, schema_editor):
    """
    Give all existing objects an increasing ID for each segment ID.
    """
    HistoricalRecord = apps.get_model("panta", "HistoricalTranslatedSegment")
    records = HistoricalRecord.objects.all().order_by("id", "history_date")
    segment_id = 0
    relative_id = 0
    for record in records:
        if record.id != segment_id:
            segment_id = record.id
            relative_id = 1
        else:
            relative_id += 1
        # We can't use save because it overrides relative_id
        records.filter(pk=record.pk).update(relative_id=relative_id)


class Migration(migrations.Migration):

    dependencies = [("panta", "0006_historicaltranslatedsegment_relative_id")]

    operations = [migrations.RunPython(set_relative_ids)]
