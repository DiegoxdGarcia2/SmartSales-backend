from rest_framework import serializers
from .models import Category, Product


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


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Product.
    Muestra el nombre de la categoría en lugar del ID.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'stock',
            'category',
            'category_name',
            'category_detail',
            'marca',
            'garantia',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_name', 'category_detail']
    
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
