from panta.models import Trustee


def run():
    Trustee.objects.create(
        name='Ellen White Estate', description='', code='EGWE'
    )
