# Generated by Django 2.0.8 on 2018-08-14 09:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0016_auto_20180709_0817")]

    operations = [
        migrations.CreateModel(
            name="BaseTranslation",
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
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="date created"
                    ),
                ),
                (
                    "last_modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modified"
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[("en", "English"), ("de", "German")],
                        db_index=True,
                        max_length=7,
                        verbose_name="language",
                    ),
                ),
            ],
            options={
                "verbose_name": "base translation",
                "verbose_name_plural": "base translations",
            },
        ),
        migrations.CreateModel(
            name="BaseTranslationSegment",
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
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="date created"
                    ),
                ),
                (
                    "last_modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modified"
                    ),
                ),
                ("content", models.TextField(verbose_name="content")),
                (
                    "original",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="basetranslations",
                        to="panta.OriginalSegment",
                        verbose_name="original",
                    ),
                ),
                (
                    "translation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="translations",
                        to="panta.BaseTranslation",
                        verbose_name="translation",
                    ),
                ),
            ],
            options={
                "verbose_name": "base translation segment",
                "verbose_name_plural": "base translation segments",
            },
        ),
        migrations.CreateModel(
            name="BaseTranslator",
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
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="date created"
                    ),
                ),
                (
                    "last_modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modified"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=40, unique=True, verbose_name="name"
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("ai", "AI")],
                        max_length=5,
                        verbose_name="type",
                    ),
                ),
            ],
            options={
                "verbose_name": "base translator",
                "verbose_name_plural": "base translators",
            },
        ),
        migrations.AddField(
            model_name="basetranslation",
            name="translator",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="panta.BaseTranslator",
                verbose_name="translator",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="basetranslationsegment",
            unique_together={("original", "translation")},
        ),
        migrations.AlterUniqueTogether(
            name="basetranslation", unique_together={("translator", "language")}
        ),
    ]
