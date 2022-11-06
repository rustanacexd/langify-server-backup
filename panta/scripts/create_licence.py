from panta.models import Licence


def run():
    Licence.objects.create(title='New Licence', description='Dummy licence')
