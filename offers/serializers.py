"""
Serializers para el sistema de ofertas de SmartSales.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Offer, OfferProduct, UserOfferInteraction, OfferRecommendation
from products.serializers import ProductSerializer


class OfferProductSerializer(serializers.ModelSerializer):
    """Serializer para productos dentro de una oferta"""
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    discount_percentage = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    savings = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferProduct
        fields = [
            'id',
            'product',
            'product_id',
            'custom_discount',
            'discount_percentage',
            'discounted_price',
            'savings',
            'display_order',
            'added_at',
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_discount_percentage(self, obj):
        return float(obj.get_discount_percentage())
    
    def get_discounted_price(self, obj):
        return float(obj.get_discounted_price())
    
    def get_savings(self, obj):
        return float(obj.get_savings())


class OfferSerializer(serializers.ModelSerializer):
    """Serializer completo para ofertas"""
    offer_products = OfferProductSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    target_user_name = serializers.CharField(source='target_user.username', read_only=True)
    is_active = serializers.SerializerMethodField()
    time_remaining_hours = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Offer
        fields = [
            'id',
            'name',
            'description',
            'offer_type',
            'discount_percentage',
            'start_date',
            'end_date',
            'status',
            'max_uses',
            'max_uses_per_user',
            'min_purchase_amount',
            'target_user',
            'target_user_name',
            'priority',
            'views_count',
            'clicks_count',
            'conversions_count',
            'conversion_rate',
            'is_active',
            'time_remaining_hours',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'offer_products',
        ]
        read_only_fields = [
            'id',
            'views_count',
            'clicks_count',
            'conversions_count',
            'created_at',
            'updated_at',
        ]
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_time_remaining_hours(self, obj):
        return obj.hours_remaining()
    
    def get_conversion_rate(self, obj):
        return obj.get_conversion_rate()
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que end_date sea después de start_date
        if 'start_date' in data and 'end_date' in data:
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
        
        # Validar que ofertas personalizadas tengan target_user
        if data.get('offer_type') == 'PERSONALIZED' and not data.get('target_user'):
            raise serializers.ValidationError({
                'target_user': 'Las ofertas personalizadas deben tener un usuario objetivo.'
            })
        
        # Validar que ofertas no personalizadas no tengan target_user
        if data.get('offer_type') != 'PERSONALIZED' and data.get('target_user'):
            raise serializers.ValidationError({
                'target_user': 'Solo las ofertas personalizadas pueden tener un usuario objetivo.'
            })
        
        return data


class OfferListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados de ofertas"""
    is_active = serializers.SerializerMethodField()
    time_remaining_hours = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    offer_products = OfferProductSerializer(many=True, read_only=True)  # 🆕 Para filtros por categoría
    
    class Meta:
        model = Offer
        fields = [
            'id',
            'name',
            'description',
            'offer_type',
            'discount_percentage',
            'start_date',
            'end_date',
            'status',
            'is_active',
            'time_remaining_hours',
            'products_count',
            'priority',
            'conversions_count',
            'created_at',
            'offer_products',  # 🆕 Incluir productos en el listado
        ]
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_time_remaining_hours(self, obj):
        return obj.hours_remaining()
    
    def get_products_count(self, obj):
        return obj.offer_products.count()


class UserOfferInteractionSerializer(serializers.ModelSerializer):
    """Serializer para interacciones de usuarios con ofertas"""
    offer_name = serializers.CharField(source='offer.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True, allow_null=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserOfferInteraction
        fields = [
            'id',
            'user',
            'user_name',
            'offer',
            'offer_name',
            'action',
            'product',
            'product_name',
            'session_id',
            'ip_address',
            'user_agent',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class OfferRecommendationSerializer(serializers.ModelSerializer):
    """Serializer para recomendaciones de ofertas"""
    offer = OfferListSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OfferRecommendation
        fields = [
            'id',
            'user',
            'offer',
            'product',
            'score',
            'reason',
            'was_shown',
            'shown_at',
            'was_clicked',
            'clicked_at',
            'was_converted',
            'converted_at',
            'model_version',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'was_shown',
            'shown_at',
            'was_clicked',
            'clicked_at',
            'was_converted',
            'converted_at',
            'created_at',
        ]


class OfferStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de ofertas"""
    total_offers = serializers.IntegerField()
    active_offers = serializers.IntegerField()
    expired_offers = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    average_conversion_rate = serializers.FloatField()
    best_performing_offer = OfferListSerializer(allow_null=True)
    offers_by_type = serializers.DictField()
    offers_by_status = serializers.DictField()


class OfferApplicationSerializer(serializers.Serializer):
    """Serializer para aplicar una oferta al carrito"""
    offer_id = serializers.IntegerField()
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    
    def validate_offer_id(self, value):
        try:
            offer = Offer.objects.get(id=value)
            if not offer.is_active():
                raise serializers.ValidationError('Esta oferta no está activa.')
        except Offer.DoesNotExist:
            raise serializers.ValidationError('Oferta no encontrada.')
        return value


class CreateOfferSerializer(serializers.ModelSerializer):
    """Serializer para crear ofertas con productos"""
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Offer
        fields = [
            'name',
            'description',
            'offer_type',
            'discount_percentage',
            'start_date',
            'end_date',
            'status',
            'max_uses',
            'max_uses_per_user',
            'min_purchase_amount',
            'target_user',
            'priority',
            'product_ids',
        ]
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que end_date sea después de start_date
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError({
                'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
            })
        
        # Validar que ofertas personalizadas tengan target_user
        if data.get('offer_type') == 'PERSONALIZED' and not data.get('target_user'):
            raise serializers.ValidationError({
                'target_user': 'Las ofertas personalizadas deben tener un usuario objetivo.'
            })
        
        # Validar que ofertas no personalizadas no tengan target_user
        if data.get('offer_type') != 'PERSONALIZED' and data.get('target_user'):
            raise serializers.ValidationError({
                'target_user': 'Solo las ofertas personalizadas pueden tener un usuario objetivo.'
            })
        
        # Validar que haya productos
        product_ids = data.get('product_ids', [])
        if not product_ids:
            raise serializers.ValidationError({
                'product_ids': 'Debes agregar al menos un producto a la oferta.'
            })
        
        return data
    
    def create(self, validated_data):
        """Crear oferta con productos"""
        product_ids = validated_data.pop('product_ids', [])
        
        # Crear la oferta
        offer = Offer.objects.create(**validated_data)
        
        # Agregar productos
        from products.models import Product
        for idx, product_id in enumerate(product_ids):
            try:
                product = Product.objects.get(id=product_id)
                OfferProduct.objects.create(
                    offer=offer,
                    product=product,
                    display_order=idx
                )
            except Product.DoesNotExist:
                pass  # Ignorar productos no encontrados
        
        return offer
