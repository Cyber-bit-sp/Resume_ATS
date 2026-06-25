from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .management.commands.ensure_default_admin import Command as EnsureDefaultAdminCommand


@receiver(post_migrate)
def ensure_default_admin(sender, **kwargs):
    if sender.label != "accounts":
        return

    EnsureDefaultAdminCommand().handle()
