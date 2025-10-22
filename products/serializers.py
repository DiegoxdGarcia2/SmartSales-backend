from rest_framework import serializers
from .models import Category, Product, Brand


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Category.
    """
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'products_count']
        read_only_fields = ['id']
    
    def get_products_count(self, obj):
        """
        Retorna el número de productos en esta categoría.
        """
        return obj.products.count()


class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Brand.
    """
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'description', 'warranty_info', 'products_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_products_count(self, obj):
        """
        Retorna el número de productos de esta marca.
        """
        return obj.products.count()


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Product.
    Muestra detalles de categoría y marca.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    
    brand = BrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source='brand',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'stock',
            'category',
            'category_id',
            'category_name',
            'category_detail',
            'brand',
            'brand_id',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_name', 'category_detail', 'brand']
    
    def validate_price(self, value):
        """
        Valida que el precio sea positivo.
        """
        if value < 0:
            raise serializers.ValidationError("El precio debe ser un valor positivo.")
        return value
    
    def validate_stock(self, value):
        """
        Valida que el stock no sea negativo.
        """
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo.")
        return value
