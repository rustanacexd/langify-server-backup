from django.db import migrations
from django.db.models import CharField, F, Func, OuterRef, Subquery, Value
from django.db.models.functions import Concat

MAPPING = {'CCH': 'CCh', 'SWK': 'SWk', 'CHS': 'ChS', 'PAM': 'PaM', 'CHL': 'ChL'}


def make_references_case_sensitive(apps, schema_editor):
    """
    Considers works that are currently (2019-04-22) imported in the production
    database only.
    """
    OriginalSegment = apps.get_model('panta', 'OriginalSegment')
    TranslatedSegment = apps.get_model('panta', 'TranslatedSegment')

    for old, new in MAPPING.items():
        func = Func(
            'reference', Value(old), Value(new), function='regexp_replace'
        )
        OriginalSegment.objects.filter(reference__startswith=old).update(
            reference=func
        )
        TranslatedSegment.objects.filter(reference__startswith=old).update(
            reference=func
        )


def add_position_references_for_model(model_name, apps):
    concat = Concat(
        'work__abbreviation',
        Value(' :'),
        F('position'),
        output_field=CharField(),
    )
    model = apps.get_model('panta', model_name)
    model.objects.filter(reference='').update(
        reference=Subquery(
            model.objects.filter(pk=OuterRef('pk'))
            .annotate(ref=concat)
            .values('ref')[:1]
        )
    )


def add_position_references(apps, schema_editor):
    """
    Adds references in the form "<abbreviation> :<position>" for segments that
    don't have a reference.
    """
    add_position_references_for_model('OriginalSegment', apps)
    add_position_references_for_model('TranslatedSegment', apps)


class Migration(migrations.Migration):

    dependencies = [('panta', '0042_auto_20190415_1630')]

    operations = [
        migrations.RunPython(make_references_case_sensitive),
        migrations.RunPython(add_position_references),
    ]
