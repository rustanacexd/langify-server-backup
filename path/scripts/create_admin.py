from path.models import User


def run(*args):
    password = args[0] if args else 'admin'
    User.objects.create_superuser('admin', 'admin@example.com', password)
