from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_default_admin(sender, **kwargs):
    if sender.label != "accounts":
        return

    User = get_user_model()
    username = settings.DEFAULT_ADMIN_USERNAME
    if not username or not settings.DEFAULT_ADMIN_PASSWORD:
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
