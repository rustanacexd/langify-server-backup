# Generated by Django 2.0.4 on 2018-05-03 09:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0009_auto_20180425_1434")]

    operations = [
        migrations.AddField(
            model_name="segmentcomment",
            name="to_delete",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="to delete"
            ),
        )
    ]