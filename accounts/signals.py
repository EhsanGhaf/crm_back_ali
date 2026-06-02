from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Team
from tickets.services import ZammadService

User = get_user_model()

# @receiver(post_save, sender=User)
# def sync_user_to_zammad(sender, instance, created, **kwargs):
#     zammad = ZammadService()
#
#     roles = ["Admin", "Agent"] if instance.is_superuser else ["Agent"]
#
#     identifier = instance.email if instance.email else f"{instance.username}@crm.local"
#
#     try:
#         zammad.sync_admin_user(
#             email=identifier,
#             firstname=instance.first_name or "کارشناس",
#             lastname=instance.last_name or instance.username,
#             roles=roles
#         )
#     except Exception as e:
#         print(f"Error syncing user to Zammad in signal: {e}")

@receiver(post_save, sender=Team)
def sync_team_to_zammad(sender, instance, created, **kwargs):
    zammad = ZammadService()
    try:
        zammad.sync_group(
            name=instance.name,
            is_active=instance.is_active,
        )
    except Exception as e:
        print(f"Error syncing team to Zammad in signal: {e}")