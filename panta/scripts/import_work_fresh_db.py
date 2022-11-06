from django.db import transaction
from path.scripts import create_admin

from . import create_egw, create_estate, create_licence, import_work


@transaction.atomic
def run(*args):
    create_admin.run()
    create_egw.run()
    create_estate.run()
    create_licence.run()
    import_work.run(*args)
