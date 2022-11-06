from panta import models


def run():
    models.TranslatedSegment.objects.all().delete()
    models.TranslatedSegment.history.all().delete()
    models.TranslatedWork.objects.all().delete()
    models.TranslatedWork.history.all().delete()
    models.OriginalSegment.objects.all().delete()
    models.OriginalSegment.history.all().delete()
    models.OriginalWork.objects.all().delete()
    models.OriginalWork.history.all().delete()
