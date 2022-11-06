import datetime
import json

from langify.celery import app
from panta.constants import CHANGE_REASONS
from panta.models import (
    BaseTranslation,
    BaseTranslationSegment,
    BaseTranslator,
    TranslatedSegment,
    WorkStatistics,
)
from panta.utils import get_system_user


def notify(start, message):
    time = str(datetime.datetime.now() - start)[:-7]
    with open('tasks.log', 'a') as log_file:
        log_file.write(f'{time} {message}\n')
    print(time, message)


def get_base_translation(type, language):
    if type == 'tm':
        name = 'translation memory'
    elif type == 'hb':
        name = 'third party'

    base_translator, created = BaseTranslator.objects.get_or_create(
        name=name, type=type
    )
    base_translation, created = BaseTranslation.objects.get_or_create(
        translator=base_translator, language=language
    )
    return base_translation


@app.task
def add_tm_paragraphs(language):
    """
    Adds content of similar segments as base translations.
    """
    segments = TranslatedSegment.objects.filter(work__language=language)
    user = get_system_user('TM')
    base_translation = get_base_translation('tm', language)
    now = datetime.datetime.now()
    notify(now, f'{now} ===============================')

    notify(now, 'Create base translations…')
    with open('similarities.jsons') as f:
        for i, line in enumerate(f, start=1):
            if i % 500 == 0:
                notify(now, f'Line {i}')
            data = json.loads(line)
            try:
                segment = segments.exclude(content='').get(
                    original__key=data[0][0]
                )
            except TranslatedSegment.DoesNotExist:
                continue
            # TODO Maybe also import TM when 100% similar and history is because
            # of AI or third-party base translation?
            # TODO Add support for segments < 100%
            keys = (p[1] for p in data if p[4] == 100)
            if not keys:
                continue
            similar = segments.filter(
                original__key__in=keys, content='', past=None
            )
            for s in similar:
                base_segment = BaseTranslationSegment.objects.create(
                    content=segment.content,
                    original_id=s.original_id,
                    translation=base_translation,
                )
                if s.history.exists():
                    # Edge case (
                    notify(now, f'History exists for {s}!')
                else:
                    s.add_to_history(
                        content=base_segment.content,
                        history_type='+',
                        history_date=base_segment.created,
                        history_change_reason=CHANGE_REASONS['tm'],
                        history_user=user,
                    )

    notify(now, 'Update pretranslated statistics…')
    WorkStatistics.update_pretranslated(language)
    # The other statistics get updated next time the update runs

    notify(now, 'Mission accomplished :)\n')


HUNGARIAN_TRANSLATION_QUALITY = {
    # From Peter. 1 = high quality, 2 = lower quality.
    'advent': 1,  # Advent Kiadó*
    'bik': 1,  # BIK Kiadó
    'felfedezesek': 1,  # Felfedezések Alapítvány*
    'egervari-dezso': 2,  # Egervári Dezső
    'boldog-elet': 1,  # Boldog Élet Alapítvány
    'egwk': 1,  # Ellen Gould White Könyvtár
    'unknown': 2,  # Unknown
    'gyarmati-es-tarsa': 2,  # Gyarmati és Társa
    'igazsag-hirnoke': 2,  # Igazság Hírnöke Könyvterjesztő
    'jelenvalo-igazsag-zurich': 2,  # Jelenvaló Igazság, Zürich
    'advent, felfedezesek': 1,  # Advent Kiadó, Felfedezések Alapítvány*
    'elet-es-egeszseg': 1,  # Élet és Egészség Kiadó*
    'reform-ujvidek': 2,  # Hetednap Adventista Reformmozgalom, Újvidék
    'bik, egwk': 1,  # BIK Kiadó, EGW Könyvtár
    'advent-ujvidek': 2,  # Keresztény Adventista Egyház, Újvidék*
    'viata-si-sanatate': 1  # Viață și Sănătate*
    # *= Approved by the church
}


@app.task
def import_hungarian_translations(path, start=None, rows=None, log=True):
    """
    Function to create base translations from a JSON file from Peter.

    All works should be protected during the process.

    Will probably be used once only.
    """
    with open(path) as f:
        data = json.load(f)
    user = get_system_user('third-party')
    base_translation = get_base_translation('hb', 'hu')
    # historical_segments = []
    now = datetime.datetime.now()
    notify(now, f'{now} ===============================')

    if start:
        data = data[start:]
    if rows:
        data = data[:rows]

    notify(now, 'Import segments…')
    for i, row in enumerate(data, start=1):
        if i % 500 == 0:
            notify(now, f'Row {i}')

        if row['publisher'] == 'egervari-dezso':
            # Skip low quality
            continue

        content = row['translation']
        if not content:
            continue

        try:
            segment = TranslatedSegment.objects.get(
                original__key=row['para_id'], work__language='hu', content=''
            )
        except TranslatedSegment.DoesNotExist:
            continue

        if HUNGARIAN_TRANSLATION_QUALITY[row['publisher']] == 1:
            segment.content = content
            segment.progress = segment.determine_progress(votes=False)
            segment.save_without_historical_record()
            obj = segment
        else:
            base_segment = BaseTranslationSegment.objects.create(
                content=content,
                original_id=segment.original_id,
                translation=base_translation,
            )
            obj = base_segment
        if segment.history.exists():
            notify(now, f'History exists for {row["para_id"]}!')
        else:
            segment.add_to_history(
                content=obj.content,
                history_type='+',
                history_date=obj.created,
                history_change_reason=CHANGE_REASONS['import'],
                history_user=user,
                # add_to=historical_segments,
            )

    # notify(now, 'Create history…')
    # TranslatedSegment.history.bulk_create(historical_segments)

    # notify(now, 'Sanitizse content…')
    # segments = TranslatedSegment.objects.filter(work__language='hu')
    # sanitize_content_of_queryset(segments)

    notify(now, 'Update pretranslated statistics…')
    WorkStatistics.update_pretranslated('hu')
    # The other statistics get updated next time the update runs

    notify(now, 'Mission accomplished :)\n')
