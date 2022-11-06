# Generated by Django 2.0 on 2017-12-20 20:38

import django_countries.fields

import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
import path.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0009_alter_user_last_name_max_length"),
        ("panta", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
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
                    "password",
                    models.CharField(max_length=128, verbose_name="password"),
                ),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="date joined",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 30 characters or fewer. Letters, digits and ./+/-/_ only.",
                        max_length=30,
                        unique=True,
                        validators=[path.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True,
                        max_length=30,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="first name",
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="last name",
                    ),
                ),
                (
                    "pseudonym",
                    models.CharField(
                        blank=True,
                        help_text="Use this name instead of the real name.",
                        max_length=100,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="pseudonym",
                    ),
                ),
                (
                    "name_display",
                    models.CharField(
                        choices=[
                            ("full", "full name"),
                            ("first", "first name"),
                            ("user", "user name"),
                        ],
                        default="full",
                        help_text="Name that is visible on the website for others.",
                        max_length=5,
                        verbose_name="name display",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        error_messages={
                            "unique": "This address is used already."
                        },
                        max_length=254,
                        unique=True,
                        verbose_name="e-mail address",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Profile image.",
                        upload_to="",
                        verbose_name="image",
                    ),
                ),
                (
                    "address",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="address",
                    ),
                ),
                (
                    "address_2",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="address 2"
                    ),
                ),
                (
                    "zip_code",
                    models.CharField(
                        blank=True, max_length=10, verbose_name="zip code"
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="city",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="state",
                    ),
                ),
                (
                    "country",
                    django_countries.fields.CountryField(
                        blank=True,
                        help_text="Enter the name of your country.",
                        max_length=2,
                        verbose_name="country",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True, max_length=40, verbose_name="phone number"
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[
                            ("af", "Afrikaans"),
                            ("ar", "Arabic"),
                            ("ast", "Asturian"),
                            ("az", "Azerbaijani"),
                            ("bg", "Bulgarian"),
                            ("be", "Belarusian"),
                            ("bn", "Bengali"),
                            ("br", "Breton"),
                            ("bs", "Bosnian"),
                            ("ca", "Catalan"),
                            ("cs", "Czech"),
                            ("cy", "Welsh"),
                            ("da", "Danish"),
                            ("de", "German"),
                            ("dsb", "Lower Sorbian"),
                            ("el", "Greek"),
                            ("en", "English"),
                            ("en-au", "Australian English"),
                            ("en-gb", "British English"),
                            ("eo", "Esperanto"),
                            ("es", "Spanish"),
                            ("es-ar", "Argentinian Spanish"),
                            ("es-co", "Colombian Spanish"),
                            ("es-mx", "Mexican Spanish"),
                            ("es-ni", "Nicaraguan Spanish"),
                            ("es-ve", "Venezuelan Spanish"),
                            ("et", "Estonian"),
                            ("eu", "Basque"),
                            ("fa", "Persian"),
                            ("fi", "Finnish"),
                            ("fr", "French"),
                            ("fy", "Frisian"),
                            ("ga", "Irish"),
                            ("gd", "Scottish Gaelic"),
                            ("gl", "Galician"),
                            ("he", "Hebrew"),
                            ("hi", "Hindi"),
                            ("hr", "Croatian"),
                            ("hsb", "Upper Sorbian"),
                            ("hu", "Hungarian"),
                            ("ia", "Interlingua"),
                            ("id", "Indonesian"),
                            ("io", "Ido"),
                            ("is", "Icelandic"),
                            ("it", "Italian"),
                            ("ja", "Japanese"),
                            ("ka", "Georgian"),
                            ("kab", "Kabyle"),
                            ("kk", "Kazakh"),
                            ("km", "Khmer"),
                            ("kn", "Kannada"),
                            ("ko", "Korean"),
                            ("lb", "Luxembourgish"),
                            ("lt", "Lithuanian"),
                            ("lv", "Latvian"),
                            ("mk", "Macedonian"),
                            ("ml", "Malayalam"),
                            ("mn", "Mongolian"),
                            ("mr", "Marathi"),
                            ("my", "Burmese"),
                            ("nb", "Norwegian Bokmål"),
                            ("ne", "Nepali"),
                            ("nl", "Dutch"),
                            ("nn", "Norwegian Nynorsk"),
                            ("os", "Ossetic"),
                            ("pa", "Punjabi"),
                            ("pl", "Polish"),
                            ("pt", "Portuguese"),
                            ("pt-br", "Brazilian Portuguese"),
                            ("ro", "Romanian"),
                            ("ru", "Russian"),
                            ("sk", "Slovak"),
                            ("sl", "Slovenian"),
                            ("sq", "Albanian"),
                            ("sr", "Serbian"),
                            ("sr-latn", "Serbian Latin"),
                            ("sv", "Swedish"),
                            ("sw", "Swahili"),
                            ("ta", "Tamil"),
                            ("te", "Telugu"),
                            ("th", "Thai"),
                            ("tr", "Turkish"),
                            ("tt", "Tatar"),
                            ("udm", "Udmurt"),
                            ("uk", "Ukrainian"),
                            ("ur", "Urdu"),
                            ("vi", "Vietnamese"),
                            ("zh-hans", "Simplified Chinese"),
                            ("zh-hant", "Traditional Chinese"),
                        ],
                        default="en",
                        max_length=5,
                        verbose_name="language",
                    ),
                ),
                (
                    "born",
                    models.DateField(
                        blank=True,
                        help_text="Format: YYYY-MM-DD, e.g. 1956-01-29.",
                        null=True,
                        validators=[path.validators.in_last_5_to_110_years],
                        verbose_name="date of birth",
                    ),
                ),
                (
                    "reputation",
                    models.PositiveIntegerField(
                        default=0, verbose_name="reputation"
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "users",
                "abstract": False,
                "verbose_name": "user",
            },
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name="HistoricalUser",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True,
                        blank=True,
                        db_index=True,
                        verbose_name="ID",
                    ),
                ),
                (
                    "password",
                    models.CharField(max_length=128, verbose_name="password"),
                ),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="date joined",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        db_index=True,
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 30 characters or fewer. Letters, digits and ./+/-/_ only.",
                        max_length=30,
                        validators=[path.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True,
                        max_length=30,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="first name",
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="last name",
                    ),
                ),
                (
                    "pseudonym",
                    models.CharField(
                        blank=True,
                        help_text="Use this name instead of the real name.",
                        max_length=100,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="pseudonym",
                    ),
                ),
                (
                    "name_display",
                    models.CharField(
                        choices=[
                            ("full", "full name"),
                            ("first", "first name"),
                            ("user", "user name"),
                        ],
                        default="full",
                        help_text="Name that is visible on the website for others.",
                        max_length=5,
                        verbose_name="name display",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        db_index=True,
                        error_messages={
                            "unique": "This address is used already."
                        },
                        max_length=254,
                        verbose_name="e-mail address",
                    ),
                ),
                (
                    "image",
                    models.TextField(
                        blank=True,
                        help_text="Profile image.",
                        max_length=100,
                        verbose_name="image",
                    ),
                ),
                (
                    "address",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="address",
                    ),
                ),
                (
                    "address_2",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="address 2"
                    ),
                ),
                (
                    "zip_code",
                    models.CharField(
                        blank=True, max_length=10, verbose_name="zip code"
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="city",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        validators=[path.validators.contains_captialized_word],
                        verbose_name="state",
                    ),
                ),
                (
                    "country",
                    django_countries.fields.CountryField(
                        blank=True,
                        help_text="Enter the name of your country.",
                        max_length=2,
                        verbose_name="country",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True, max_length=40, verbose_name="phone number"
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[
                            ("af", "Afrikaans"),
                            ("ar", "Arabic"),
                            ("ast", "Asturian"),
                            ("az", "Azerbaijani"),
                            ("bg", "Bulgarian"),
                            ("be", "Belarusian"),
                            ("bn", "Bengali"),
                            ("br", "Breton"),
                            ("bs", "Bosnian"),
                            ("ca", "Catalan"),
                            ("cs", "Czech"),
                            ("cy", "Welsh"),
                            ("da", "Danish"),
                            ("de", "German"),
                            ("dsb", "Lower Sorbian"),
                            ("el", "Greek"),
                            ("en", "English"),
                            ("en-au", "Australian English"),
                            ("en-gb", "British English"),
                            ("eo", "Esperanto"),
                            ("es", "Spanish"),
                            ("es-ar", "Argentinian Spanish"),
                            ("es-co", "Colombian Spanish"),
                            ("es-mx", "Mexican Spanish"),
                            ("es-ni", "Nicaraguan Spanish"),
                            ("es-ve", "Venezuelan Spanish"),
                            ("et", "Estonian"),
                            ("eu", "Basque"),
                            ("fa", "Persian"),
                            ("fi", "Finnish"),
                            ("fr", "French"),
                            ("fy", "Frisian"),
                            ("ga", "Irish"),
                            ("gd", "Scottish Gaelic"),
                            ("gl", "Galician"),
                            ("he", "Hebrew"),
                            ("hi", "Hindi"),
                            ("hr", "Croatian"),
                            ("hsb", "Upper Sorbian"),
                            ("hu", "Hungarian"),
                            ("ia", "Interlingua"),
                            ("id", "Indonesian"),
                            ("io", "Ido"),
                            ("is", "Icelandic"),
                            ("it", "Italian"),
                            ("ja", "Japanese"),
                            ("ka", "Georgian"),
                            ("kab", "Kabyle"),
                            ("kk", "Kazakh"),
                            ("km", "Khmer"),
                            ("kn", "Kannada"),
                            ("ko", "Korean"),
                            ("lb", "Luxembourgish"),
                            ("lt", "Lithuanian"),
                            ("lv", "Latvian"),
                            ("mk", "Macedonian"),
                            ("ml", "Malayalam"),
                            ("mn", "Mongolian"),
                            ("mr", "Marathi"),
                            ("my", "Burmese"),
                            ("nb", "Norwegian Bokmål"),
                            ("ne", "Nepali"),
                            ("nl", "Dutch"),
                            ("nn", "Norwegian Nynorsk"),
                            ("os", "Ossetic"),
                            ("pa", "Punjabi"),
                            ("pl", "Polish"),
                            ("pt", "Portuguese"),
                            ("pt-br", "Brazilian Portuguese"),
                            ("ro", "Romanian"),
                            ("ru", "Russian"),
                            ("sk", "Slovak"),
                            ("sl", "Slovenian"),
                            ("sq", "Albanian"),
                            ("sr", "Serbian"),
                            ("sr-latn", "Serbian Latin"),
                            ("sv", "Swedish"),
                            ("sw", "Swahili"),
                            ("ta", "Tamil"),
                            ("te", "Telugu"),
                            ("th", "Thai"),
                            ("tr", "Turkish"),
                            ("tt", "Tatar"),
                            ("udm", "Udmurt"),
                            ("uk", "Ukrainian"),
                            ("ur", "Urdu"),
                            ("vi", "Vietnamese"),
                            ("zh-hans", "Simplified Chinese"),
                            ("zh-hant", "Traditional Chinese"),
                        ],
                        default="en",
                        max_length=5,
                        verbose_name="language",
                    ),
                ),
                (
                    "born",
                    models.DateField(
                        blank=True,
                        help_text="Format: YYYY-MM-DD, e.g. 1956-01-29.",
                        null=True,
                        validators=[path.validators.in_last_5_to_110_years],
                        verbose_name="date of birth",
                    ),
                ),
                (
                    "reputation",
                    models.PositiveIntegerField(
                        default=0, verbose_name="reputation"
                    ),
                ),
                (
                    "history_id",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                ("history_date", models.DateTimeField()),
                (
                    "history_change_reason",
                    models.CharField(max_length=100, null=True),
                ),
                (
                    "history_type",
                    models.CharField(
                        choices=[
                            ("+", "Created"),
                            ("~", "Changed"),
                            ("-", "Deleted"),
                        ],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
                "verbose_name": "historical user",
            },
        ),
        migrations.CreateModel(
            name="Privilege",
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
                        choices=[
                            ("student", "student"),
                            ("contrib", "contributor"),
                            ("flagger", "flagger"),
                            ("initiat", "initiator"),
                            ("agreer", "agreer"),
                            ("transla", "translator"),
                            ("voter", "voter"),
                            ("reviewe", "reviewer"),
                            ("mentor", "mentor"),
                            ("moderat", "moderator"),
                            ("guardia", "guardian"),
                            ("amender", "amender"),
                            ("trustee", "trustee"),
                        ],
                        max_length=7,
                    ),
                ),
                ("language", models.CharField(max_length=2)),
                (
                    "trustee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="panta.Trustee",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="user",
            name="privileges",
            field=models.ManyToManyField(
                related_name="users",
                to="path.Privilege",
                verbose_name="privileges",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.Permission",
                verbose_name="user permissions",
            ),
        ),
    ]
