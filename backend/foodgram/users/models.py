from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.db import models


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=254,
        null=False,
        db_index=True
    )
    username = models.CharField(
        validators=[validators.RegexValidator(regex=r'^[\w.@+-]+\Z')],
        unique=True,
        max_length=150,
        null=False,
        db_index=True
    )
    first_name = models.CharField(max_length=150, null=False)
    last_name = models.CharField(max_length=150, null=False)
    password = models.CharField(max_length=150, null=False)
    subscriptions = models.ManyToManyField(
        to='self',
        related_name='subscribers',
        symmetrical=False
    )

    class Meta:
        ordering = ['email']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', ]
    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.username
