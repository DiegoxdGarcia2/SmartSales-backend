from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, authenticate
from .models import ClientProfile, Role

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Role.
    """
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para obtener tokens JWT.
    Permite autenticación con username o email.
    """
    
    @classmethod
    def get_token(cls, user):
        """
        Añade claims personalizados al token JWT.
        Incluye información del rol del usuario.
        """
        token = super().get_token(user)

        # Añadir claims personalizados
        token['username'] = user.username
        token['email'] = user.email
        if user.role:  # Asegurarse de que el usuario tenga un rol asignado
            token['role_id'] = user.role.id
            token['role_name'] = user.role.name
        else:
            token['role_id'] = None
            token['role_name'] = None

        return token
    
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
            'role': user.role.name if user.role else None,
        }
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo User.
    Muestra información básica del usuario.
    """
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_id']
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
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'role_id']
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
        
        # Si no se proporciona rol, asignar CLIENTE por defecto
        if 'role' not in validated_data or validated_data['role'] is None:
            try:
                default_role = Role.objects.get(name='CLIENTE')
                validated_data['role'] = default_role
            except Role.DoesNotExist:
                pass  # Si no existe el rol CLIENTE, quedará como None
        
        # Crear usuario con contraseña hasheada
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role')
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
