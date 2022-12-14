# Generated by Django 2.0.9 on 2018-10-22 07:11

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("panta", "0020_auto_20181011_1859"),
    ]

    operations = [
        migrations.CreateModel(
            name="Vote",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("translator", "translator"),
                            ("reviewer", "reviewer"),
                            ("trustee", "trustee"),
                        ],
                        max_length=10,
                        verbose_name="role",
                    ),
                ),
                (
                    "assessment",
                    models.CharField(
                        choices=[("+", "+"), ("-", "-")],
                        max_length=1,
                        verbose_name="assessment",
                    ),
                ),
                (
                    "date",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date"
                    ),
                ),
                (
                    "historical_segments",
                    models.ManyToManyField(
                        blank=True,
                        related_name="votes",
                        to="panta.HistoricalTranslatedSegment",
                        verbose_name="historical segment",
                    ),
                ),
                (
                    "segment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="votes",
                        to="panta.TranslatedSegment",
                        verbose_name="segment",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="votes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={"verbose_name": "vote", "verbose_name_plural": "votes"},
        ),
        migrations.AddField(
            model_name="segmentcomment",
            name="role",
            field=models.CharField(
                choices=[
                    ("translator", "translator"),
                    ("reviewer", "reviewer"),
                    ("trustee", "trustee"),
                ],
                default="translator",
                max_length=10,
                verbose_name="role",
            ),
            preserve_default=False,
        ),
    ]
