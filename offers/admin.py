"""
Configuración del admin de Django para el sistema de ofertas.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Offer, OfferProduct, UserOfferInteraction, OfferRecommendation


class OfferProductInline(admin.TabularInline):
    """Inline para productos en una oferta"""
    model = OfferProduct
    extra = 1
    fields = ['product', 'custom_discount', 'display_order']
    autocomplete_fields = ['product']


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Admin para Ofertas"""
    list_display = [
        'name',
        'offer_type',
        'discount_badge',
        'status_badge',
        'start_date',
        'end_date',
        'stats_display',
        'is_active'
    ]
    list_filter = ['offer_type', 'status', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    readonly_fields = [
        'views_count',
        'clicks_count',
        'conversions_count',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'offer_type', 'status')
        }),
        ('Descuento y Vigencia', {
            'fields': ('discount_percentage', 'start_date', 'end_date')
        }),
        ('Restricciones', {
            'fields': (
                'max_uses',
                'max_uses_per_user',
                'min_purchase_amount',
                'target_user',
                'priority'
            )
        }),
        ('Estadísticas', {
            'fields': ('views_count', 'clicks_count', 'conversions_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OfferProductInline]
    
    def discount_badge(self, obj):
        """Muestra el descuento como badge"""
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{:.0f}% OFF</span>',
            obj.discount_percentage
        )
    discount_badge.short_description = 'Descuento'
    
    def status_badge(self, obj):
        """Muestra el estado con colores"""
        colors = {
            'ACTIVE': '#28a745',
            'DRAFT': '#6c757d',
            'PAUSED': '#ffc107',
            'EXPIRED': '#dc3545',
            'CANCELLED': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def stats_display(self, obj):
        """Muestra estadísticas resumidas"""
        conversion_rate = obj.get_conversion_rate()
        return format_html(
            '👁 {} | 🖱 {} | ✅ {} | 📊 {:.1f}%',
            obj.views_count,
            obj.clicks_count,
            obj.conversions_count,
            conversion_rate
        )
    stats_display.short_description = 'Vistas | Clicks | Conversiones | Tasa'
    
    def save_model(self, request, obj, form, change):
        """Asigna el usuario creador si es nuevo"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OfferProduct)
class OfferProductAdmin(admin.ModelAdmin):
    """Admin para productos en ofertas"""
    list_display = ['offer', 'product', 'discount_display', 'display_order', 'added_at']
    list_filter = ['offer__offer_type', 'added_at']
    search_fields = ['offer__name', 'product__name']
    autocomplete_fields = ['offer', 'product']
    
    def discount_display(self, obj):
        """Muestra el descuento aplicable"""
        discount = obj.get_discount_percentage()
        return f"{discount}%"
    discount_display.short_description = 'Descuento'


@admin.register(UserOfferInteraction)
class UserOfferInteractionAdmin(admin.ModelAdmin):
    """Admin para interacciones de usuarios"""
    list_display = ['user', 'offer', 'action', 'product', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'offer__name', 'product__name']
    readonly_fields = ['user', 'offer', 'action', 'product', 'session_id', 'ip_address', 'user_agent', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        """No se pueden crear manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No se pueden editar"""
        return False


@admin.register(OfferRecommendation)
class OfferRecommendationAdmin(admin.ModelAdmin):
    """Admin para recomendaciones de ofertas"""
    list_display = [
        'user',
        'offer',
        'product',
        'score_display',
        'tracking_status',
        'model_version',
        'created_at'
    ]
    list_filter = ['was_shown', 'was_clicked', 'was_converted', 'model_version', 'created_at']
    search_fields = ['user__username', 'offer__name', 'product__name']
    readonly_fields = [
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
        'created_at'
    ]
    date_hierarchy = 'created_at'
    
    def score_display(self, obj):
        """Muestra el score con barra visual"""
        percentage = int(obj.score * 100)
        color = '#28a745' if obj.score >= 0.7 else '#ffc107' if obj.score >= 0.4 else '#dc3545'
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; color: white; text-align: center; '
            'border-radius: 3px; padding: 2px;">{:.0f}%</div></div>',
            percentage,
            color,
            percentage
        )
    score_display.short_description = 'Score'
    
    def tracking_status(self, obj):
        """Muestra el estado de tracking"""
        icons = []
        if obj.was_shown:
            icons.append('👁')
        if obj.was_clicked:
            icons.append('🖱')
        if obj.was_converted:
            icons.append('✅')
        return ' '.join(icons) if icons else '⏳'
    tracking_status.short_description = 'Tracking'
    
    def has_add_permission(self, request):
        """No se pueden crear manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No se pueden editar"""
        return False
