from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    """
    Inline para ver items del carrito dentro de la vista de Cart
    """
    model = CartItem
    extra = 0
    readonly_fields = ['get_item_price']
    fields = ['product', 'quantity', 'get_item_price']

    def get_item_price(self, obj):
        if obj.id:
            return f"${obj.get_item_price()}"
        return "-"
    get_item_price.short_description = 'Precio Total'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Cart
    """
    list_display = ['user', 'get_items_count', 'get_total_price', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'get_total_price']
    inlines = [CartItemInline]

    def get_items_count(self, obj):
        return obj.items.count()
    get_items_count.short_description = 'Items'

    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para CartItem
    """
    list_display = ['cart', 'product', 'quantity', 'get_item_price']
    list_filter = ['cart__user']
    search_fields = ['cart__user__username', 'product__name']

    def get_item_price(self, obj):
        return f"${obj.get_item_price()}"
    get_item_price.short_description = 'Precio Total'


class OrderItemInline(admin.TabularInline):
    """
    Inline para ver items de la orden dentro de la vista de Order
    """
    model = OrderItem
    extra = 0
    readonly_fields = ['get_item_price']
    fields = ['product', 'quantity', 'price', 'get_item_price']

    def get_item_price(self, obj):
        if obj.id:
            return f"${obj.get_item_price()}"
        return "-"
    get_item_price.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para Order
    """
    list_display = [
        'id',
        'user',
        'status',
        'total_price',
        'get_items_count',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email', 'id']
    readonly_fields = ['total_price', 'created_at', 'updated_at']
    inlines = [OrderItemInline]

    fieldsets = (
        ('Información de la Orden', {
            'fields': ('user', 'status', 'total_price')
        }),
        ('Información de Envío', {
            'fields': ('shipping_address', 'shipping_phone')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_items_count(self, obj):
        return obj.items.count()
    get_items_count.short_description = 'Items'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para OrderItem
    """
    list_display = ['order', 'product', 'quantity', 'price', 'get_item_price']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['order__id', 'product__name']

    def get_item_price(self, obj):
        return f"${obj.get_item_price()}"
    get_item_price.short_description = 'Subtotal'
