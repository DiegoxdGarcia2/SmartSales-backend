from django.contrib import admin
from .models import Category, Product, Brand, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Category.
    """
    list_display = ['name', 'description', 'get_products_count']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_products_count(self, obj):
        """
        Muestra el número de productos en la categoría.
        """
        return obj.products.count()
    
    get_products_count.short_description = 'Número de Productos'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Brand.
    """
    list_display = ['name', 'warranty_info', 'get_products_count', 'updated_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información de la Marca', {
            'fields': ('name', 'description', 'warranty_info')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_products_count(self, obj):
        """
        Muestra el número de productos de esta marca.
        """
        return obj.products.count()
    
    get_products_count.short_description = 'Número de Productos'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Product.
    """
    list_display = ['name', 'category', 'brand', 'price', 'stock', 'created_at']
    list_filter = ['category', 'brand', 'created_at']
    search_fields = ['name', 'description', 'brand__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category', 'brand')
        }),
        ('Precios e Inventario', {
            'fields': ('price', 'stock')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Review.
    """
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['comment', 'product__name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Información de la Reseña', {
            'fields': ('product', 'user', 'rating', 'comment')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
