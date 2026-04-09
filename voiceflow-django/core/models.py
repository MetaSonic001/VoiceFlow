import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with multi-tenant support."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=255, default="", db_index=True)
    company_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "django_users"

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            self.tenant_id = f"tenant-{self.id}"
        super().save(*args, **kwargs)
