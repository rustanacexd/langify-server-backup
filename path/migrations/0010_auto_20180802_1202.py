# Generated by Django 2.0.8 on 2018-08-02 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("path", "0009_historicalemailaddress")]

    operations = [
        migrations.AlterField(
            model_name="historicaluser",
            name="name_display",
            field=models.CharField(
                choices=[("full", "full name"), ("user", "username")],
                default="full",
                help_text="Name that is visible on the website for others.",
                max_length=5,
                verbose_name="name display",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="name_display",
            field=models.CharField(
                choices=[("full", "full name"), ("user", "username")],
                default="full",
                help_text="Name that is visible on the website for others.",
                max_length=5,
                verbose_name="name display",
            ),
        ),
    ]
