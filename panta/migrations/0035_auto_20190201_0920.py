# Generated by Django 2.0.10 on 2019-02-01 09:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0034_auto_20190121_2001")]

    operations = [
        migrations.AlterField(
            model_name="historicaloriginalsegment",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, verbose_name="reference"
            ),
        ),
        migrations.AlterField(
            model_name="originalsegment",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, verbose_name="reference"
            ),
        ),
        migrations.AlterField(
            model_name="translatedsegment",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, verbose_name="reference"
            ),
        ),
    ]
