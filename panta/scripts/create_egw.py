import datetime

from panta import models


def run():
    models.Author.objects.create(
        first_name='Ellen Gould',
        last_name='White',
        born=datetime.date(1827, 11, 26),
        bio='born Harmon',
    )
