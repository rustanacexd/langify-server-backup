# Generated by Django 2.0.9 on 2018-12-24 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("path", "0014_auto_20181213_2139")]

    operations = [
        migrations.AddField(
            model_name="historicaluser",
            name="subscribed_edits",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="subscribed_edits",
            field=models.BooleanField(default=True),
        ),
    ]
