from django.contrib import admin
from .models import Category, Product


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Product.
    """
    list_display = ['name', 'category', 'price', 'stock', 'marca', 'created_at']
    list_filter = ['category', 'marca', 'created_at']
    search_fields = ['name', 'description', 'marca']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category')
        }),
        ('Precios e Inventario', {
            'fields': ('price', 'stock')
        }),
        ('Detalles Adicionales', {
            'fields': ('marca', 'garantia')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
