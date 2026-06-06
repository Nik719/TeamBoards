# Signals: auto-create Company + api_key when a new User is saved
import secrets

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Company


@receiver(post_save, sender=User)
def create_company_profile(sender, instance, created, **kwargs):
    if created:
        Company.objects.create(
            user=instance,
            company_name=instance.username,   # overwritten by RegisterView
            api_key=secrets.token_urlsafe(32),
        )
