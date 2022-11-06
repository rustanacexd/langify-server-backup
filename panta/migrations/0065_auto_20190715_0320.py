# Generated by Django 2.0.13 on 2019-07-15 03:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('panta', '0064_populate_originalwork_key')]

    operations = [
        migrations.AlterModelOptions(
            name='originalwork',
            options={
                'get_latest_by': 'created',
                'verbose_name': 'original work',
                'verbose_name_plural': 'original works',
            },
        ),
        migrations.AlterModelOptions(
            name='translatedwork',
            options={
                'get_latest_by': 'created',
                'verbose_name': 'translated work',
                'verbose_name_plural': 'translated works',
            },
        ),
    ]