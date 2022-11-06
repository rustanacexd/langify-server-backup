from django.db import migrations
from django.db.models import F


def populate_history_relation(apps, schema_editor):
    HistoricalTranslatedSegment = apps.get_model(
        'panta', 'HistoricalTranslatedSegment'
    )

    HistoricalTranslatedSegment.objects.update(history_relation_id=F('id'))


class Migration(migrations.Migration):
    dependencies = [('panta', '0045_auto_20190502_1027')]
    operations = [migrations.RunPython(populate_history_relation)]
