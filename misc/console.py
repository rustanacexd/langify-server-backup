from pprint import pprint  # noqa: E402

from panta import models
from path.models import Reputation, User  # noqa: E402

segments = models.TranslatedSegment.objects.all()
for s in segments:
    if s.content:
        print(
            str(s.position).ljust(5),
            s.reference.ljust(8),
            'characters:',
            str(len(s.original.content)).ljust(4),
            str(len(s.content)).ljust(4),
            'ratio:',
            str(len(s.original.content) / len(s.content)).ljust(20),
            'characters without whitespaces:',
            str(len(s.original.content.replace(' ', ''))).ljust(4),
            str(len(s.content.replace(' ', ''))).ljust(4),
            'ratio:',
            str(
                len(s.original.content.replace(' ', ''))
                / len(s.content.replace(' ', ''))
            ).ljust(20),
            'words:',
            str(len(s.original.content.split())).ljust(4),
            str(len(s.content.split())).ljust(4),
            'ratio:',
            str(len(s.original.content.split()) / len(s.content.split())).ljust(
                20
            ),
        )


segments = models.TranslatedSegment.objects.filter(
    position__gte=1940, position__lte=2035
).select_related('original')
ratios = {}


def add_ratio(ratio, type):
    ratio = round(ratio, 2)
    if ratio in ratios:
        if type in ratios[ratio]:
            ratios[ratio][type] += 1
        else:
            ratios[ratio][type] = 1
    else:
        ratios[ratio] = {type: 1}


for s in segments:
    add_ratio(len(s.original.content) / len(s.content), 'characters')
    add_ratio(
        len(s.original.content.replace(' ', ''))
        / len(s.content.replace(' ', '')),
        'characters_no_white',
    )
    add_ratio(len(s.original.content.split()) / len(s.content.split()), 'words')

pprint(ratios)


# Assign reputation


users = User.objects.exclude(username='AnonymousUser')
for u in users:
    Reputation.objects.create(user=u, score=5, language='de')
