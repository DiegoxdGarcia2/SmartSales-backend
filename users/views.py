from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, UserSerializer, ClientProfileSerializer, MyTokenObtainPairSerializer
from .models import ClientProfile


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
