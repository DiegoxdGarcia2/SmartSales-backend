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
    PATCH: Actualizar preferencias
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
