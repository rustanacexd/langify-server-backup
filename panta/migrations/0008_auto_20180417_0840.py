# Generated by Django 2.0.4 on 2018-04-17 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0007_auto_20180417_0722")]

    operations = [
        migrations.AlterField(
            model_name="historicaltranslatedsegment",
            name="relative_id",
            field=models.PositiveSmallIntegerField(verbose_name="relative ID"),
        ),
        migrations.AlterUniqueTogether(
            name="historicaltranslatedsegment",
            unique_together={("id", "relative_id")},
        ),
    ]