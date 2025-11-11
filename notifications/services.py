"""
Servicio centralizado para el envío de notificaciones
Soporta 3 canales: IN_APP, PUSH (FCM), EMAIL
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from firebase_admin import messaging
from .models import Notification, NotificationPreference, DeviceToken
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Servicio para enviar notificaciones a través de múltiples canales.
    """
    
    @staticmethod
    def send_notification(user, notification_type, title, message, 
                         data=None, action_url=None, action_text=None,
                         channels=None, icon=None):
        """
        Envía una notificación al usuario a través de los canales especificados.
        
        Args:
            user: Usuario destinatario
            notification_type: Tipo de notificación (ORDER_CONFIRMED, NEW_OFFER, etc.)
            title: Título de la notificación
            message: Mensaje de la notificación
            data: Datos adicionales en formato JSON (opcional)
            action_url: URL para redirigir al hacer clic (opcional)
            action_text: Texto del botón de acción (opcional)
            channels: Lista de canales ['IN_APP', 'PUSH', 'EMAIL'] (opcional, usa preferencias si no se especifica)
            icon: Icono de la notificación (opcional)
        
        Returns:
            dict: Resultado del envío por cada canal
        """
        try:
            # Obtener preferencias del usuario
            prefs, _ = NotificationPreference.objects.get_or_create(user=user)
            
            # Si no se especifican canales, usar las preferencias del usuario
            if channels is None:
                channels = []
                if NotificationService._check_preference(prefs, notification_type, 'IN_APP'):
                    channels.append('IN_APP')
                if NotificationService._check_preference(prefs, notification_type, 'PUSH'):
                    channels.append('PUSH')
                if NotificationService._check_preference(prefs, notification_type, 'EMAIL'):
                    channels.append('EMAIL')
            
            results = {}
            
            # Enviar por cada canal
            for channel in channels:
                try:
                    if channel == 'IN_APP':
                        notification = Notification.objects.create(
                            user=user,
                            type=notification_type,
                            channel='IN_APP',
                            title=title,
                            message=message,
                            data=data,
                            action_url=action_url,
                            action_text=action_text,
                            icon=icon
                        )
                        results['IN_APP'] = {'success': True, 'notification_id': notification.id}
                        logger.info(f"✅ Notificación IN_APP enviada a {user.email}: {title}")
                    
                    elif channel == 'PUSH':
                        push_result = NotificationService._send_push(
                            user, title, message, data, action_url, icon
                        )
                        results['PUSH'] = push_result
                        
                        # También guardar en IN_APP si el push fue exitoso
                        if push_result.get('success'):
                            Notification.objects.create(
                                user=user,
                                type=notification_type,
                                channel='PUSH',
                                title=title,
                                message=message,
                                data=data,
                                action_url=action_url,
                                action_text=action_text,
                                icon=icon
                            )
                    
                    elif channel == 'EMAIL':
                        email_result = NotificationService._send_email(
                            user, title, message, data, action_url, action_text
                        )
                        results['EMAIL'] = email_result
                        
                        # También guardar en IN_APP si el email fue exitoso
                        if email_result.get('success'):
                            Notification.objects.create(
                                user=user,
                                type=notification_type,
                                channel='EMAIL',
                                title=title,
                                message=message,
                                data=data,
                                action_url=action_url,
                                action_text=action_text,
                                icon=icon
                            )
                
                except Exception as e:
                    logger.error(f"❌ Error enviando notificación {channel} a {user.email}: {e}")
                    results[channel] = {'success': False, 'error': str(e)}
            
            return results
        
        except Exception as e:
            logger.error(f"❌ Error general en send_notification: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_push(user, title, message, data=None, action_url=None, icon=None):
        """
        Envía notificación push mediante Firebase Cloud Messaging.
        """
        try:
            # Obtener tokens activos del usuario
            tokens = DeviceToken.objects.filter(user=user, is_active=True)
            
            if not tokens.exists():
                logger.warning(f"⚠️ Usuario {user.email} no tiene tokens FCM registrados")
                return {'success': False, 'error': 'No FCM tokens found'}
            
            # Preparar datos para FCM
            fcm_data = data.copy() if data else {}
            if action_url:
                fcm_data['click_action'] = action_url
            
            results = []
            failed_tokens = []
            
            # Enviar a cada token
            for device_token in tokens:
                try:
                    message_obj = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=message,
                            image=icon
                        ),
                        data={k: str(v) for k, v in fcm_data.items()} if fcm_data else None,
                        token=device_token.token,
                        webpush=messaging.WebpushConfig(
                            notification=messaging.WebpushNotification(
                                title=title,
                                body=message,
                                icon=icon or '/static/icons/notification-icon.png',
                            ),
                            fcm_options=messaging.WebpushFCMOptions(
                                link=action_url
                            ) if action_url else None
                        )
                    )
                    
                    response = messaging.send(message_obj)
                    results.append({'token_id': device_token.id, 'success': True, 'response': response})
                    
                    # Actualizar last_used
                    device_token.last_used = timezone.now()
                    device_token.save(update_fields=['last_used'])
                    
                    logger.info(f"✅ Push enviado a {user.email} (token {device_token.id})")
                
                except messaging.UnregisteredError:
                    logger.warning(f"⚠️ Token {device_token.id} no registrado, marcando como inactivo")
                    device_token.is_active = False
                    device_token.save(update_fields=['is_active'])
                    failed_tokens.append(device_token.id)
                
                except Exception as e:
                    logger.error(f"❌ Error enviando push a token {device_token.id}: {e}")
                    results.append({'token_id': device_token.id, 'success': False, 'error': str(e)})
            
            success_count = sum(1 for r in results if r.get('success'))
            
            return {
                'success': success_count > 0,
                'sent': success_count,
                'failed': len(results) - success_count,
                'results': results,
                'failed_tokens': failed_tokens
            }
        
        except Exception as e:
            logger.error(f"❌ Error en _send_push: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_email(user, title, message, data=None, action_url=None, action_text=None):
        """
        Envía notificación por email.
        """
        try:
            # Renderizar template HTML
            html_content = render_to_string('emails/notification.html', {
                'user': user,
                'title': title,
                'message': message,
                'data': data,
                'action_url': action_url,
                'action_text': action_text or 'Ver Detalles',
                'site_name': 'SmartSales',
                'site_url': settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'https://smartsales.com'
            })
            
            # Versión texto plano
            text_content = strip_tags(html_content)
            
            # Enviar email
            send_mail(
                subject=f"[SmartSales] {title}",
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False
            )
            
            logger.info(f"✅ Email enviado a {user.email}: {title}")
            return {'success': True}
        
        except Exception as e:
            logger.error(f"❌ Error enviando email a {user.email}: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _check_preference(prefs, notification_type, channel):
        """
        Verifica si el usuario tiene habilitado un canal para un tipo de notificación.
        """
        return prefs.get_preference_for_type(notification_type, channel)
    
    # ===== MÉTODOS DE CONVENIENCIA PARA CADA TIPO DE NOTIFICACIÓN =====
    
    @staticmethod
    def notify_order_confirmed(order):
        """Notifica que un pedido fue confirmado."""
        return NotificationService.send_notification(
            user=order.user,
            notification_type='ORDER_CONFIRMED',
            title='¡Pedido Confirmado!',
            message=f'Tu pedido #{order.id} ha sido confirmado y está siendo procesado.',
            data={'order_id': order.id, 'order_number': str(order.id)},
            action_url=f'/orders/{order.id}',
            action_text='Ver Pedido',
            icon='✅'
        )
    
    @staticmethod
    def notify_order_shipped(order):
        """Notifica que un pedido fue enviado."""
        return NotificationService.send_notification(
            user=order.user,
            notification_type='ORDER_SHIPPED',
            title='¡Pedido Enviado!',
            message=f'Tu pedido #{order.id} está en camino.',
            data={'order_id': order.id, 'order_number': str(order.id)},
            action_url=f'/orders/{order.id}',
            action_text='Rastrear Pedido',
            icon='📦'
        )
    
    @staticmethod
    def notify_order_delivered(order):
        """Notifica que un pedido fue entregado."""
        return NotificationService.send_notification(
            user=order.user,
            notification_type='ORDER_DELIVERED',
            title='¡Pedido Entregado!',
            message=f'Tu pedido #{order.id} ha sido entregado. ¡Esperamos que lo disfrutes!',
            data={'order_id': order.id, 'order_number': str(order.id)},
            action_url=f'/orders/{order.id}',
            action_text='Ver Pedido',
            icon='🎉'
        )
    
    @staticmethod
    def notify_payment_success(order):
        """Notifica que un pago fue exitoso."""
        return NotificationService.send_notification(
            user=order.user,
            notification_type='PAYMENT_SUCCESS',
            title='Pago Exitoso',
            message=f'Tu pago de ${order.total} ha sido procesado correctamente.',
            data={
                'order_id': order.id,
                'amount': float(order.total),
                'currency': 'USD'
            },
            action_url=f'/orders/{order.id}',
            action_text='Ver Comprobante',
            icon='💳'
        )
    
    @staticmethod
    def notify_payment_failed(user, order_id, reason=None):
        """Notifica que un pago falló."""
        message = f'Tu pago para el pedido #{order_id} no pudo ser procesado.'
        if reason:
            message += f' Razón: {reason}'
        
        return NotificationService.send_notification(
            user=user,
            notification_type='PAYMENT_FAILED',
            title='Pago Fallido',
            message=message,
            data={'order_id': order_id, 'reason': reason},
            action_url=f'/orders/{order_id}',
            action_text='Reintentar Pago',
            icon='❌'
        )
    
    @staticmethod
    def notify_new_offer(user, product, discount_percentage):
        """Notifica sobre una nueva oferta de producto."""
        return NotificationService.send_notification(
            user=user,
            notification_type='NEW_OFFER',
            title='¡Nueva Oferta Disponible!',
            message=f'{product.name} está en oferta con {discount_percentage}% de descuento.',
            data={
                'product_id': product.id,
                'product_name': product.name,
                'discount': discount_percentage,
                'original_price': float(product.price),
                'discounted_price': float(product.price * (1 - discount_percentage / 100))
            },
            action_url=f'/products/{product.id}',
            action_text='Ver Oferta',
            icon='🎁'
        )
    
    @staticmethod
    def notify_offer_expiring(user, product, hours_left):
        """Notifica que una oferta está por vencer."""
        return NotificationService.send_notification(
            user=user,
            notification_type='OFFER_EXPIRING',
            title='¡Oferta por Vencer!',
            message=f'La oferta de {product.name} vence en {hours_left} horas. ¡No te la pierdas!',
            data={
                'product_id': product.id,
                'product_name': product.name,
                'hours_left': hours_left
            },
            action_url=f'/products/{product.id}',
            action_text='Comprar Ahora',
            icon='⏰'
        )
    
    @staticmethod
    def notify_stock_available(user, product):
        """Notifica que un producto volvió a estar disponible."""
        return NotificationService.send_notification(
            user=user,
            notification_type='STOCK_AVAILABLE',
            title='¡Producto Disponible!',
            message=f'{product.name} volvió a estar en stock.',
            data={
                'product_id': product.id,
                'product_name': product.name,
                'stock': product.stock
            },
            action_url=f'/products/{product.id}',
            action_text='Ver Producto',
            icon='✨'
        )
    
    @staticmethod
    def notify_system_alert(user, alert_title, alert_message, severity='INFO'):
        """Envía una alerta del sistema."""
        icons = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'SUCCESS': '✅'
        }
        
        return NotificationService.send_notification(
            user=user,
            notification_type='SYSTEM_ALERT',
            title=alert_title,
            message=alert_message,
            data={'severity': severity},
            icon=icons.get(severity, 'ℹ️')
        )


# Importar timezone después de la definición de la clase para evitar circular import
from django.utils import timezone
