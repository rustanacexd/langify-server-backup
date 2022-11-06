from django.db import migrations
from django.utils.text import slugify


def populate_slug(apps, schema_editor):
    Tag = apps.get_model('panta', 'Tag')

    for t in Tag.objects.all():
        t.slug = slugify(t.name)
        t.clean()
        t.save()


class Migration(migrations.Migration):

    dependencies = [('panta', '0051_tag_slug')]

    operations = [migrations.RunPython(populate_slug)]
