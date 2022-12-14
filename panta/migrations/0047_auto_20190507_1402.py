# Generated by Django 2.0.13 on 2019-05-07 14:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('panta', '0046_populate_history_relation')]

    operations = [
        migrations.CreateModel(
            name='WorkStatistics',
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
                    'segments',
                    models.PositiveSmallIntegerField(verbose_name='segments'),
                ),
                (
                    'translated_count',
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name='translated'
                    ),
                ),
                (
                    'reviewed_count',
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name='reviewed'
                    ),
                ),
                (
                    'authorized_count',
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name='authorized'
                    ),
                ),
                (
                    'translated_percent',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=5,
                        verbose_name='translated (%)',
                    ),
                ),
                (
                    'reviewed_percent',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=5,
                        verbose_name='reviewed (%)',
                    ),
                ),
                (
                    'authorized_percent',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=5,
                        verbose_name='authorized (%)',
                    ),
                ),
                (
                    'contributors',
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name='contributors'
                    ),
                ),
                (
                    'last_activity',
                    models.DateTimeField(
                        blank=True,
                        help_text=(
                            '`last_modified` of the last modified segment.'
                        ),
                        null=True,
                        verbose_name='last activity',
                    ),
                ),
                (
                    'work',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='statistics',
                        to='panta.TranslatedWork',
                        verbose_name='work',
                    ),
                ),
            ],
            options={
                'verbose_name': 'work statistics',
                'verbose_name_plural': 'work statistics',
            },
        ),
        migrations.AddField(
            model_name='historicaltranslatedsegment',
            name='work',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='panta.TranslatedWork',
                verbose_name='work',
            ),
        ),
        migrations.AlterField(
            model_name='historicaltranslatedsegment',
            name='history_relation',
            field=models.ForeignKey(
                db_constraint=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='past',
                to='panta.TranslatedSegment',
            ),
        ),
    ]
