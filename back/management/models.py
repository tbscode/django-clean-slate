from django.db import models


class Profile(models.Model):
    """
    Default Profile model, fields:
    first_name: ...
    second_name: ...
    """
    first_name = models.CharField(
        max_length=150,
        blank=False,
        default=None  # Will raise 'IntegrityError' if not passed
    )

    second_name = models.CharField(
        max_length=150,
        blank=False,
        default=None
    )
