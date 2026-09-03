"""Django admin registration. Mounted under the dev settings only."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, EmailVerification, PasswordReset


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_active", "is_verified", "is_suspended"]
    list_filter = ["is_active", "is_verified", "is_suspended", "is_staff", "auth_provider"]
    search_fields = ["email", "first_name", "last_name", "phone_number"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        ("Status", {"fields": ("is_active", "is_verified", "is_suspended", "auth_provider")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )


class OneTimeCodeAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "used", "used_at"]
    list_filter = ["used"]
    search_fields = ["user__email"]
    readonly_fields = ["code", "created_at", "used_at"]


admin.site.register(EmailVerification, OneTimeCodeAdmin)
admin.site.register(PasswordReset, OneTimeCodeAdmin)
