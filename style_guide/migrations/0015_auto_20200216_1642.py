# Generated by Django 2.1.12 on 2020-02-16 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('style_guide', '0014_merge_20200216_1626')]

    operations = [
        migrations.AddField(
            model_name='historicalissue',
            name='is_from_style_guide',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='issue',
            name='is_from_style_guide',
            field=models.BooleanField(default=False),
        ),
    ]
