# Generated by Django 2.0.10 on 2019-01-21 20:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0033_auto_20181220_0142")]

    operations = [
        migrations.AlterField(
            model_name="historicaloriginalsegment",
            name="work",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="panta.OriginalWork",
                verbose_name="work",
            ),
        ),
        migrations.AlterField(
            model_name="historicaloriginalwork",
            name="author",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="panta.Author",
                verbose_name="author",
            ),
        ),
        migrations.AlterField(
            model_name="historicaloriginalwork",
            name="licence",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text=(
                    "Select the licence you want to publish this work under."
                ),
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="panta.Licence",
                verbose_name="licence",
            ),
        ),
        migrations.AlterField(
            model_name="historicaloriginalwork",
            name="trustee",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="panta.Trustee",
                verbose_name="trustee",
            ),
        ),
        migrations.AlterField(
            model_name="historicaltranslatedwork",
            name="original",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Select the original work.",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="panta.OriginalWork",
                verbose_name="original",
            ),
        ),
        migrations.AlterField(
            model_name="historicaltranslatedwork",
            name="trustee",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="panta.Trustee",
                verbose_name="trustee",
            ),
        ),
    ]