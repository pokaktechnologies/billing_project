from django.db import models
from django.conf import settings

from .activity_log import create_log, get_current_user

class BaseModel(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True


    def save(self, *args, **kwargs):
        is_create = self.pk is None

        user = getattr(self, '_current_user', None)

        if not user:
            user = get_current_user()

        print("USER:", user)

        #  SAFE CHECK
        if user and user.is_authenticated:
            if is_create:
                self.created_by = user

        super().save(*args, **kwargs)

        #  SAFE LOGGING
        if user and user.is_authenticated:
            if is_create:
                create_log(user, 'CREATE', self)
            else:
                create_log(user, 'UPDATE', self)

    def delete(self, *args, **kwargs):
        user = getattr(self, '_current_user', None)

        if not user:
            user = get_current_user()

        #  SAFE CHECK
        if user and user.is_authenticated:
            create_log(user, 'DELETE', self)

        super().delete(*args, **kwargs)