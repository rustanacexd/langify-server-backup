# Generated by Django 2.1.12 on 2020-01-30 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('path', '0025_merge_20191124_1549')]

    operations = [
        migrations.AlterField(
            model_name='historicaluser',
            name='language',
            field=models.CharField(
                blank=True,
                choices=[
                    ('af', 'Afrikaans'),
                    ('am', 'Amharic'),
                    ('ar', 'Arabic'),
                    ('hy', 'Armenian'),
                    ('bn', 'Bengali'),
                    ('ber', 'Berber'),
                    ('bg', 'Bulgarian'),
                    ('my', 'Burmese'),
                    ('ckb', 'Central Kurdish'),
                    ('zh', 'Chinese'),
                    ('hr', 'Croatian'),
                    ('cs', 'Czech'),
                    ('da', 'Danish'),
                    ('nl', 'Dutch'),
                    ('en', 'English'),
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
                    ('nb', 'Norwegian Bokmål'),
                    ('hil', 'Panayan'),
                    ('fa', 'Persian'),
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
                    ('ton', 'Tongan (Tonga Islands)'),
                    ('tr', 'Turkish'),
                    ('uk', 'Ukrainian'),
                    ('ur', 'Urdu'),
                    ('vi', 'Vietnamese'),
                ],
                max_length=5,
                verbose_name='language',
            ),
        ),
        migrations.AlterField(
            model_name='reputation',
            name='language',
            field=models.CharField(
                choices=[
                    ('af', 'Afrikaans'),
                    ('am', 'Amharic'),
                    ('ar', 'Arabic'),
                    ('hy', 'Armenian'),
                    ('bn', 'Bengali'),
                    ('ber', 'Berber'),
                    ('bg', 'Bulgarian'),
                    ('my', 'Burmese'),
                    ('ckb', 'Central Kurdish'),
                    ('zh', 'Chinese'),
                    ('hr', 'Croatian'),
                    ('cs', 'Czech'),
                    ('da', 'Danish'),
                    ('nl', 'Dutch'),
                    ('en', 'English'),
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
                    ('nb', 'Norwegian Bokmål'),
                    ('hil', 'Panayan'),
                    ('fa', 'Persian'),
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
                    ('ton', 'Tongan (Tonga Islands)'),
                    ('tr', 'Turkish'),
                    ('uk', 'Ukrainian'),
                    ('ur', 'Urdu'),
                    ('vi', 'Vietnamese'),
                ],
                max_length=5,
                verbose_name='language',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='language',
            field=models.CharField(
                blank=True,
                choices=[
                    ('af', 'Afrikaans'),
                    ('am', 'Amharic'),
                    ('ar', 'Arabic'),
                    ('hy', 'Armenian'),
                    ('bn', 'Bengali'),
                    ('ber', 'Berber'),
                    ('bg', 'Bulgarian'),
                    ('my', 'Burmese'),
                    ('ckb', 'Central Kurdish'),
                    ('zh', 'Chinese'),
                    ('hr', 'Croatian'),
                    ('cs', 'Czech'),
                    ('da', 'Danish'),
                    ('nl', 'Dutch'),
                    ('en', 'English'),
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
                    ('nb', 'Norwegian Bokmål'),
                    ('hil', 'Panayan'),
                    ('fa', 'Persian'),
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
                    ('ton', 'Tongan (Tonga Islands)'),
                    ('tr', 'Turkish'),
                    ('uk', 'Ukrainian'),
                    ('ur', 'Urdu'),
                    ('vi', 'Vietnamese'),
                ],
                max_length=5,
                verbose_name='language',
            ),
        ),
    ]
