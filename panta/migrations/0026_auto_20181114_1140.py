# Generated by Django 2.0.9 on 2018-11-14 11:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0025_auto_20181112_1828")]

    operations = [
        migrations.AlterModelOptions(
            name="vote",
            options={
                "get_latest_by": "date",
                "verbose_name": "vote",
                "verbose_name_plural": "votes",
            },
        ),
        migrations.RemoveField(model_name="vote", name="assessment"),
        migrations.AddField(
            model_name="vote",
            name="revoke",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Only true if this vote resets the total vote of the user, "
                    "segment and role to 0, not in case of opposite votes."
                ),
                verbose_name="revoke",
            ),
        ),
        migrations.AddField(
            model_name="vote",
            name="value",
            field=models.SmallIntegerField(
                choices=[(-2, "-2"), (-1, "-1"), (1, "+1"), (2, "+2")],
                default=1,
                verbose_name="value",
            ),
            preserve_default=False,
        ),
    ]
