# Generated by Django 2.0.4 on 2018-04-16 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0005_segmentcomment")]

    operations = [
        migrations.AddField(
            model_name="historicaltranslatedsegment",
            name="relative_id",
            field=models.PositiveSmallIntegerField(
                blank=True, null=True, verbose_name="relative ID"
            ),
        )
    ]
