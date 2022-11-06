# Generated by Django 2.0.8 on 2018-09-26 09:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("path", "0010_auto_20180802_1202")]

    operations = [
        migrations.AlterField(
            model_name="historicalemailaddress",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="historicalemailaddresses",
                to=settings.AUTH_USER_MODEL,
            ),
        )
    ]
