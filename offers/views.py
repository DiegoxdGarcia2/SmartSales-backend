"""
Vistas para el sistema de ofertas de SmartSales.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

User = get_user_model()

from .models import Offer, OfferProduct, UserOfferInteraction, OfferRecommendation
from .serializers import (
    OfferSerializer,
    OfferListSerializer,
    OfferProductSerializer,
    UserOfferInteractionSerializer,
    OfferRecommendationSerializer,
    OfferStatsSerializer,
    OfferApplicationSerializer,
    CreateOfferSerializer
)
from .services import OfferService
from .ml_models import OfferRecommendationEngine, DiscountOptimizer
from products.models import Product

logger = logging.getLogger(__name__)


class OfferViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de ofertas"""
    permission_classes = [AllowAny]  # Permitir acceso público a ofertas activas
    
    def get_queryset(self):
        """Filtra ofertas según el usuario"""
        user = self.request.user
        
        # Administradores ven todas las ofertas
        if user.is_authenticated and user.is_staff:
            return Offer.objects.all()
        
        # Usuarios anónimos o normales: solo ofertas activas y públicas
        now = timezone.now()
        queryset = Offer.objects.filter(
            status='ACTIVE',
            start_date__lte=now,
            end_date__gte=now
        )
        
        # Si está autenticado, incluir ofertas personalizadas
        if user.is_authenticated:
            queryset = queryset.filter(
                Q(target_user__isnull=True) | Q(target_user=user)
            )
        else:
            # Solo ofertas públicas (sin target_user específico)
            queryset = queryset.filter(target_user__isnull=True)
        
        return queryset.distinct()
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'list':
            return OfferListSerializer
        elif self.action == 'create':
            return CreateOfferSerializer
        return OfferSerializer
    
    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'activate', 'deactivate']:
            return [IsAdminUser()]
        elif self.action in ['list', 'retrieve', 'active', 'featured']:
            return [AllowAny()]  # Ofertas activas son públicas
        return [IsAuthenticated()]
    
    def list(self, request):
        """Lista ofertas con filtros opcionales"""
        queryset = self.get_queryset()
        
        # Filtros opcionales
        offer_type = request.query_params.get('type')
        if offer_type:
            queryset = queryset.filter(offer_type=offer_type)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Solo ofertas activas
        active_only = request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            now = timezone.now()
            queryset = queryset.filter(
                status='ACTIVE',
                start_date__lte=now,
                end_date__gte=now
            )
        
        # Ordenar por prioridad
        queryset = queryset.order_by('-priority', '-created_at')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Crea una nueva oferta"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        offer = serializer.save(created_by=request.user)
        
        # Retornar oferta completa
        detail_serializer = OfferSerializer(offer)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        """Activa una oferta y notifica usuarios"""
        try:
            notify = request.data.get('notify_users', True)
            offer = OfferService.activate_offer(pk, notify_users=notify)
            serializer = self.get_serializer(offer)
            return Response({
                'message': 'Oferta activada exitosamente',
                'offer': serializer.data
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error al activar oferta: {str(e)}")
            return Response(
                {'error': 'Error al activar oferta'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def deactivate(self, request, pk=None):
        """Desactiva una oferta"""
        try:
            offer = self.get_object()
            offer.status = 'PAUSED'
            offer.save(update_fields=['status', 'updated_at'])
            
            serializer = self.get_serializer(offer)
            return Response({
                'message': 'Oferta desactivada exitosamente',
                'offer': serializer.data
            })
        except Exception as e:
            logger.error(f"Error al desactivar oferta: {str(e)}")
            return Response(
                {'error': 'Error al desactivar oferta'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def track_view(self, request, pk=None):
        """Registra que un usuario vio la oferta"""
        try:
            offer = self.get_object()
            
            # Obtener metadata de la request
            session_id = request.session.session_key
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Registrar interacción
            OfferService.track_interaction(
                user=request.user,
                offer=offer,
                action='VIEWED',
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return Response({'message': 'Vista registrada'})
        except Exception as e:
            logger.error(f"Error al registrar vista: {str(e)}")
            return Response(
                {'error': 'Error al registrar vista'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def track_click(self, request, pk=None):
        """Registra que un usuario clickeó la oferta"""
        try:
            offer = self.get_object()
            product_id = request.data.get('product_id')
            
            # Obtener metadata
            session_id = request.session.session_key
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Obtener producto si se especificó
            from products.models import Product
            product = None
            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    pass
            
            # Registrar interacción
            OfferService.track_interaction(
                user=request.user,
                offer=offer,
                action='CLICKED',
                product=product,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return Response({'message': 'Click registrado'})
        except Exception as e:
            logger.error(f"Error al registrar click: {str(e)}")
            return Response(
                {'error': 'Error al registrar click'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def apply_to_cart(self, request):
        """Aplica una oferta al carrito del usuario"""
        serializer = OfferApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            offer = Offer.objects.get(id=serializer.validated_data['offer_id'])
            cart_items = [
                {'product_id': pid, 'quantity': 1}
                for pid in serializer.validated_data['product_ids']
            ]
            
            result = OfferService.apply_offer_to_cart(
                user=request.user,
                offer=offer,
                cart_items=cart_items
            )
            
            return Response(result)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error al aplicar oferta: {str(e)}")
            return Response(
                {'error': 'Error al aplicar oferta'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def stats(self, request):
        """Obtiene estadísticas de ofertas"""
        try:
            stats_data = OfferService.get_offer_stats()
            serializer = OfferStatsSerializer(stats_data)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return Response(
                {'error': 'Error al obtener estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def my_offers(self, request):
        """Obtiene ofertas activas para el usuario actual"""
        try:
            offers = OfferService.get_active_offers_for_user(request.user)
            serializer = OfferListSerializer(offers, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error al obtener ofertas del usuario: {str(e)}")
            return Response(
                {'error': 'Error al obtener ofertas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def personalized(self, request):
        """Obtiene ofertas personalizadas basadas en ML para el usuario actual"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Autenticación requerida'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Obtener recomendaciones ML del usuario
            from .models import OfferRecommendation
            recommendations = OfferRecommendation.objects.filter(
                user=request.user
            ).select_related('offer').order_by('-score')[:10]
            
            # Filtrar ofertas activas
            now = timezone.now()
            active_offers = []
            for rec in recommendations:
                offer = rec.offer
                if (offer.status == 'ACTIVE' and 
                    offer.start_date <= now <= offer.end_date):
                    active_offers.append(offer)
            
            serializer = OfferListSerializer(active_offers, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error al obtener ofertas personalizadas: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'Error al obtener ofertas personalizadas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Obtiene solo ofertas activas (públicas)"""
        try:
            now = timezone.now()
            offers = Offer.objects.filter(
                status='ACTIVE',
                start_date__lte=now,
                end_date__gte=now,
                target_user__isnull=True  # Solo ofertas públicas
            ).order_by('-priority', '-created_at')
            
            serializer = OfferListSerializer(offers, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error al obtener ofertas activas: {str(e)}")
            return Response(
                {'error': 'Error al obtener ofertas activas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Obtiene ofertas destacadas (alta prioridad)"""
        try:
            now = timezone.now()
            offers = Offer.objects.filter(
                status='ACTIVE',
                start_date__lte=now,
                end_date__gte=now,
                target_user__isnull=True,
                priority__gte=5  # Solo ofertas con prioridad >= 5
            ).order_by('-priority', '-created_at')[:6]
            
            serializer = OfferListSerializer(offers, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error al obtener ofertas destacadas: {str(e)}")
            return Response(
                {'error': 'Error al obtener ofertas destacadas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def populate_sample_offers(self, request):
        """Crea ofertas de prueba en la base de datos"""
        try:
            from datetime import timedelta
            from decimal import Decimal
            from products.models import Product
            
            # Limpiar ofertas existentes si se solicita
            if request.data.get('reset', False):
                count = Offer.objects.count()
                Offer.objects.all().delete()
                logger.info(f"Eliminadas {count} ofertas existentes")
            
            # Verificar si ya hay ofertas
            if Offer.objects.count() > 0:
                return Response({
                    'error': 'Ya existen ofertas. Usa "reset": true para eliminarlas.',
                    'existing_count': Offer.objects.count()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener productos
            products = list(Product.objects.all()[:10])
            if not products:
                return Response({
                    'error': 'No hay productos en la base de datos'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            now = timezone.now()
            offers_created = []
            
            # Crear ofertas
            offers_data = [
                {
                    'name': "🔥 Venta Flash - 50% OFF",
                    'description': "¡Aprovecha nuestra venta flash! 50% de descuento.",
                    'offer_type': "FLASH_SALE",
                    'discount_percentage': Decimal('50.00'),
                    'start_date': now - timedelta(days=1),
                    'end_date': now + timedelta(days=2),
                    'priority': 10,
                    'min_purchase_amount': Decimal('50.00'),
                    'max_uses': 100,
                    'products': products[:3]
                },
                {
                    'name': "⭐ Oferta del Día - 30% OFF",
                    'description': "Oferta especial del día en productos premium.",
                    'offer_type': "DAILY_DEAL",
                    'discount_percentage': Decimal('30.00'),
                    'start_date': now - timedelta(hours=2),
                    'end_date': now + timedelta(hours=22),
                    'priority': 8,
                    'min_purchase_amount': Decimal('30.00'),
                    'max_uses': 50,
                    'products': products[3:6]
                },
                {
                    'name': "🎄 Oferta de Temporada - 25% OFF",
                    'description': "Celebra esta temporada especial.",
                    'offer_type': "SEASONAL",
                    'discount_percentage': Decimal('25.00'),
                    'start_date': now - timedelta(days=5),
                    'end_date': now + timedelta(days=25),
                    'priority': 6,
                    'min_purchase_amount': Decimal('40.00'),
                    'max_uses': 200,
                    'products': products[::2][:5]
                },
                {
                    'name': "🏷️ Liquidación - 40% OFF",
                    'description': "Últimas unidades en liquidación.",
                    'offer_type': "CLEARANCE",
                    'discount_percentage': Decimal('40.00'),
                    'start_date': now - timedelta(days=10),
                    'end_date': now + timedelta(days=5),
                    'priority': 5,
                    'min_purchase_amount': Decimal('20.00'),
                    'max_uses': 150,
                    'products': products[6:9] if len(products) > 6 else products[:3]
                },
                {
                    'name': "💼 Descuento Especial - 15% OFF",
                    'description': "Descuento especial para nuevos clientes.",
                    'offer_type': "DAILY_DEAL",
                    'discount_percentage': Decimal('15.00'),
                    'start_date': now,
                    'end_date': now + timedelta(days=30),
                    'priority': 3,
                    'min_purchase_amount': Decimal('10.00'),
                    'max_uses': 1000,
                    'products': products[1:4]
                }
            ]
            
            for offer_data in offers_data:
                products_to_add = offer_data.pop('products')
                offer = Offer.objects.create(
                    status='ACTIVE',
                    **offer_data
                )
                # Crear relaciones OfferProduct
                from offers.models import OfferProduct
                for product in products_to_add:
                    OfferProduct.objects.create(offer=offer, product=product)
                offers_created.append(offer.name)
            
            return Response({
                'message': 'Ofertas de prueba creadas exitosamente',
                'total_created': len(offers_created),
                'offers': offers_created,
                'active_offers': Offer.objects.filter(status='ACTIVE').count(),
                'featured_offers': Offer.objects.filter(status='ACTIVE', priority__gte=5).count()
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creando ofertas de prueba: {str(e)}")
            return Response({
                'error': f'Error creando ofertas: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def generate_ml_recommendations(self, request):
        """Genera recomendaciones ML para todos los usuarios o uno específico"""
        try:
            user_id = request.data.get('user_id')
            max_recommendations = int(request.data.get('max_recommendations', 10))
            
            engine = OfferRecommendationEngine()
            
            if user_id:
                # Generar para un usuario específico
                user = User.objects.get(id=user_id)
                recommendations = engine.generate_recommendations_for_user(
                    user,
                    max_recommendations=max_recommendations
                )
                return Response({
                    'message': f'Generadas {len(recommendations)} recomendaciones para {user.username}',
                    'user': user.username,
                    'recommendations_count': len(recommendations)
                })
            else:
                # Generar para todos los usuarios activos
                users = User.objects.filter(is_active=True)
                total_recommendations = 0
                
                for user in users:
                    recommendations = engine.generate_recommendations_for_user(
                        user,
                        max_recommendations=max_recommendations
                    )
                    total_recommendations += len(recommendations)
                
                return Response({
                    'message': f'Recomendaciones generadas para {users.count()} usuarios',
                    'users_processed': users.count(),
                    'total_recommendations': total_recommendations
                })
                
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generando recomendaciones ML: {str(e)}")
            return Response(
                {'error': 'Error al generar recomendaciones'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def optimize_discount(self, request):
        """Sugiere el descuento óptimo para un producto"""
        try:
            product_id = request.data.get('product_id')
            target_increase = float(request.data.get('target_sales_increase', 1.5))
            
            if not product_id:
                return Response(
                    {'error': 'product_id es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            product = Product.objects.get(id=product_id)
            optimizer = DiscountOptimizer()
            
            suggestion = optimizer.suggest_optimal_discount(
                product,
                target_sales_increase=target_increase
            )
            
            return Response(suggestion)
            
        except Product.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error optimizando descuento: {str(e)}")
            return Response(
                {'error': 'Error al optimizar descuento'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OfferProductViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de productos en ofertas"""
    serializer_class = OfferProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra productos de ofertas"""
        offer_id = self.request.query_params.get('offer_id')
        if offer_id:
            return OfferProduct.objects.filter(offer_id=offer_id)
        return OfferProduct.objects.all()
    
    def get_permissions(self):
        """Solo admins pueden crear/modificar"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]


class UserOfferInteractionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver interacciones de usuarios con ofertas"""
    serializer_class = UserOfferInteractionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra interacciones según el usuario"""
        user = self.request.user
        
        # Admins ven todas las interacciones
        if user.is_staff:
            queryset = UserOfferInteraction.objects.all()
            
            # Filtros opcionales
            offer_id = self.request.query_params.get('offer_id')
            if offer_id:
                queryset = queryset.filter(offer_id=offer_id)
            
            action = self.request.query_params.get('action')
            if action:
                queryset = queryset.filter(action=action)
            
            return queryset.order_by('-created_at')
        
        # Usuarios normales solo ven sus propias interacciones
        return UserOfferInteraction.objects.filter(user=user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def my_history(self, request):
        """Obtiene el historial de interacciones del usuario"""
        interactions = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(interactions, many=True)
        return Response(serializer.data)


class OfferRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para recomendaciones de ofertas"""
    serializer_class = OfferRecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Obtiene recomendaciones para el usuario actual"""
        user = self.request.user
        
        # Admins ven todas
        if user.is_staff:
            return OfferRecommendation.objects.all().order_by('-score', '-created_at')
        
        # Usuarios normales solo ven sus recomendaciones
        return OfferRecommendation.objects.filter(user=user).order_by('-score', '-created_at')
    
    @action(detail=False, methods=['get'])
    def top_recommendations(self, request):
        """Obtiene las mejores recomendaciones para el usuario"""
        limit = int(request.query_params.get('limit', 5))
        
        recommendations = OfferRecommendation.objects.filter(
            user=request.user,
            offer__status='ACTIVE'
        ).order_by('-score')[:limit]
        
        # Marcar como mostradas
        for rec in recommendations:
            if not rec.was_shown:
                rec.mark_shown()
        
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_clicked(self, request, pk=None):
        """Marca una recomendación como clickeada"""
        try:
            recommendation = self.get_object()
            recommendation.mark_clicked()
            return Response({'message': 'Click registrado'})
        except Exception as e:
            logger.error(f"Error al marcar click: {str(e)}")
            return Response(
                {'error': 'Error al registrar click'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def mark_converted(self, request, pk=None):
        """Marca una recomendación como convertida"""
        try:
            recommendation = self.get_object()
            recommendation.mark_converted()
            return Response({'message': 'Conversión registrada'})
        except Exception as e:
            logger.error(f"Error al marcar conversión: {str(e)}")
            return Response(
                {'error': 'Error al registrar conversión'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OfferCategoriesView(APIView):
    """
    Vista para obtener las categorías/tipos de ofertas disponibles.
    Retorna los tipos de ofertas definidos en el modelo como "categorías".
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Obtiene lista de categorías de ofertas"""
        try:
            from .models import Offer
            
            categories = [
                {
                    'id': idx + 1,
                    'name': display_name,
                    'slug': value.lower().replace('_', '-'),
                    'value': value
                }
                for idx, (value, display_name) in enumerate(Offer.OFFER_TYPES)
            ]
            
            return Response(categories)
        except Exception as e:
            logger.error(f"Error al obtener categorías: {str(e)}")
            return Response(
                {'error': 'Error al obtener categorías'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
