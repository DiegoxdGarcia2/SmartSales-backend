from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.conf import settings
import stripe

from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    OrderCreateSerializer
)
from products.models import Product


class CartView(APIView):
    """
    Vista para gestionar el carrito de compras del usuario
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Obtiene o crea el carrito del usuario autenticado
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        """
        Añade un item al carrito o actualiza la cantidad si ya existe
        """
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response(
                {'error': 'product_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validar stock
        if quantity > product.stock:
            return Response(
                {'error': f'Stock insuficiente. Disponible: {product.stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener o crear el carrito
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Verificar si el producto ya está en el carrito
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            # Si ya existe, actualizar la cantidad
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                return Response(
                    {'error': f'Stock insuficiente. Disponible: {product.stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = new_quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request):
        """
        Actualiza la cantidad de un item en el carrito
        """
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        if not item_id or quantity is None:
            return Response(
                {'error': 'item_id y quantity son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Item no encontrado en tu carrito'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validar cantidad
        if quantity < 1:
            return Response(
                {'error': 'La cantidad debe ser al menos 1'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar stock
        if quantity > cart_item.product.stock:
            return Response(
                {'error': f'Stock insuficiente. Disponible: {cart_item.product.stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data)

    def delete(self, request):
        """
        Elimina un item del carrito
        """
        item_id = request.data.get('item_id')

        if not item_id:
            return Response(
                {'error': 'item_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
            cart_item.delete()
            return Response(
                {'message': 'Item eliminado del carrito'},
                status=status.HTTP_204_NO_CONTENT
            )
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Item no encontrado en tu carrito'},
                status=status.HTTP_404_NOT_FOUND
            )


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver órdenes del usuario
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Retorna solo las órdenes del usuario autenticado
        """
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def create_order_from_cart(self, request):
        """
        Crea una orden desde el carrito actual del usuario
        (antes de procesar el pago con Stripe)
        """
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()

            if not cart_items.exists():
                return Response(
                    {'error': 'El carrito está vacío'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                # Validar stock ANTES de crear la orden
                for item in cart_items:
                    if item.product.stock < item.quantity:
                        return Response(
                            {'error': f'Stock insuficiente para {item.product.name}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Crear la orden
                order = Order.objects.create(
                    user=request.user,
                    total_price=cart.get_total_price(),
                    shipping_address=request.data.get('shipping_address', ''),
                    shipping_phone=request.data.get('shipping_phone', '')
                )

                # Crear OrderItems y reducir stock
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                    # Reducir stock
                    item.product.stock -= item.quantity
                    item.product.save()

                # Vaciar carrito
                cart_items.delete()

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Carrito no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al crear la orden: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateCheckoutSessionView(APIView):
    """
    Vista para crear una sesión de checkout de Stripe para una orden
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = request.data.get('order_id')
        
        if not order_id:
            return Response(
                {'error': 'order_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(
                id=order_id,
                user=request.user,
                status='PENDIENTE'
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Orden no válida o no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Construir line_items para Stripe
        line_items = []
        for item in order.items.all():
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.name if item.product else 'Producto eliminado',
                    },
                    'unit_amount': int(item.price * 100),  # Stripe usa centavos
                },
                'quantity': item.quantity,
            })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=settings.FRONTEND_CHECKOUT_SUCCESS_URL,
                cancel_url=settings.FRONTEND_CHECKOUT_CANCEL_URL,
                metadata={
                    'order_id': order.id
                },
            )

            # Guardar el ID de la sesión en la orden
            order.stripe_checkout_id = checkout_session.id
            order.save()

            # Devolver la URL de la sesión de checkout
            return Response({'url': checkout_session.url})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeWebhookView(APIView):
    """
    Vista para recibir y procesar webhooks de Stripe
    """
    # No CSRF protection needed for webhooks
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            return Response(
                {'error': 'Invalid payload'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return Response(
                {'error': 'Invalid signature'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            order_id = session.get('metadata', {}).get('order_id')
            payment_intent_id = session.get('payment_intent')

            try:
                order = Order.objects.get(id=order_id)
                
                # Evitar procesar dos veces
                if order.payment_status == 'pendiente':
                    order.status = 'PAGADO'
                    order.payment_status = 'pagado'
                    order.stripe_payment_intent_id = payment_intent_id
                    order.save()
                    
                    print(f"✅ Orden {order_id} marcada como PAGADO.")
                    
            except Order.DoesNotExist:
                print(f"❌ Error: Orden {order_id} no encontrada para evento webhook.")
                return Response(
                    {'error': 'Orden no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                print(f"❌ Error procesando webhook para orden {order_id}: {str(e)}")
                return Response(
                    {'error': 'Error interno'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        elif event['type'] == 'payment_intent.payment_failed':
            # Manejar pagos fallidos
            session = event['data']['object']
            order_id = session.get('metadata', {}).get('order_id')
            
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    order.payment_status = 'fallido'
                    order.save()
                    print(f"⚠️ Pago fallido para orden {order_id}")
                except Order.DoesNotExist:
                    pass

        return Response(status=status.HTTP_200_OK)
