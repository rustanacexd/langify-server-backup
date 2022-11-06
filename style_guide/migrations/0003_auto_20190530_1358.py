# Generated by Django 2.0.13 on 2019-05-30 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('style_guide', '0002_auto_20190524_1444')]

    operations = [
        migrations.AlterField(
            model_name='historicalstyleguide',
            name='language',
            field=models.CharField(
                choices=[
                    ('af', 'Afrikaans'),
                    ('am', 'Amharic'),
                    ('ar', 'Arabic'),
                    ('hy', 'Armenian'),
                    ('bn', 'Bengali'),
                    ('bg', 'Bulgarian'),
                    ('my', 'Burmese'),
                    ('ckb', 'Central Kurdish'),
                    ('zh', 'Chinese'),
                    ('hr', 'Croatian'),
                    ('cs', 'Czech'),
                    ('da', 'Danish'),
                    ('nl', 'Dutch'),
                    ('en', 'English'),
                    ('fa', 'Farsi'),
                    ('fi', 'Finnish'),
                    ('fr', 'French'),
                    ('grt', 'Garo'),
                    ('de', 'German'),
                    ('hi', 'Hindi'),
                    ('hu', 'Hungarian'),
                    ('is', 'Icelandic'),
                    ('ilo', 'Ilocano'),
                    ('id', 'Indonesian'),
                    ('it', 'Italian'),
                    ('ja', 'Japanese'),
                    ('kha', 'Khasi'),
                    ('rw', 'Kinyarwanda'),
                    ('ko', 'Korean'),
                    ('lv', 'Latvian'),
                    ('lt', 'Lithuanian'),
                    ('lus2', 'Lushai'),
                    ('mk', 'Macedonian'),
                    ('mg', 'Malagasy'),
                    ('ms', 'Malay'),
                    ('mr', 'Marathi'),
                    ('lus', 'Mizo'),
                    ('no', 'Norwegian'),
                    ('hil', 'Panayan'),
                    ('pl', 'Polish'),
                    ('pt', 'Portuguese'),
                    ('ro', 'Romanian'),
                    ('ru', 'Russian'),
                    ('ksw', "S'gaw Karen"),
                    ('sr', 'Serbian'),
                    ('si', 'Sinhala'),
                    ('sk', 'Slovak'),
                    ('es', 'Spanish'),
                    ('sw', 'Swahili'),
                    ('sv', 'Swedish'),
                    ('tl', 'Tagalog'),
                    ('ta', 'Tamil'),
                    ('te', 'Telugu'),
                    ('th', 'Thai'),
                    ('tr', 'Turkish'),
                    ('uk', 'Ukrainian'),
                    ('ur', 'Urdu'),
                    ('vi', 'Vietnamese'),
                ],
                db_index=True,
                max_length=7,
                verbose_name='language',
            ),
        ),
        migrations.AlterField(
            model_name='styleguide',
            name='language',
            field=models.CharField(
                choices=[
                    ('af', 'Afrikaans'),
                    ('am', 'Amharic'),
                    ('ar', 'Arabic'),
                    ('hy', 'Armenian'),
                    ('bn', 'Bengali'),
                    ('bg', 'Bulgarian'),
                    ('my', 'Burmese'),
                    ('ckb', 'Central Kurdish'),
                    ('zh', 'Chinese'),
                    ('hr', 'Croatian'),
                    ('cs', 'Czech'),
                    ('da', 'Danish'),
                    ('nl', 'Dutch'),
                    ('en', 'English'),
                    ('fa', 'Farsi'),
                    ('fi', 'Finnish'),
                    ('fr', 'French'),
                    ('grt', 'Garo'),
                    ('de', 'German'),
                    ('hi', 'Hindi'),
                    ('hu', 'Hungarian'),
                    ('is', 'Icelandic'),
                    ('ilo', 'Ilocano'),
                    ('id', 'Indonesian'),
                    ('it', 'Italian'),
                    ('ja', 'Japanese'),
                    ('kha', 'Khasi'),
                    ('rw', 'Kinyarwanda'),
                    ('ko', 'Korean'),
                    ('lv', 'Latvian'),
                    ('lt', 'Lithuanian'),
                    ('lus2', 'Lushai'),
                    ('mk', 'Macedonian'),
                    ('mg', 'Malagasy'),
                    ('ms', 'Malay'),
                    ('mr', 'Marathi'),
                    ('lus', 'Mizo'),
                    ('no', 'Norwegian'),
                    ('hil', 'Panayan'),
                    ('pl', 'Polish'),
                    ('pt', 'Portuguese'),
                    ('ro', 'Romanian'),
                    ('ru', 'Russian'),
                    ('ksw', "S'gaw Karen"),
                    ('sr', 'Serbian'),
                    ('si', 'Sinhala'),
                    ('sk', 'Slovak'),
                    ('es', 'Spanish'),
                    ('sw', 'Swahili'),
                    ('sv', 'Swedish'),
                    ('tl', 'Tagalog'),
                    ('ta', 'Tamil'),
                    ('te', 'Telugu'),
                    ('th', 'Thai'),
                    ('tr', 'Turkish'),
                    ('uk', 'Ukrainian'),
                    ('ur', 'Urdu'),
                    ('vi', 'Vietnamese'),
                ],
                max_length=7,
                unique=True,
                verbose_name='language',
            ),
        ),
    ]
