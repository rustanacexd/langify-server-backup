from django.db import migrations
from django.db.models import F


def populate_published(apps, schema_editor):
    OriginalWork = apps.get_model('panta', 'OriginalWork')

    OriginalWork.objects.update(published=F('published_2'))


class Migration(migrations.Migration):

    dependencies = [('panta', '0057_auto_20190523_2118')]

    operations = [migrations.RunPython(populate_published)]
