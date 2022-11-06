from django.db import migrations, models
from django.db.models.functions import Cast


def populate_published_2(apps, schema_editor):
    OriginalWork = apps.get_model('panta', 'OriginalWork')

    OriginalWork.objects.exclude(published='').update(
        published_2=Cast('published', models.IntegerField())
    )


def flush_published_2(apps, schema_editor):
    OriginalWork = apps.get_model('panta', 'OriginalWork')

    OriginalWork.objects.update(published_2=None)


class Migration(migrations.Migration):

    dependencies = [('panta', '0054_auto_20190523_2056')]

    operations = [migrations.RunPython(populate_published_2, flush_published_2)]
