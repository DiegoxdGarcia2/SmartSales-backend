"""
Señales para productos - notificaciones de stock disponible
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Product
from notifications.services import NotificationService
from orders.models import OrderItem
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Product)
def track_stock_change(sender, instance, **kwargs):
    """
    Rastrea cambios de stock para notificar cuando vuelve a estar disponible
    """
    if instance.pk:  # Solo si es una actualización
        try:
            old_product = Product.objects.get(pk=instance.pk)
            instance._old_stock = old_product.stock
        except Product.DoesNotExist:
            instance._old_stock = 0
    else:
        instance._old_stock = 0


@receiver(post_save, sender=Product)
def notify_stock_available(sender, instance, created, **kwargs):
    """
    Envía notificaciones cuando un producto vuelve a estar disponible
    """
    if created:
        # Nuevo producto - no necesitamos notificar
        return

    old_stock = getattr(instance, '_old_stock', 0)
    new_stock = instance.stock

    # Solo notificar si pasó de 0 a algo positivo
    if old_stock == 0 and new_stock > 0:
        try:
            # Obtener usuarios que han comprado este producto antes
            # o que han mostrado interés (por ejemplo, agregándolo al carrito)
            interested_users = set()

            # Usuarios que han comprado este producto
            buyers = OrderItem.objects.filter(
                product=instance
            ).values_list('order__user', flat=True).distinct()

            interested_users.update(buyers)

            # Enviar notificación a cada usuario interesado
            for user_id in interested_users:
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                    
                    NotificationService.notify_stock_available(
                        user=user,
                        product=instance
                    )
                    logger.info(f"Notificación de stock disponible enviada para producto {instance.name} a usuario {user_id}")
                except User.DoesNotExist:
                    logger.warning(f"Usuario {user_id} no encontrado para notificación de stock")
                except Exception as e:
                    logger.error(f"Error notificando stock disponible a usuario {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error general notificando stock disponible para producto {instance.name}: {e}")


"""
Señales para reseñas - notificaciones cuando se crean reseñas nuevas
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Review
from notifications.services import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Review)
def notify_new_review(sender, instance, created, **kwargs):
    """
    Envía notificación cuando se crea una reseña nueva
    (útil para administradores o para el sistema de gamificación)
    """
    if created:
        try:
            # Notificar al administrador sobre reseña nueva
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Obtener administradores
            admins = User.objects.filter(is_staff=True, is_active=True)
            
            for admin in admins:
                NotificationService.send_notification(
                    user=admin,
                    notification_type='SYSTEM_ALERT',
                    title='Nueva Reseña Recibida',
                    message=f'{instance.user.username} ha reseñado "{instance.product.name}" con {instance.rating} estrellas.',
                    data={
                        'review_id': instance.id,
                        'product_id': instance.product.id,
                        'rating': instance.rating
                    },
                    action_url=f'/admin/products/review/{instance.id}',
                    action_text='Ver Reseña',
                    icon='⭐'
                )
            
            logger.info(f"Notificación de nueva reseña enviada para reseña {instance.id}")
            
        except Exception as e:
            logger.error(f"Error enviando notificación de nueva reseña {instance.id}: {e}")