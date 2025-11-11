"""
Serializers para la API de notificaciones
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Notification, NotificationPreference, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Notification"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_email', 'user_name', 'type', 'channel',
            'title', 'message', 'icon', 'data', 'action_url', 'action_text',
            'is_read', 'read_at', 'created_at', 'sent_at', 'time_ago'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'sent_at', 'read_at']
    
    def get_user_name(self, obj):
        """Obtiene el nombre completo del usuario o email si no tiene nombre"""
        if obj.user.first_name or obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.email
    
    def get_time_ago(self, obj):
        """Calcula el tiempo transcurrido desde la creación"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "Ahora"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"Hace {minutes} min"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"Hace {hours}h"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"Hace {days}d"
        else:
            return obj.created_at.strftime("%d/%m/%Y")


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de notificaciones"""
    
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message', 'icon',
            'is_read', 'created_at', 'time_ago'
        ]
    
    def get_time_ago(self, obj):
        """Calcula el tiempo transcurrido desde la creación"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "Ahora"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"Hace {minutes} min"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"Hace {hours}h"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"Hace {days}d"
        else:
            return obj.created_at.strftime("%d/%m/%Y")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer para el modelo NotificationPreference"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_email',
            # Preferencias de pedidos
            'orders_in_app', 'orders_push', 'orders_email',
            # Preferencias de ofertas
            'offers_in_app', 'offers_push', 'offers_email',
            # Preferencias del sistema
            'system_in_app', 'system_push', 'system_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validación personalizada para asegurar que al menos un canal esté activo
        para notificaciones críticas.
        """
        # Verificar que al menos un canal esté activo para pedidos (crítico)
        orders_channels = [
            data.get('orders_in_app', True),
            data.get('orders_push', True),
            data.get('orders_email', True)
        ]
        
        if not any(orders_channels):
            raise serializers.ValidationError(
                "Debes mantener al menos un canal activo para notificaciones de pedidos."
            )
        
        return data


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DeviceToken"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'user', 'user_email', 'token', 'device_type',
            'device_name', 'is_active', 'created_at', 'last_used'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'last_used']
        extra_kwargs = {
            'token': {'write_only': True}  # No exponer tokens en respuestas
        }
    
    def validate_token(self, value):
        """Valida que el token no esté vacío y tenga longitud adecuada"""
        if not value or len(value) < 10:
            raise serializers.ValidationError("Token inválido o demasiado corto")
        return value
    
    def create(self, validated_data):
        """
        Crea o actualiza un token existente.
        Si el token ya existe para este usuario, lo reactiva.
        """
        token = validated_data.get('token')
        user = validated_data.get('user')
        
        # Buscar si ya existe este token
        existing_token = DeviceToken.objects.filter(token=token).first()
        
        if existing_token:
            # Si existe pero es de otro usuario, marcar como inactivo
            if existing_token.user != user:
                existing_token.is_active = False
                existing_token.save()
                # Crear nuevo token para el usuario actual
                return super().create(validated_data)
            else:
                # Si es del mismo usuario, solo actualizarlo
                existing_token.device_type = validated_data.get('device_type', existing_token.device_type)
                existing_token.device_name = validated_data.get('device_name', existing_token.device_name)
                existing_token.is_active = True
                existing_token.save()
                return existing_token
        
        return super().create(validated_data)


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de notificaciones"""
    
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    read = serializers.IntegerField()
    by_type = serializers.DictField()
    by_channel = serializers.DictField()
    recent_count = serializers.IntegerField()
