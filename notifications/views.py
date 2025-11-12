"""
Vistas y endpoints para la API de notificaciones
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import Notification, NotificationPreference, DeviceToken
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationPreferenceSerializer,
    DeviceTokenSerializer,
    NotificationStatsSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar notificaciones del usuario.
    
    list: Obtener todas las notificaciones del usuario
    retrieve: Obtener una notificación específica
    unread_count: Obtener el conteo de notificaciones no leídas
    mark_as_read: Marcar una notificación como leída
    mark_all_as_read: Marcar todas las notificaciones como leídas
    delete_read: Eliminar todas las notificaciones leídas
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        """Retorna solo las notificaciones del usuario autenticado"""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_serializer_class(self):
        """Usa serializer simplificado para listado"""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Lista las notificaciones con paginación y filtros opcionales.
        
        Query params:
        - unread: true/false - Filtrar solo no leídas
        - type: ORDER_CONFIRMED,NEW_OFFER,etc - Filtrar por tipo
        - limit: número - Limitar cantidad de resultados
        """
        queryset = self.get_queryset()
        
        # Filtrar por leídas/no leídas
        unread_filter = request.query_params.get('unread', None)
        if unread_filter is not None:
            is_unread = unread_filter.lower() == 'true'
            queryset = queryset.filter(is_read=not is_unread)
        
        # Filtrar por tipo
        notification_type = request.query_params.get('type', None)
        if notification_type:
            queryset = queryset.filter(type=notification_type)
        
        # Obtener el count ANTES de limitar
        total_count = queryset.count()
        
        # Limitar resultados
        limit = request.query_params.get('limit', None)
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': total_count,
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Obtiene el conteo de notificaciones no leídas"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marca una notificación específica como leída"""
        notification = self.get_object()
        notification.mark_as_read()
        
        serializer = self.get_serializer(notification)
        return Response({
            'message': 'Notificación marcada como leída',
            'notification': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Marca todas las notificaciones del usuario como leídas"""
        updated_count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{updated_count} notificaciones marcadas como leídas',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['delete'])
    def delete_read(self, request):
        """Elimina todas las notificaciones leídas del usuario"""
        deleted_count, _ = self.get_queryset().filter(is_read=True).delete()
        
        return Response({
            'message': f'{deleted_count} notificaciones eliminadas',
            'deleted_count': deleted_count
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtiene estadísticas de las notificaciones del usuario"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        unread = queryset.filter(is_read=False).count()
        read = queryset.filter(is_read=True).count()
        
        # Conteo por tipo
        by_type = dict(
            queryset.values('type').annotate(count=Count('type')).values_list('type', 'count')
        )
        
        # Conteo por canal
        by_channel = dict(
            queryset.values('channel').annotate(count=Count('channel')).values_list('channel', 'count')
        )
        
        # Notificaciones recientes (últimas 24 horas)
        recent_count = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        stats_data = {
            'total': total,
            'unread': unread,
            'read': read,
            'by_type': by_type,
            'by_channel': by_channel,
            'recent_count': recent_count
        }
        
        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)


class NotificationPreferenceView(APIView):
    """
    Vista para gestionar las preferencias de notificación del usuario.
    
    GET: Obtener preferencias actuales
    PUT: Actualizar preferencias (completo o parcial)
    PATCH: Actualizar preferencias (parcial)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtiene las preferencias de notificación del usuario"""
        prefs, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs)
        
        return Response({
            'preferences': serializer.data,
            'is_new': created
        })
    
    def patch(self, request):
        """Actualiza las preferencias de notificación del usuario"""
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Preferencias actualizadas correctamente',
                'preferences': serializer.data
            })
        
        return Response({
            'message': 'Error al actualizar preferencias',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        """Actualiza las preferencias de notificación del usuario (completo o parcial)"""
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Preferencias actualizadas correctamente',
                'preferences': serializer.data
            })
        
        return Response({
            'message': 'Error al actualizar preferencias',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tokens de dispositivos (FCM).
    
    list: Obtener todos los tokens del usuario
    create: Registrar un nuevo token
    destroy: Eliminar un token
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenSerializer
    
    def get_queryset(self):
        """Retorna solo los tokens del usuario autenticado"""
        return DeviceToken.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Asigna automáticamente el usuario al crear un token"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Desactiva un token específico sin eliminarlo"""
        token = self.get_object()
        token.is_active = False
        token.save(update_fields=['is_active'])
        
        return Response({
            'message': 'Token desactivado correctamente',
            'token_id': token.id
        })
    
    @action(detail=False, methods=['post'])
    def deactivate_all(self, request):
        """Desactiva todos los tokens del usuario"""
        updated_count = self.get_queryset().filter(is_active=True).update(is_active=False)
        
        return Response({
            'message': f'{updated_count} tokens desactivados',
            'updated_count': updated_count
        })


class TestNotificationView(APIView):
    """
    Vista para enviar notificaciones de prueba (solo para testing).
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Envía una notificación de prueba al usuario.
        
        Body params:
        - title: Título de la notificación
        - message: Mensaje
        - channels: Lista de canales (opcional, por defecto ['IN_APP'])
        """
        from .services import NotificationService
        
        title = request.data.get('title', '🧪 Notificación de Prueba')
        message = request.data.get('message', 'Esta es una notificación de prueba del sistema.')
        channels = request.data.get('channels', ['IN_APP'])
        
        result = NotificationService.send_notification(
            user=request.user,
            notification_type='SYSTEM_ALERT',
            title=title,
            message=message,
            channels=channels,
            icon='🧪'
        )
        
        return Response({
            'message': 'Notificación de prueba enviada',
            'results': result
        })


class DebugNotificationView(APIView):
    """
    Vista para debuggear problemas con notificaciones.
    Solo accesible para administradores.
    """
    
    permission_classes = [IsAuthenticated]  # Cambiar a IsAdminUser en producción
    
    def get(self, request):
        """Obtiene información de debug sobre las notificaciones del usuario"""
        from .models import NotificationPreference, DeviceToken
        
        user = request.user
        
        # Preferencias
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        prefs_data = {
            'orders_in_app': prefs.orders_in_app,
            'orders_push': prefs.orders_push,
            'orders_email': prefs.orders_email,
            'offers_in_app': prefs.offers_in_app,
            'offers_push': prefs.offers_push,
            'offers_email': prefs.offers_email,
            'system_in_app': prefs.system_in_app,
            'system_push': prefs.system_push,
            'system_email': prefs.system_email,
        }
        
        # Tokens FCM
        tokens = DeviceToken.objects.filter(user=user, is_active=True)
        tokens_data = []
        for token in tokens:
            tokens_data.append({
                'id': token.id,
                'device_type': token.device_type,
                'device_name': token.device_name,
                'last_used': token.last_used,
                'created_at': token.created_at,
            })
        
        # Notificaciones recientes
        recent_notifications = Notification.objects.filter(
            user=user
        ).order_by('-created_at')[:10]
        
        notifications_data = []
        for notif in recent_notifications:
            notifications_data.append({
                'id': notif.id,
                'type': notif.type,
                'channel': notif.channel,
                'title': notif.title,
                'message': notif.message[:100] + '...' if len(notif.message) > 100 else notif.message,
                'is_read': notif.is_read,
                'created_at': notif.created_at,
                'sent_at': notif.sent_at,
            })
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'preferences': prefs_data,
            'fcm_tokens': {
                'count': tokens.count(),
                'tokens': tokens_data,
            },
            'recent_notifications': {
                'count': recent_notifications.count(),
                'notifications': notifications_data,
            }
        })
    
    def post(self, request):
        """
        Envía notificaciones de prueba específicas (pago u oferta).
        
        Body params:
        - type: 'payment' o 'offer'
        - order_id: ID de la orden (para pago)
        - product_id: ID del producto (para oferta)
        """
        from .services import NotificationService
        from orders.models import Order
        from products.models import Product
        
        notif_type = request.data.get('type')
        
        if notif_type == 'payment':
            order_id = request.data.get('order_id')
            if not order_id:
                return Response(
                    {'error': 'order_id es requerido para notificación de pago'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                order = Order.objects.get(id=order_id, user=request.user)
                result = NotificationService.notify_payment_success(order)
                return Response({
                    'message': 'Notificación de pago enviada',
                    'order_id': order_id,
                    'result': result
                })
            except Order.DoesNotExist:
                return Response(
                    {'error': 'Orden no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif notif_type == 'offer':
            product_id = request.data.get('product_id')
            if not product_id:
                return Response(
                    {'error': 'product_id es requerido para notificación de oferta'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                product = Product.objects.get(id=product_id)
                result = NotificationService.notify_new_offer(
                    user=request.user,
                    product=product,
                    discount_percentage=25  # 25% de descuento de prueba
                )
                return Response({
                    'message': 'Notificación de oferta enviada',
                    'product_id': product_id,
                    'result': result
                })
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Producto no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        else:
            return Response(
                {'error': 'Tipo de notificación inválido. Use "payment" o "offer"'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def post(self, request):
        """
        Ejecuta tareas de mantenimiento de notificaciones
        - check_expiring_offers: Verifica ofertas por expirar
        """
        action = request.data.get('action')
        
        if action == 'check_expiring_offers':
            try:
                from offers.services import OfferService
                expiring_offers = OfferService.check_expiring_offers()
                
                return Response({
                    'message': f'Verificación completada. {len(expiring_offers)} ofertas notificadas.',
                    'expiring_offers_count': len(expiring_offers),
                    'expiring_offers': [{'id': o.id, 'name': o.name, 'end_date': o.end_date} for o in expiring_offers]
                })
                
            except Exception as e:
                return Response(
                    {'error': f'Error ejecutando check_expiring_offers: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        elif action == 'test_all_notifications':
            # Probar todas las notificaciones disponibles
            results = {}
            
            try:
                # Notificación de pago (usando una orden existente si hay)
                from orders.models import Order
                order = Order.objects.filter(user=request.user).first()
                if order:
                    results['payment_success'] = NotificationService.notify_payment_success(order)
                else:
                    results['payment_success'] = {'error': 'No hay órdenes para el usuario'}
                
                # Notificación de oferta (usando un producto existente)
                from products.models import Product
                product = Product.objects.first()
                if product:
                    results['new_offer'] = NotificationService.notify_new_offer(
                        user=request.user,
                        product=product,
                        discount_percentage=25
                    )
                else:
                    results['new_offer'] = {'error': 'No hay productos disponibles'}
                
                # Notificación del sistema
                results['system_alert'] = NotificationService.send_notification(
                    user=request.user,
                    notification_type='SYSTEM_ALERT',
                    title='Prueba de Notificación del Sistema',
                    message='Esta es una notificación de prueba del sistema.',
                    icon='🧪'
                )
                
                return Response({
                    'message': 'Todas las notificaciones de prueba enviadas',
                    'results': results
                })
                
            except Exception as e:
                return Response(
                    {'error': f'Error probando notificaciones: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        else:
            return Response(
                {'error': 'Acción inválida. Use "check_expiring_offers" o "test_all_notifications"'},
                status=status.HTTP_400_BAD_REQUEST
            )
