from base.constants import LANGUAGES_DICT
from django.core.management.base import BaseCommand, CommandError
from white_estate.utils import OpenTranslations


class Command(BaseCommand):
    help = 'Create books for a given language.'

    def add_arguments(self, parser):
        parser.add_argument('language', help='Target language e.g "de"')

    def handle(self, *args, **options):
        language = options.pop('language')
        if language not in LANGUAGES_DICT.keys():
            raise CommandError('Invalid language.')

        books_count = OpenTranslations(language).create_books()
        self.stdout.write(
            self.style.SUCCESS(
                'Successfully created {} books.'.format(books_count)
            )
        )
