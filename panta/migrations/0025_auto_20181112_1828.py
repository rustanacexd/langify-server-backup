# Generated by Django 2.0.9 on 2018-11-12 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panta", "0024_assign_progress_of_segments")]

    operations = [
        migrations.CreateModel(
            name="Tag",
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
                    "name",
                    models.CharField(
                        max_length=40, unique=True, verbose_name="name"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="originalwork",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                related_name="originalworks",
                to="panta.Tag",
                verbose_name="tags",
            ),
        ),
        migrations.AddField(
            model_name="translatedwork",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                related_name="translatedworks",
                to="panta.Tag",
                verbose_name="tags",
            ),
        ),
    ]