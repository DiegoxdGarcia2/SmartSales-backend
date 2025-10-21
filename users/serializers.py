from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, authenticate
from .models import ClientProfile

User = get_user_model()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para obtener tokens JWT.
    Permite autenticación con username o email.
    """
    
    def validate(self, attrs):
        """
        Valida las credenciales permitiendo login con username o email.
        """
        # Obtener las credenciales
        username_or_email = attrs.get('username')
        password = attrs.get('password')
        
        # Primer intento: autenticar con username
        user = authenticate(
            request=self.context.get('request'),
            username=username_or_email,
            password=password
        )
        
        # Segundo intento: si falla, intentar con email
        if user is None:
            try:
                # Buscar usuario por email
                user_obj = User.objects.get(email=username_or_email)
                # Intentar autenticar con el username del usuario encontrado
                user = authenticate(
                    request=self.context.get('request'),
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                user = None
        
        # Si ambos intentos fallaron, lanzar error
        if user is None:
            raise AuthenticationFailed(
                'No se encontró ninguna cuenta activa con las credenciales proporcionadas.'
            )
        
        # Si el usuario está inactivo
        if not user.is_active:
            raise AuthenticationFailed('Esta cuenta está desactivada.')
        
        # Actualizar attrs con el username correcto para que el padre lo procese
        attrs['username'] = user.username
        
        # Llamar al método validate del padre para generar los tokens
        data = super().validate(attrs)
        
        # Añadir información adicional al response (opcional)
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
        }
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo User.
    Muestra información básica del usuario.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']
        read_only_fields = ['id']


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro de nuevos usuarios.
    Valida que las contraseñas coincidan y hace hash de la contraseña.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Confirmar contraseña'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'role']
        extra_kwargs = {
            'email': {'required': True}
        }
    
    def validate(self, attrs):
        """
        Valida que las contraseñas coincidan.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password': 'Las contraseñas no coinciden.'
            })
        return attrs
    
    def create(self, validated_data):
        """
        Crea un nuevo usuario con la contraseña hasheada.
        """
        # Eliminar password2 ya que no es parte del modelo
        validated_data.pop('password2')
        
        # Crear usuario con contraseña hasheada
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'CLIENTE')
        )
        
        return user


class ClientProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el perfil de cliente.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = [
            'id',
            'user',
            'username',
            'email',
            'full_name',
            'phone_number',
            'address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'username', 'email', 'created_at', 'updated_at']
    
    def validate_phone_number(self, value):
        """
        Valida el formato del número de teléfono.
        """
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("El número de teléfono debe contener solo números.")
        return value
