from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure the configured default admin user exists"

    def handle(self, *args, **options):
        User = get_user_model()
        username = settings.DEFAULT_ADMIN_USERNAME
        if not username or not settings.DEFAULT_ADMIN_PASSWORD:
            self.stdout.write(self.style.WARNING("Default admin settings are not configured."))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": settings.DEFAULT_ADMIN_EMAIL},
        )
        should_set_default_password = (
            created
            or not user.has_usable_password()
            or user.email != settings.DEFAULT_ADMIN_EMAIL
        )
        user.email = settings.DEFAULT_ADMIN_EMAIL
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if should_set_default_password:
            user.set_password(settings.DEFAULT_ADMIN_PASSWORD)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Default admin user {action}: {username}"))
