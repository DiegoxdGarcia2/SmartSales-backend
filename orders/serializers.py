from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.serializers import ProductSerializer
from products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer para items del carrito
    """
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    item_price = serializers.SerializerMethodField()
    base_price = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'discount_percentage', 
                  'item_price', 'base_price', 'discount_amount']

    def get_item_price(self, obj):
        """
        Calcula el precio total del item con descuento aplicado
        """
        return obj.get_item_price()
    
    def get_base_price(self, obj):
        """
        Calcula el precio base sin descuento
        """
        return obj.get_base_price()
    
    def get_discount_amount(self, obj):
        """
        Calcula el monto del descuento aplicado
        """
        return obj.get_discount_amount()

    def validate_quantity(self, value):
        """
        Valida que la cantidad sea mayor a 0
        """
        if value < 1:
            raise serializers.ValidationError("La cantidad debe ser al menos 1")
        return value
    
    def validate_discount_percentage(self, value):
        """
        Valida que el porcentaje de descuento esté entre 0 y 100
        """
        if value < 0 or value > 100:
            raise serializers.ValidationError("El descuento debe estar entre 0 y 100")
        return value

    def validate(self, data):
        """
        Valida que haya stock disponible
        """
        product = data.get('product')
        quantity = data.get('quantity', 1)

        if product and quantity > product.stock:
            raise serializers.ValidationError({
                'quantity': f'Stock insuficiente. Disponible: {product.stock}'
            })

        return data


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer para el carrito completo
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'items_count', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        """
        Calcula el precio total del carrito
        """
        return obj.get_total_price()

    def get_items_count(self, obj):
        """
        Cuenta el número total de items en el carrito
        """
        return obj.items.count()


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer para items de la orden
    """
    product = ProductSerializer(read_only=True)
    item_price = serializers.SerializerMethodField()
    base_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'quantity', 'price', 'item_price',
            'base_price', 'discount_percentage', 'discount_amount'
        ]

    def get_item_price(self, obj):
        """
        Calcula el precio total del item
        """
        return obj.get_item_price()

    def get_base_price(self, obj):
        """
        Calcula el precio base sin descuento
        """
        if obj.product:
            return obj.product.price * obj.quantity
        return 0

    def get_discount_percentage(self, obj):
        """
        Calcula el porcentaje de descuento aplicado
        """
        if obj.product and obj.product.price > 0:
            original_unit_price = obj.product.price
            discount = (original_unit_price - obj.price) / original_unit_price * 100
            return max(0, discount)  # No mostrar descuentos negativos
        return 0

    def get_discount_amount(self, obj):
        """
        Calcula el monto del descuento aplicado
        """
        if obj.product:
            original_total = obj.product.price * obj.quantity
            return original_total - obj.get_item_price()
        return 0


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer para órdenes
    """
    items = OrderItemSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'username',
            'status',
            'total_price',
            'shipping_address',
            'shipping_phone',
            'items',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['user', 'total_price', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer para crear una orden desde el carrito
    """
    shipping_address = serializers.CharField(required=False, allow_blank=True)
    shipping_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
