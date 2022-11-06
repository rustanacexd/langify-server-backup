from django.db import migrations


def update_deepl_records(apps, schema_editor):
    """
    Creates a user "AI", assigns it to all historical DeepL records and
    updates their change reason to include the DeepL domain.
    """
    User = apps.get_model("path", "User")
    ai_user, created = User.objects.get_or_create(
        username="AI", defaults={"email": "ai@example.com"}
    )

    HistoricalTranslatedSegment = apps.get_model(
        "panta", "HistoricalTranslatedSegment"
    )
    history = HistoricalTranslatedSegment.objects.filter(
        history_change_reason="DeepL translation"
    )
    history.update(
        history_user=ai_user, history_change_reason="DeepL.com translation"
    )


def revert(apps, schema_editor):
    """
    We don't have to change anything when migrating backwards.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("panta", "0017_auto_20180814_0910"),
        ("path", "0010_auto_20180802_1202"),
    ]

    operations = [migrations.RunPython(update_deepl_records, revert)]
