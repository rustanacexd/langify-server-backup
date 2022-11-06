from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from panta.models import TranslatedSegment, TranslatedWork


class Command(BaseCommand):
    help = 'Delete a translated work by primary key'

    def add_arguments(self, parser):
        parser.add_argument('id', help='Target translated work by primary key')

    def handle(self, *args, **options):
        pk = options.pop('id')
        try:
            translated_work = TranslatedWork.objects.get(pk=pk)
        except TranslatedWork.DoesNotExist:
            raise CommandError("Book doesn't exist")

        # check if any translated segments not empty
        if (
            TranslatedSegment.objects.filter(work=pk)
            .exclude(content='')
            .exists()
        ):
            self.stderr.write('Translation has already began for this book.')
            return
        with transaction.atomic():
            for segment in translated_work.segments.all():
                for vote in segment.votes.all():
                    for segment_comment in vote.segmentcomments.all():
                        segment_comment.delete()
                    vote.delete()

                for draft in segment.drafts.all():
                    draft.delete()

                segment.delete()

            for comment in translated_work.segmentcomments.all():
                comment.delete()

            print(translated_work.delete())
            self.stdout.write(
                self.style.SUCCESS('Successfully deleted translated work. ')
            )
