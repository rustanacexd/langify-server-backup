# Generated by Django 2.0.13 on 2019-06-25 21:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('panta', '0061_auto_20190613_1122')]

    operations = [
        migrations.AlterIndexTogether(
            name='translatedsegment',
            index_together={('position', 'work', 'original')},
        )
    ]
