"""
Señales para órdenes - notificaciones automáticas por cambios de estado
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order
from notifications.services import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """
    Rastrea cambios de estado en las órdenes para enviar notificaciones
    """
    if instance.pk:  # Solo si es una actualización
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def notify_order_status_change(sender, instance, created, **kwargs):
    """
    Envía notificaciones cuando cambia el estado de una orden
    """
    if created:
        # Nueva orden creada - ya se maneja en el webhook de pago
        return

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    # Solo enviar notificación si el estado cambió
    if old_status == new_status:
        return

    try:
        if new_status == 'ENVIADO' and old_status != 'ENVIADO':
            # Orden enviada
            NotificationService.notify_order_shipped(instance)
            logger.info(f"Notificación de envío enviada para orden {instance.id}")

        elif new_status == 'ENTREGADO' and old_status != 'ENTREGADO':
            # Orden entregada
            NotificationService.notify_order_delivered(instance)
            logger.info(f"Notificación de entrega enviada para orden {instance.id}")

        elif new_status == 'CANCELADO' and old_status != 'CANCELADO':
            # Orden cancelada
            NotificationService.send_notification(
                user=instance.user,
                notification_type='SYSTEM_ALERT',
                title='Orden Cancelada',
                message=f'Tu orden #{instance.id} ha sido cancelada.',
                data={'order_id': instance.id},
                action_url=f'/orders/{instance.id}',
                action_text='Ver Detalles',
                icon='❌'
            )
            logger.info(f"Notificación de cancelación enviada para orden {instance.id}")

    except Exception as e:
        logger.error(f"Error enviando notificación de cambio de estado para orden {instance.id}: {e}")