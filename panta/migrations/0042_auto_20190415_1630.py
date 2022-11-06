# Generated by Django 2.0.13 on 2019-04-15 16:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('panta', '0041_populate_chapters')]

    operations = [
        migrations.RemoveField(model_name='importantheading', name='segments'),
        migrations.AlterField(
            model_name='translatedsegment',
            name='chapter',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='segments',
                to='panta.ImportantHeading',
                verbose_name='chapter',
            ),
        ),
    ]