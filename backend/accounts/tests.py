from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings


class EnsureDefaultAdminCommandTests(TestCase):
    @override_settings(
        DEFAULT_ADMIN_USERNAME="admin",
        DEFAULT_ADMIN_EMAIL="admin@example.com",
        DEFAULT_ADMIN_PASSWORD="secret123!",
    )
    def test_command_creates_superuser(self):
        User = get_user_model()
        User.objects.all().delete()

        call_command("ensure_default_admin")

        user = User.objects.get(username="admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("secret123!"))
