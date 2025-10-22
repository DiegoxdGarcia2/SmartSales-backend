from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer, ClientProfileSerializer, MyTokenObtainPairSerializer, RoleSerializer
from .models import ClientProfile, Role

User = get_user_model()


class MyTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para obtener tokens JWT.
    Permite autenticación con username o email.
    """
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    Vista para el registro de nuevos usuarios.
    Permite que cualquier usuario (sin autenticación) se registre.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Serializar el usuario creado para la respuesta
        user_serializer = UserSerializer(user)
        
        return Response(
            {
                'message': 'Usuario registrado exitosamente',
                'user': user_serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class ClientProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los perfiles de clientes.
    - Los clientes solo pueden ver y actualizar su propio perfil.
    - Los administradores pueden ver y gestionar todos los perfiles.
    """
    queryset = ClientProfile.objects.all()
    serializer_class = ClientProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Los clientes solo ven su propio perfil.
        Los administradores ven todos.
        """
        user = self.request.user
        if user.is_staff:
            return ClientProfile.objects.all()
        return ClientProfile.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """
        Al crear un perfil, asigna automáticamente el usuario actual.
        """
        serializer.save(user=self.request.user)


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar roles del sistema.
    Solo administradores pueden crear, actualizar o eliminar roles.
    Usuarios autenticados pueden ver los roles disponibles.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    
    def get_permissions(self):
        """
        Solo admins pueden crear, actualizar o eliminar roles.
        Usuarios autenticados pueden listarlos.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios del sistema.
    - GET: Listar usuarios (solo admin ve todos, usuarios normales solo se ven a sí mismos)
    - POST: Crear usuario (solo admin)
    - PUT/PATCH: Actualizar usuario (admin puede actualizar cualquiera, usuario solo a sí mismo)
    - DELETE: Eliminar usuario (solo admin)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Admins ven todos los usuarios.
        Usuarios normales solo se ven a sí mismos.
        """
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    def get_permissions(self):
        """
        Solo admins pueden crear o eliminar usuarios.
        """
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def update(self, request, *args, **kwargs):
        """
        Usuarios solo pueden actualizar su propio perfil.
        Admins pueden actualizar cualquier usuario.
        """
        user = self.get_object()
        if not request.user.is_staff and user.id != request.user.id:
            return Response(
                {'detail': 'No tienes permiso para actualizar este usuario.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Usuarios solo pueden actualizar su propio perfil.
        Admins pueden actualizar cualquier usuario.
        """
        user = self.get_object()
        if not request.user.is_staff and user.id != request.user.id:
            return Response(
                {'detail': 'No tienes permiso para actualizar este usuario.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
