from psycopg2 import ProgrammingError, connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Deletes the test database if it exists.'

    def handle(self, *args, **kwargs):
        db_settings = settings.DATABASES['default']
        connection = connect(
            dbname='postgres',
            user=db_settings['USER'],
            host=db_settings['HOST'],
            password=db_settings['PASSWORD'],
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        curser = connection.cursor()
        name = f'test_{db_settings["NAME"]}'

        try:
            curser.execute(f'DROP DATABASE {name}')
        except ProgrammingError:
            msg = f'Test DB "{name}" could not be deleted or was not found.'
            self.stdout.write(self.style.NOTICE(msg))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Test database "{name}" was deleted.')
            )
        finally:
            curser.close()
            connection.close()
