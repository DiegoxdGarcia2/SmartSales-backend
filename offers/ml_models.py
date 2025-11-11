"""
Sistema de Machine Learning para recomendaciones de ofertas personalizadas.
Utiliza historial de compras, interacciones y análisis de productos.
"""
import logging
from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta
from django.db.models import Count, Avg, F, Q, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
import numpy as np

from .models import Offer, OfferProduct, UserOfferInteraction, OfferRecommendation
from products.models import Product
from orders.models import Order, OrderItem

User = get_user_model()
logger = logging.getLogger(__name__)


class OfferRecommendationEngine:
    """
    Motor de recomendación de ofertas basado en ML.
    Genera recomendaciones personalizadas usando múltiples estrategias.
    """
    
    MODEL_VERSION = "1.0"
    
    def __init__(self):
        self.min_score_threshold = 0.3  # Score mínimo para recomendar
    
    def generate_recommendations_for_user(self, user, max_recommendations=10):
        """
        Genera recomendaciones de ofertas para un usuario.
        
        Args:
            user: Usuario
            max_recommendations: Número máximo de recomendaciones
        
        Returns:
            list: Lista de OfferRecommendation creadas
        """
        try:
            # Obtener ofertas activas
            active_offers = self._get_active_offers()
            
            if not active_offers:
                logger.info(f"No hay ofertas activas para recomendar a {user.username}")
                return []
            
            # Calcular scores para cada oferta
            recommendations = []
            
            for offer in active_offers:
                # Calcular score compuesto
                score_data = self._calculate_offer_score(user, offer)
                
                if score_data['score'] >= self.min_score_threshold:
                    # Determinar producto recomendado dentro de la oferta
                    recommended_product = self._get_recommended_product_from_offer(user, offer)
                    
                    # Crear o actualizar recomendación
                    recommendation, created = OfferRecommendation.objects.update_or_create(
                        user=user,
                        offer=offer,
                        product=recommended_product,
                        defaults={
                            'score': score_data['score'],
                            'reason': score_data['reason'],
                            'model_version': self.MODEL_VERSION
                        }
                    )
                    
                    recommendations.append(recommendation)
            
            # Ordenar por score y limitar
            recommendations.sort(key=lambda x: x.score, reverse=True)
            top_recommendations = recommendations[:max_recommendations]
            
            logger.info(
                f"Generadas {len(top_recommendations)} recomendaciones para {user.username}"
            )
            
            return top_recommendations
            
        except Exception as e:
            logger.error(f"Error al generar recomendaciones para {user.id}: {str(e)}")
            return []
    
    def _get_active_offers(self):
        """Obtiene ofertas activas"""
        now = timezone.now()
        return Offer.objects.filter(
            status='ACTIVE',
            start_date__lte=now,
            end_date__gte=now
        ).filter(
            Q(max_uses__isnull=True) | Q(conversions_count__lt=F('max_uses'))
        )
    
    def _calculate_offer_score(self, user, offer):
        """
        Calcula el score de una oferta para un usuario.
        
        Factores considerados:
        - Historial de compras (40%)
        - Interacciones previas (20%)
        - Popularidad de la oferta (15%)
        - Descuento atractivo (15%)
        - Urgencia (tiempo restante) (10%)
        
        Returns:
            dict: {'score': float, 'reason': dict}
        """
        reason = {}
        
        # 1. Score de historial de compras (40%)
        purchase_score = self._calculate_purchase_history_score(user, offer)
        reason['purchase_history'] = f"Score de historial: {purchase_score:.2f}"
        
        # 2. Score de interacciones previas (20%)
        interaction_score = self._calculate_interaction_score(user, offer)
        reason['interactions'] = f"Score de interacciones: {interaction_score:.2f}"
        
        # 3. Score de popularidad (15%)
        popularity_score = self._calculate_popularity_score(offer)
        reason['popularity'] = f"Score de popularidad: {popularity_score:.2f}"
        
        # 4. Score de descuento (15%)
        discount_score = self._calculate_discount_score(offer)
        reason['discount'] = f"Descuento del {offer.discount_percentage}%"
        
        # 5. Score de urgencia (10%)
        urgency_score = self._calculate_urgency_score(offer)
        reason['urgency'] = f"Expira en {offer.hours_remaining()} horas"
        
        # Calcular score total ponderado
        total_score = (
            purchase_score * 0.40 +
            interaction_score * 0.20 +
            popularity_score * 0.15 +
            discount_score * 0.15 +
            urgency_score * 0.10
        )
        
        # Normalizar entre 0 y 1
        total_score = max(0.0, min(1.0, total_score))
        
        return {
            'score': total_score,
            'reason': reason
        }
    
    def _calculate_purchase_history_score(self, user, offer):
        """
        Calcula score basado en historial de compras.
        Si el usuario ha comprado productos similares, score más alto.
        """
        try:
            # Obtener productos de la oferta
            offer_product_ids = offer.offer_products.values_list('product_id', flat=True)
            
            if not offer_product_ids:
                return 0.0
            
            # Obtener categorías de productos en la oferta
            offer_categories = Product.objects.filter(
                id__in=offer_product_ids
            ).values_list('category', flat=True).distinct()
            
            # Contar compras del usuario en esas categorías
            user_purchases_in_categories = OrderItem.objects.filter(
                order__user=user,
                order__status='completed',
                product__category__in=offer_categories
            ).count()
            
            # Contar compras totales del usuario
            total_user_purchases = OrderItem.objects.filter(
                order__user=user,
                order__status='completed'
            ).count()
            
            if total_user_purchases == 0:
                # Usuario nuevo, dar score neutral
                return 0.5
            
            # Calcular ratio
            ratio = user_purchases_in_categories / total_user_purchases
            
            # Ajustar a escala 0-1
            return min(1.0, ratio * 2)
            
        except Exception as e:
            logger.error(f"Error calculando purchase history score: {str(e)}")
            return 0.5
    
    def _calculate_interaction_score(self, user, offer):
        """
        Calcula score basado en interacciones previas del usuario.
        Penaliza si el usuario ya descartó la oferta.
        """
        try:
            # Verificar si el usuario ya interactuó con esta oferta
            interactions = UserOfferInteraction.objects.filter(
                user=user,
                offer=offer
            )
            
            if not interactions.exists():
                return 0.5  # Neutral si no hay interacciones
            
            # Penalizar si descartó
            if interactions.filter(action='DISMISSED').exists():
                return 0.0
            
            # Premiar si vio pero no compró (interesado)
            if interactions.filter(action__in=['VIEWED', 'CLICKED']).exists():
                return 0.8
            
            # Si ya usó, no recomendar de nuevo
            if interactions.filter(action='USED').exists():
                return 0.0
            
            return 0.5
            
        except Exception as e:
            logger.error(f"Error calculando interaction score: {str(e)}")
            return 0.5
    
    def _calculate_popularity_score(self, offer):
        """
        Calcula score basado en popularidad de la oferta.
        Ofertas con buena tasa de conversión obtienen mayor score.
        """
        try:
            if offer.clicks_count == 0:
                return 0.5  # Neutral si no hay datos
            
            conversion_rate = offer.get_conversion_rate() / 100  # Convertir a 0-1
            
            # Ajustar por número de interacciones (más datos = más confiable)
            confidence = min(1.0, offer.clicks_count / 100)
            
            # Score ponderado por confianza
            return conversion_rate * confidence + 0.5 * (1 - confidence)
            
        except Exception as e:
            logger.error(f"Error calculando popularity score: {str(e)}")
            return 0.5
    
    def _calculate_discount_score(self, offer):
        """
        Calcula score basado en el descuento.
        Descuentos mayores = score más alto.
        """
        try:
            discount = float(offer.discount_percentage)
            
            # Escalar de 0-100% a 0-1
            # 10% = 0.3, 20% = 0.5, 50% = 0.9, 70%+ = 1.0
            if discount <= 10:
                return 0.3
            elif discount <= 20:
                return 0.5
            elif discount <= 30:
                return 0.7
            elif discount <= 50:
                return 0.9
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculando discount score: {str(e)}")
            return 0.5
    
    def _calculate_urgency_score(self, offer):
        """
        Calcula score basado en urgencia (tiempo restante).
        Ofertas que expiran pronto obtienen mayor score.
        """
        try:
            hours_remaining = offer.hours_remaining()
            
            if hours_remaining is None or hours_remaining <= 0:
                return 0.0
            
            # Menos de 24 horas = urgente
            if hours_remaining <= 24:
                return 1.0
            # Menos de 3 días = moderadamente urgente
            elif hours_remaining <= 72:
                return 0.7
            # Menos de 1 semana = algo urgente
            elif hours_remaining <= 168:
                return 0.5
            # Más de 1 semana = no urgente
            else:
                return 0.3
                
        except Exception as e:
            logger.error(f"Error calculando urgency score: {str(e)}")
            return 0.5
    
    def _get_recommended_product_from_offer(self, user, offer):
        """
        Determina qué producto específico recomendar de una oferta.
        Elige el producto que el usuario tiene más probabilidad de comprar.
        """
        try:
            offer_products = offer.offer_products.all()
            
            if not offer_products.exists():
                return None
            
            # Si solo hay un producto, retornarlo
            if offer_products.count() == 1:
                return offer_products.first().product
            
            # Calcular score para cada producto
            product_scores = []
            
            for offer_product in offer_products:
                product = offer_product.product
                
                # Factores:
                # - Usuario ha comprado productos de esa categoría
                # - Precio dentro del rango que suele comprar
                # - Stock disponible
                
                score = 0.0
                
                # Score de categoría
                user_bought_category = OrderItem.objects.filter(
                    order__user=user,
                    order__status='completed',
                    product__category=product.category
                ).exists()
                
                if user_bought_category:
                    score += 0.5
                
                # Score de precio
                avg_purchase_price = OrderItem.objects.filter(
                    order__user=user,
                    order__status='completed'
                ).aggregate(
                    avg_price=Avg('price')
                )['avg_price'] or Decimal('0')
                
                if avg_purchase_price > 0:
                    price_diff = abs(float(product.price) - float(avg_purchase_price))
                    price_score = max(0, 1 - (price_diff / float(avg_purchase_price)))
                    score += price_score * 0.3
                
                # Score de stock
                if product.stock > 10:
                    score += 0.2
                elif product.stock > 0:
                    score += 0.1
                
                product_scores.append((product, score))
            
            # Ordenar por score y retornar el mejor
            product_scores.sort(key=lambda x: x[1], reverse=True)
            return product_scores[0][0]
            
        except Exception as e:
            logger.error(f"Error determinando producto recomendado: {str(e)}")
            # Retornar el primer producto por defecto
            first_product = offer.offer_products.first()
            return first_product.product if first_product else None


