# Generated on 2018-05-22 17:24

import random
from string import ascii_letters, digits

from django.db import migrations


def assign_public_ids(apps, shema_editor):
    User = apps.get_model("path", "User")
    for user in User.objects.all():
        user.public_id = "".join(
            [random.choice(ascii_letters + digits) for ch in range(8)]
        )
        user.save()


class Migration(migrations.Migration):

    dependencies = [("path", "0005_user_public_id")]

    operations = [migrations.RunPython(assign_public_ids)]
