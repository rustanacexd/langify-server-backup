# Generated by Django 2.0.9 on 2018-11-26 19:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("panta", "0027_auto_20181122_0112")]

    operations = [
        migrations.RemoveField(model_name="translatedsegment", name="progress")
    ]