class DiscountOptimizer:
    """
    Optimizador de descuentos usando análisis de datos.
    Sugiere el porcentaje de descuento óptimo para maximizar ventas.
    """
    
    def __init__(self):
        self.historical_window_days = 90  # Analizar últimos 90 días
    
    def suggest_optimal_discount(self, product, target_sales_increase=1.5):
        """
        Sugiere el descuento óptimo para un producto.
        
        Args:
            product: Producto
            target_sales_increase: Multiplicador de ventas deseado (1.5 = 50% más ventas)
        
        Returns:
            dict: Sugerencia de descuento con análisis
        """
        try:
            # Analizar historial del producto
            historical_data = self._analyze_product_history(product)
            
            # Analizar elasticidad de precio
            price_elasticity = self._estimate_price_elasticity(product)
            
            # Analizar competencia (productos similares)
            competitive_analysis = self._analyze_competition(product)
            
            # Calcular descuento sugerido
            suggested_discount = self._calculate_suggested_discount(
                historical_data,
                price_elasticity,
                competitive_analysis,
                target_sales_increase
            )
            
            # Calcular proyección de impacto
            impact_projection = self._project_impact(
                product,
                suggested_discount,
                historical_data
            )
            
            discount_decimal = Decimal(str(suggested_discount / 100))
            discounted_price = product.price * (Decimal('1') - discount_decimal)
            
            return {
                'product_id': product.id,
                'product_name': product.name,
                'current_price': float(product.price),
                'suggested_discount_percentage': suggested_discount,
                'discounted_price': float(discounted_price),
                'historical_avg_sales': historical_data['avg_monthly_sales'],
                'projected_sales_increase': impact_projection['sales_increase_percentage'],
                'projected_revenue_impact': impact_projection['revenue_impact'],
                'confidence_level': impact_projection['confidence'],
                'reasoning': {
                    'price_elasticity': price_elasticity,
                    'competitive_position': competitive_analysis,
                    'historical_performance': historical_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error sugiriendo descuento óptimo: {str(e)}")
            # Retornar sugerencia conservadora
            return {
                'product_id': product.id,
                'product_name': product.name,
                'current_price': float(product.price),
                'suggested_discount_percentage': 15.0,
                'error': str(e)
            }
    
    def _analyze_product_history(self, product):
        """Analiza el historial de ventas del producto"""
        try:
            cutoff_date = timezone.now() - timedelta(days=self.historical_window_days)
            
            # Obtener ventas históricas
            sales = OrderItem.objects.filter(
                product=product,
                order__status='completed',
                order__created_at__gte=cutoff_date
            )
            
            total_sales = sales.count()
            total_revenue = sales.aggregate(
                total=Sum(F('price') * F('quantity'))
            )['total'] or Decimal('0')
            
            avg_monthly_sales = total_sales / 3  # Últimos 3 meses
            
            return {
                'total_sales': total_sales,
                'total_revenue': float(total_revenue),
                'avg_monthly_sales': avg_monthly_sales,
                'has_sufficient_data': total_sales >= 10
            }
            
        except Exception as e:
            logger.error(f"Error analizando historial: {str(e)}")
            return {
                'total_sales': 0,
                'total_revenue': 0,
                'avg_monthly_sales': 0,
                'has_sufficient_data': False
            }
    
    def _estimate_price_elasticity(self, product):
        """Estima la elasticidad de precio del producto"""
        # Simplificado: Clasificar por categoría
        # En un sistema real, se calcularía usando datos históricos de cambios de precio
        
        # Categorías con alta elasticidad (sensibles al precio)
        high_elasticity_categories = ['Electrónica', 'Ropa', 'Accesorios']
        
        # Categorías con baja elasticidad (menos sensibles)
        low_elasticity_categories = ['Alimentos', 'Medicamentos', 'Libros']
        
        if product.category in high_elasticity_categories:
            return 'high'  # Pequeños descuentos generan grandes cambios en demanda
        elif product.category in low_elasticity_categories:
            return 'low'  # Se necesitan descuentos grandes para cambiar demanda
        else:
            return 'medium'
    
    def _analyze_competition(self, product):
        """Analiza productos competidores"""
        try:
            # Buscar productos similares (misma categoría, precio similar)
            price_range_lower = product.price * Decimal('0.8')
            price_range_upper = product.price * Decimal('1.2')
            
            competitors = Product.objects.filter(
                category=product.category,
                price__gte=price_range_lower,
                price__lte=price_range_upper
            ).exclude(id=product.id)
            
            if not competitors.exists():
                return 'no_competitors'
            
            # Calcular precio promedio de competidores
            avg_competitor_price = competitors.aggregate(
                avg=Avg('price')
            )['avg'] or Decimal('0')
            
            # Comparar posición
            if product.price > avg_competitor_price * Decimal('1.1'):
                return 'above_market'  # Más caro que competencia
            elif product.price < avg_competitor_price * Decimal('0.9'):
                return 'below_market'  # Más barato que competencia
            else:
                return 'at_market'  # Precio competitivo
                
        except Exception as e:
            logger.error(f"Error analizando competencia: {str(e)}")
            return 'unknown'
    
    def _calculate_suggested_discount(self, historical, elasticity, competition, target_increase):
        """Calcula el descuento sugerido basado en múltiples factores"""
        base_discount = 15.0  # Base 15%
        
        # Ajustar por elasticidad
        if elasticity == 'high':
            elasticity_adjustment = -5.0  # Menor descuento necesario
        elif elasticity == 'low':
            elasticity_adjustment = 5.0  # Mayor descuento necesario
        else:
            elasticity_adjustment = 0.0
        
        # Ajustar por competencia
        if competition == 'above_market':
            competition_adjustment = 10.0  # Más descuento para competir
        elif competition == 'below_market':
            competition_adjustment = -5.0  # Ya somos competitivos
        else:
            competition_adjustment = 0.0
        
        # Ajustar por objetivo de ventas
        target_adjustment = (target_increase - 1.0) * 10.0
        
        # Calcular total
        total_discount = base_discount + elasticity_adjustment + competition_adjustment + target_adjustment
        
        # Limitar entre 10% y 70%
        total_discount = max(10.0, min(70.0, total_discount))
        
        return round(total_discount, 2)
    
    def _project_impact(self, product, discount_percentage, historical_data):
        """Proyecta el impacto del descuento"""
        # Calcular aumento de ventas estimado
        # Fórmula simplificada: sales_increase = discount * elasticity_factor
        
        elasticity_factor = 2.0  # Por cada 10% de descuento, 20% más ventas
        estimated_sales_increase = (discount_percentage / 10) * elasticity_factor
        
        # Calcular impacto en ingresos
        original_revenue = historical_data['total_revenue']
        new_sales_volume = historical_data['total_sales'] * (1 + estimated_sales_increase / 100)
        discount_decimal = Decimal(str(discount_percentage / 100))
        discounted_price = product.price * (Decimal('1') - discount_decimal)
        new_revenue = new_sales_volume * float(discounted_price)
        
        revenue_impact = new_revenue - original_revenue
        revenue_impact_percentage = (revenue_impact / original_revenue * 100) if original_revenue > 0 else 0
        
        # Calcular nivel de confianza
        confidence = 'high' if historical_data['has_sufficient_data'] else 'low'
        
        return {
            'sales_increase_percentage': round(estimated_sales_increase, 2),
            'revenue_impact': round(revenue_impact, 2),
            'revenue_impact_percentage': round(revenue_impact_percentage, 2),
            'confidence': confidence
        }
