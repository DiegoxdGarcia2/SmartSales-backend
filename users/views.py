from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, UserSerializer


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
