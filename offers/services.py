"""
Servicio centralizado para el manejo de ofertas en SmartSales.
Maneja la lógica de negocio de ofertas, aplicación de descuentos y tracking.
"""
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import logging

from .models import Offer, OfferProduct, UserOfferInteraction, OfferRecommendation
from products.models import Product
from notifications.services import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


class OfferService:
    """Servicio para gestión de ofertas"""
    
    @staticmethod
    def create_offer(data, created_by=None):
        """
        Crea una nueva oferta.
        
        Args:
            data: Diccionario con datos de la oferta
            created_by: Usuario que crea la oferta
        
        Returns:
            Offer: Oferta creada
        """
        try:
            offer = Offer.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                offer_type=data['offer_type'],
                discount_percentage=data['discount_percentage'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                status=data.get('status', 'DRAFT'),
                max_uses=data.get('max_uses'),
                max_uses_per_user=data.get('max_uses_per_user', 1),
                min_purchase_amount=data.get('min_purchase_amount'),
                target_user=data.get('target_user'),
                priority=data.get('priority', 0),
                created_by=created_by
            )
            
            logger.info(f"Oferta creada: {offer.name} (ID: {offer.id})")
            return offer
            
        except Exception as e:
            logger.error(f"Error al crear oferta: {str(e)}")
            raise
    
    @staticmethod
    def activate_offer(offer_id, notify_users=True):
        """
        Activa una oferta y opcionalmente notifica a los usuarios.
        
        Args:
            offer_id: ID de la oferta
            notify_users: Si se debe notificar a los usuarios
        
        Returns:
            Offer: Oferta activada
        """
        try:
            offer = Offer.objects.get(id=offer_id)
            
            # Validar que tenga productos
            if not offer.offer_products.exists():
                raise ValueError("La oferta debe tener al menos un producto")
            
            # Activar
            offer.status = 'ACTIVE'
            offer.save(update_fields=['status', 'updated_at'])
            
            # Notificar usuarios
            if notify_users:
                if offer.offer_type == 'PERSONALIZED' and offer.target_user:
                    # Notificar solo al usuario objetivo
                    OfferService._notify_user_about_offer(offer.target_user, offer)
                elif offer.offer_type == 'FLASH_SALE':
                    # Notificar a todos los usuarios activos
                    OfferService._notify_all_users_about_flash_sale(offer)
                else:
                    # Para ofertas diarias y de temporada, notificar selectivamente
                    OfferService._notify_interested_users(offer)
            
            logger.info(f"Oferta activada: {offer.name} (ID: {offer.id})")
            return offer
            
        except Offer.DoesNotExist:
            logger.error(f"Oferta no encontrada: {offer_id}")
            raise
        except Exception as e:
            logger.error(f"Error al activar oferta {offer_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_active_offers_for_user(user):
        """
        Obtiene todas las ofertas activas para un usuario específico.
        
        Args:
            user: Usuario
        
        Returns:
            QuerySet: Ofertas activas
        """
        now = timezone.now()
        
        # Ofertas generales activas
        general_offers = Offer.objects.filter(
            status='ACTIVE',
            start_date__lte=now,
            end_date__gte=now,
            target_user__isnull=True
        ).filter(
            Q(max_uses__isnull=True) | Q(conversions_count__lt=F('max_uses'))
        )
        
        # Ofertas personalizadas para este usuario
        personal_offers = Offer.objects.filter(
            status='ACTIVE',
            start_date__lte=now,
            end_date__gte=now,
            target_user=user
        ).filter(
            Q(max_uses__isnull=True) | Q(conversions_count__lt=F('max_uses'))
        )
        
        # Combinar y ordenar por prioridad
        offers = (general_offers | personal_offers).distinct().order_by('-priority', '-created_at')
        
        # Filtrar por usos del usuario
        valid_offers = []
        for offer in offers:
            if offer.is_valid_for_user(user):
                valid_offers.append(offer.id)
        
        return Offer.objects.filter(id__in=valid_offers).order_by('-priority', '-created_at')
    
    @staticmethod
    def apply_offer_to_cart(user, offer, cart_items):
        """
        Aplica una oferta a un carrito de compras.
        
        Args:
            user: Usuario
            offer: Oferta a aplicar
            cart_items: Lista de items del carrito [{'product_id': id, 'quantity': qty}, ...]
        
        Returns:
            dict: Resultado con descuentos aplicados
        """
        try:
            # Validar que el usuario puede usar la oferta
            if not offer.is_valid_for_user(user):
                raise ValueError("Usuario no puede usar esta oferta")
            
            # Calcular total del carrito
            cart_total = Decimal('0.00')
            items_detail = []
            
            for item in cart_items:
                product = Product.objects.get(id=item['product_id'])
                quantity = item['quantity']
                subtotal = product.price * quantity
                cart_total += subtotal
                
                items_detail.append({
                    'product': product,
                    'quantity': quantity,
                    'original_price': product.price,
                    'subtotal': subtotal
                })
            
            # Validar monto mínimo
            if not offer.can_apply_to_cart(cart_total):
                min_amount = offer.min_purchase_amount or 0
                raise ValueError(f"El monto mínimo de compra es {min_amount}")
            
            # Calcular descuentos
            total_discount = Decimal('0.00')
            discounted_items = []
            
            offer_products = {op.product_id: op for op in offer.offer_products.all()}
            
            for item in items_detail:
                product = item['product']
                
                # Verificar si el producto está en la oferta
                if product.id in offer_products:
                    offer_product = offer_products[product.id]
                    discount_pct = offer_product.get_discount_percentage()
                    
                    # Calcular descuento
                    item_discount = item['subtotal'] * (discount_pct / 100)
                    discounted_price = item['subtotal'] - item_discount
                    
                    total_discount += item_discount
                    
                    discounted_items.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'quantity': item['quantity'],
                        'original_price': float(item['original_price']),
                        'discount_percentage': float(discount_pct),
                        'discount_amount': float(item_discount),
                        'final_price': float(discounted_price)
                    })
                else:
                    # Producto no está en la oferta
                    discounted_items.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'quantity': item['quantity'],
                        'original_price': float(item['original_price']),
                        'discount_percentage': 0,
                        'discount_amount': 0,
                        'final_price': float(item['subtotal'])
                    })
            
            final_total = cart_total - total_discount
            
            # Registrar interacción
            OfferService.track_interaction(
                user=user,
                offer=offer,
                action='ADDED_TO_CART'
            )
            
            return {
                'success': True,
                'offer_id': offer.id,
                'offer_name': offer.name,
                'original_total': float(cart_total),
                'total_discount': float(total_discount),
                'final_total': float(final_total),
                'items': discounted_items
            }
            
        except Product.DoesNotExist:
            logger.error("Producto no encontrado en carrito")
            raise ValueError("Producto no encontrado")
        except Exception as e:
            logger.error(f"Error al aplicar oferta: {str(e)}")
            raise
    
    @staticmethod
    def track_interaction(user, offer, action, product=None, session_id=None, ip_address=None, user_agent=None):
        """
        Registra una interacción del usuario con una oferta.
        
        Args:
            user: Usuario
            offer: Oferta
            action: Tipo de acción (VIEWED, CLICKED, etc.)
            product: Producto específico (opcional)
            session_id: ID de sesión
            ip_address: IP del usuario
            user_agent: User agent del navegador
        
        Returns:
            UserOfferInteraction: Interacción registrada
        """
        try:
            interaction = UserOfferInteraction.objects.create(
                user=user,
                offer=offer,
                action=action,
                product=product,
                session_id=session_id or '',
                ip_address=ip_address,
                user_agent=user_agent or ''
            )
            
            # Actualizar contadores de la oferta
            if action == 'VIEWED':
                offer.increment_view()
            elif action == 'CLICKED':
                offer.increment_click()
            elif action == 'USED':
                offer.increment_conversion()
            
            logger.info(f"Interacción registrada: {user.username} - {offer.name} - {action}")
            return interaction
            
        except Exception as e:
            logger.error(f"Error al registrar interacción: {str(e)}")
            raise
    
    @staticmethod
    def get_offer_stats():
        """
        Obtiene estadísticas generales de ofertas.
        
        Returns:
            dict: Estadísticas
        """
        now = timezone.now()
        
        total_offers = Offer.objects.count()
        active_offers = Offer.objects.filter(
            status='ACTIVE',
            start_date__lte=now,
            end_date__gte=now
        ).count()
        expired_offers = Offer.objects.filter(
            Q(status='EXPIRED') | Q(end_date__lt=now)
        ).count()
        
        # Estadísticas agregadas
        stats = Offer.objects.aggregate(
            total_views=Count('views_count'),
            total_clicks=Count('clicks_count'),
            total_conversions=Count('conversions_count')
        )
        
        # Mejor oferta por tasa de conversión
        best_offer = Offer.objects.filter(
            clicks_count__gt=0
        ).order_by(
            '-conversions_count'
        ).first()
        
        # Ofertas por tipo
        offers_by_type = dict(
            Offer.objects.values('offer_type').annotate(
                count=Count('id')
            ).values_list('offer_type', 'count')
        )
        
        # Ofertas por estado
        offers_by_status = dict(
            Offer.objects.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )
        
        # Calcular tasa de conversión promedio
        offers_with_clicks = Offer.objects.filter(clicks_count__gt=0)
        if offers_with_clicks.exists():
            avg_conversion = sum(o.get_conversion_rate() for o in offers_with_clicks) / offers_with_clicks.count()
        else:
            avg_conversion = 0
        
        return {
            'total_offers': total_offers,
            'active_offers': active_offers,
            'expired_offers': expired_offers,
            'total_views': sum(o.views_count for o in Offer.objects.all()),
            'total_clicks': sum(o.clicks_count for o in Offer.objects.all()),
            'total_conversions': sum(o.conversions_count for o in Offer.objects.all()),
            'average_conversion_rate': avg_conversion,
            'best_performing_offer': best_offer,
            'offers_by_type': offers_by_type,
            'offers_by_status': offers_by_status
        }
    
    @staticmethod
    def check_expiring_offers():
        """
        Verifica ofertas que están por expirar (menos de 24 horas)
        y notifica a los usuarios interesados.
        
        Returns:
            list: Ofertas notificadas
        """
        now = timezone.now()
        expiring_threshold = now + timezone.timedelta(hours=24)
        
        # Obtener ofertas activas que expiran en las próximas 24 horas
        expiring_offers = Offer.objects.filter(
            status='ACTIVE',
            end_date__lte=expiring_threshold,
            end_date__gt=now
        )
        
        notified_offers = []
        
        for offer in expiring_offers:
            # Obtener usuarios que han interactuado con la oferta pero no la han usado
            interested_users = User.objects.filter(
                offer_interactions__offer=offer,
                offer_interactions__action__in=['VIEWED', 'CLICKED']
            ).exclude(
                offer_interactions__offer=offer,
                offer_interactions__action='USED'
            ).distinct()
            
            # Notificar a cada usuario
            for user in interested_users:
                OfferService._notify_offer_expiring(user, offer)
            
            notified_offers.append(offer)
            logger.info(f"Notificados {interested_users.count()} usuarios sobre oferta expirando: {offer.name}")
        
        return notified_offers
    
    # Métodos privados de notificación
    
    @staticmethod
    def _notify_user_about_offer(user, offer):
        """Notifica a un usuario sobre una nueva oferta personalizada"""
        try:
            NotificationService.notify_new_offer(
                user=user,
                offer_name=offer.name,
                discount=str(offer.discount_percentage),
                end_date=offer.end_date,
                action_url=f'/offers/{offer.id}'
            )
        except Exception as e:
            logger.error(f"Error al notificar usuario {user.id} sobre oferta {offer.id}: {str(e)}")
    
    @staticmethod
    def _notify_all_users_about_flash_sale(offer):
        """Notifica a todos los usuarios sobre una venta flash"""
        try:
            active_users = User.objects.filter(is_active=True)
            for user in active_users:
                NotificationService.notify_new_offer(
                    user=user,
                    offer_name=offer.name,
                    discount=str(offer.discount_percentage),
                    end_date=offer.end_date,
                    action_url=f'/offers/{offer.id}'
                )
            logger.info(f"Notificados {active_users.count()} usuarios sobre flash sale: {offer.name}")
        except Exception as e:
            logger.error(f"Error al notificar flash sale {offer.id}: {str(e)}")
    
    @staticmethod
    def _notify_interested_users(offer):
        """Notifica a usuarios potencialmente interesados en la oferta"""
        try:
            # Obtener productos de la oferta
            product_ids = offer.offer_products.values_list('product_id', flat=True)
            
            # Obtener usuarios que han comprado productos similares
            from orders.models import OrderItem
            interested_users = User.objects.filter(
                orders__items__product_id__in=product_ids
            ).distinct()[:100]  # Limitar a 100 usuarios
            
            for user in interested_users:
                NotificationService.notify_new_offer(
                    user=user,
                    offer_name=offer.name,
                    discount=str(offer.discount_percentage),
                    end_date=offer.end_date,
                    action_url=f'/offers/{offer.id}'
                )
            
            logger.info(f"Notificados {interested_users.count()} usuarios interesados sobre: {offer.name}")
        except Exception as e:
            logger.error(f"Error al notificar usuarios interesados en oferta {offer.id}: {str(e)}")
    
    @staticmethod
    def _notify_offer_expiring(user, offer):
        """Notifica a un usuario que una oferta está por expirar"""
        try:
            hours_left = offer.hours_remaining()
            NotificationService.notify_offer_expiring(
                user=user,
                offer_name=offer.name,
                hours_left=hours_left,
                action_url=f'/offers/{offer.id}'
            )
        except Exception as e:
            logger.error(f"Error al notificar expiración de oferta {offer.id} a usuario {user.id}: {str(e)}")
