# Generated by Django 2.1.12 on 2019-10-23 02:04

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('path', '0023_user_flagged')]

    operations = [
        migrations.CreateModel(
            name='FlagUser',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'reason',
                    models.CharField(blank=True, max_length=200, null=True),
                ),
            ],
        ),
        migrations.RemoveField(model_name='user', name='flagged'),
        migrations.AddField(
            model_name='flaguser',
            name='flagged',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='flagged_user',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='flaguser',
            name='flagger',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='flagger_user',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='flags',
            field=models.ManyToManyField(
                related_name='flagged_by',
                through='path.FlagUser',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
