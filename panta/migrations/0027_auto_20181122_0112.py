# Generated by Django 2.0.9 on 2018-11-22 01:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0026_auto_20181114_1140")]

    operations = [
        migrations.AlterField(
            model_name="translatedsegment",
            name="progress",
            field=models.CharField(
                choices=[
                    ("blank", "blank"),
                    ("in_translation", "in translation"),
                    ("translation_done", "translation done"),
                    ("in_review", "in review"),
                ],
                default="blank",
                max_length=16,
                verbose_name="progress",
            ),
        )
    ]
