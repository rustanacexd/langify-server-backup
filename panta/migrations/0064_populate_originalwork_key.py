from django.db import migrations


def populate_key(apps, schema_editor):
    OriginalWork = apps.get_model('panta', 'OriginalWork')
    HistoricalOriginalWork = apps.get_model('panta', 'HistoricalOriginalWork')

    for work in OriginalWork.objects.all():
        key = work.segments.first().key.split('.')[0]
        work.key = key
        work.save()
        HistoricalOriginalWork.objects.filter(id=work.pk).update(key=key)


class Migration(migrations.Migration):

    dependencies = [('panta', '0063_auto_20190626_1658')]

    operations = [migrations.RunPython(populate_key)]
