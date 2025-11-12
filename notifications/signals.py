"""
Señales para el sistema de notificaciones automáticas
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification
from .services import NotificationService
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def notify_user_registration(sender, instance, created, **kwargs):
    """
    Envía notificación de bienvenida cuando se registra un nuevo usuario
    """
    if created:
        try:
            NotificationService.send_notification(
                user=instance,
                notification_type='SYSTEM_ALERT',
                title='¡Bienvenido a SmartSales! 🎉',
                message='Gracias por registrarte. Explora nuestros productos y descubre ofertas exclusivas.',
                data={'user_id': instance.id},
                action_url='/products',
                action_text='Explorar Productos',
                icon='🎉'
            )
            logger.info(f"Notificación de bienvenida enviada a {instance.email}")
        except Exception as e:
            logger.error(f"Error enviando notificación de bienvenida a {instance.email}: {e}")


@receiver(pre_save, sender=Notification)
def set_notification_sent_at(sender, instance, **kwargs):
    """
    Establece la fecha de envío cuando se crea una notificación
    """
    if not instance.sent_at:
        instance.sent_at = timezone.now()