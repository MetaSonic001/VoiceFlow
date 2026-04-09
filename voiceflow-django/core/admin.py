from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "tenant_id", "company_name", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Tenant Info", {"fields": ("tenant_id", "company_name")}),
    )
