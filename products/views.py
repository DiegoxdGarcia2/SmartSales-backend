import logging
from rest_framework import viewsets, permissions, serializers as drf_serializers
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Prefetch
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from .models import Category, Product, Brand, Review
from .serializers import CategorySerializer, ProductSerializer, BrandSerializer, ReviewSerializer
from .permissions import HasPurchasedProduct, IsReviewAuthorOrReadOnly
from .gemini_sentiment import analyze_review_sentiment_advanced, extract_basic_sentiment
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.core.management import call_command
from django.http import JsonResponse
from io import StringIO
import sys
from django.db import transaction

# Configurar logger
logger = logging.getLogger(__name__)


def analyze_review_sentiment(rating, comment):
    """
    Analiza el sentimiento de una reseña basándose en el rating y el comentario.
    
    Args:
        rating (int): Calificación numérica de 1 a 5
        comment (str): Comentario textual de la reseña
        
    Returns:
        tuple: (sentiment, score) donde sentiment es 'POSITIVO', 'NEUTRO' o 'NEGATIVO'
               y score es la puntuación compound de VADER (-1 a 1)
    """
    # Regla base: clasificar por rating
    if rating >= 4:
        sentiment = 'POSITIVO'
    elif rating == 3:
        sentiment = 'NEUTRO'
    else:
        sentiment = 'NEGATIVO'
    
    score = 0.0

    # Refinar análisis con el texto del comentario (si existe)
    if comment and comment.strip():
        try:
            analyzer = SentimentIntensityAnalyzer()
            # Analizar el texto del comentario
            vs = analyzer.polarity_scores(comment)
            score = vs['compound']  # Puntuación compuesta (-1 a 1)

            # Ajustar sentimiento si el comentario contradice el rating
            # Ejemplo: Rating 5 pero comentario muy negativo -> ajustar a NEUTRO
            if score > 0.05 and sentiment == 'NEGATIVO':
                # Comentario positivo pero rating bajo
                sentiment = 'NEUTRO'
                logger.info(f"Ajuste: Rating bajo ({rating}) pero comentario positivo (score: {score:.2f})")
            elif score < -0.05 and sentiment == 'POSITIVO':
                # Comentario negativo pero rating alto
                sentiment = 'NEUTRO'
                logger.info(f"Ajuste: Rating alto ({rating}) pero comentario negativo (score: {score:.2f})")
            elif score > 0.05:
                sentiment = 'POSITIVO'
            elif score < -0.05:
                sentiment = 'NEGATIVO'
                
        except Exception as e:
            # Si falla el análisis VADER, mantener el sentimiento basado en rating
            logger.error(f"Error en análisis de sentimiento VADER: {e}", exc_info=True)
            # score se mantiene en 0.0

    return sentiment, score


@api_view(['POST'])
@permission_classes([IsAdminUser])
def analyze_old_reviews(request):
    """
    Endpoint temporal para analizar reseñas antiguas con Gemini AI.
    Solo accesible para administradores.
    
    POST /api/analyze-old-reviews/
    Parámetros opcionales:
    - dry_run: true/false (default: true)
    - batch_size: número de reseñas a procesar (default: 10)
    - max_reviews: límite máximo de reseñas a procesar (default: 100)
    """
    try:
        # Parámetros de la petición
        dry_run = request.data.get('dry_run', True)
        batch_size = int(request.data.get('batch_size', 10))
        max_reviews = int(request.data.get('max_reviews', 100))
        
        # Validar parámetros
        if batch_size < 1 or batch_size > 50:
            return Response(
                {'error': 'batch_size debe estar entre 1 y 50'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if max_reviews < 1 or max_reviews > 1000:
            return Response(
                {'error': 'max_reviews debe estar entre 1 y 1000'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener reseñas sin análisis
        reviews_to_analyze = Review.objects.filter(
            sentiment_confidence__isnull=True
        ).select_related('product', 'user')[:max_reviews]
        
        total_reviews = reviews_to_analyze.count()
        
        if total_reviews == 0:
            return Response({
                'message': 'No hay reseñas pendientes de análisis',
                'total_processed': 0,
                'dry_run': dry_run
            })
        
        processed = 0
        errors = 0
        results = []
        
        logger.info(f"🔄 Iniciando análisis de {total_reviews} reseñas antiguas (dry_run={dry_run})")
        
        for review in reviews_to_analyze:
            try:
                # Analizar con Gemini AI
                analysis = analyze_review_sentiment_advanced(
                    rating=review.rating,
                    comment=review.comment or '',
                    product_name=review.product.name
                )
                
                # Extraer datos
                sentiment, sentiment_score = extract_basic_sentiment(analysis)
                sentiment_confidence = analysis.get('confidence', 0.8)
                sentiment_summary = analysis.get('summary', '')
                aspects = analysis.get('aspects', {})
                keywords = analysis.get('keywords', [])
                
                review_data = {
                    'id': review.id,
                    'product': review.product.name,
                    'rating': review.rating,
                    'sentiment': sentiment,
                    'confidence': sentiment_confidence,
                    'summary': sentiment_summary
                }
                
                if not dry_run:
                    # Actualizar la reseña en la base de datos
                    with transaction.atomic():
                        review.sentiment = sentiment
                        review.sentiment_score = sentiment_score
                        review.sentiment_confidence = sentiment_confidence
                        review.sentiment_summary = sentiment_summary
                        review.aspect_quality = aspects.get('product_quality')
                        review.aspect_value = aspects.get('value_for_money')
                        review.aspect_delivery = aspects.get('delivery_experience')
                        review.keywords = keywords if keywords else None
                        review.save(update_fields=[
                            'sentiment', 'sentiment_score', 'sentiment_confidence',
                            'sentiment_summary', 'aspect_quality', 'aspect_value',
                            'aspect_delivery', 'keywords'
                        ])
                    
                    logger.info(f"✅ Reseña {review.id} actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                else:
                    logger.info(f"🔍 [DRY RUN] Reseña {review.id} sería actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                
                results.append(review_data)
                processed += 1
                
                # Procesar en lotes para no sobrecargar
                if processed % batch_size == 0:
                    logger.info(f"📊 Progreso: {processed}/{total_reviews} reseñas procesadas")
                
            except Exception as e:
                errors += 1
                logger.error(f"❌ Error procesando reseña {review.id}: {e}")
                results.append({
                    'id': review.id,
                    'error': str(e)
                })
        
        # Respuesta final
        response_data = {
            'message': f'Análisis completado. {"(DRY RUN)" if dry_run else ""}',
            'total_reviews': total_reviews,
            'processed': processed,
            'errors': errors,
            'dry_run': dry_run,
            'results': results[:10]  # Solo mostrar las primeras 10 para no sobrecargar
        }
        
        logger.info(f"🎉 Análisis completado: {processed} procesadas, {errors} errores")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint de análisis: {e}", exc_info=True)
        return Response(
            {'error': f'Error interno del servidor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado: Admin puede hacer todo, otros solo pueden leer.
    """
    def has_permission(self, request, view):
        # Permitir peticiones de lectura (GET, HEAD, OPTIONS) a todos
        if request.method in permissions.SAFE_METHODS:
            return True
        # Permitir escritura solo a administradores
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las categorías de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Category.objects.prefetch_related('products').all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class BrandViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las marcas de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Brand.objects.prefetch_related('products').all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    Optimizado con select_related y prefetch_related para reducir queries
    """
    queryset = Product.objects.select_related('category', 'brand').prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user'))
    ).all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """
        Opcionalmente filtra productos por categoría o marca usando query params.
        Ejemplo: /api/products/?category=1&brand=2
        Optimizado con select_related para evitar N+1 queries
        """
        queryset = Product.objects.select_related('category', 'brand').prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user'))
        )
        category_id = self.request.query_params.get('category', None)
        brand_id = self.request.query_params.get('brand', None)
        
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        
        if brand_id is not None:
            queryset = queryset.filter(brand_id=brand_id)
        
        return queryset


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las reseñas de productos.
    GET: Todos pueden ver
    POST: Usuario autenticado que haya comprado el producto
    PUT, PATCH, DELETE: Solo el autor de la reseña
    """
    queryset = Review.objects.all().select_related('user', 'product')
    serializer_class = ReviewSerializer

    def get_queryset(self):
        """
        Opcional: Filtrar reseñas por producto si se pasa ?product_id=X en la URL
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        """
        Asigna el usuario automáticamente, valida que haya comprado el producto
        y analiza automáticamente el sentimiento de la reseña con Gemini AI.
        """
        user = self.request.user
        product = serializer.validated_data['product']  # Obtener instancia del producto

        # 1. Validar si el usuario compró el producto
        if not HasPurchasedProduct.check_purchase(user, product.id):
            raise PermissionDenied(HasPurchasedProduct.message)

        # 2. Validar si ya existe una reseña (Hacerlo ANTES de intentar guardar)
        #    Es buena práctica, aunque el unique_together lo asegura en DB.
        if Review.objects.filter(product=product, user=user).exists():
            # Usar ValidationError que el frontend puede interpretar mejor como 400
            raise drf_serializers.ValidationError({'detail': 'Ya has dejado una reseña para este producto.'})

        # 3. Analizar sentimiento de la reseña con Gemini AI (análisis avanzado)
        rating = serializer.validated_data['rating']
        comment = serializer.validated_data.get('comment', '')
        
        try:
            # Análisis avanzado con Gemini
            analysis = analyze_review_sentiment_advanced(
                rating=rating, 
                comment=comment,
                product_name=product.name
            )
            
            # Extraer sentimiento básico para compatibilidad
            sentiment, sentiment_score = extract_basic_sentiment(analysis)
            
            # Extraer datos avanzados
            sentiment_confidence = analysis.get('confidence', 0.8)
            sentiment_summary = analysis.get('summary', '')
            aspects = analysis.get('aspects', {})
            keywords = analysis.get('keywords', [])
            
            logger.info(
                f"✨ Nueva reseña analizada con Gemini - "
                f"Producto: {product.id}, Rating: {rating}, "
                f"Sentimiento: {sentiment} (confianza: {sentiment_confidence:.2f})"
            )
            
        except Exception as e:
            # Fallback a análisis simple si Gemini falla
            logger.warning(f"⚠️ Gemini falló, usando análisis simple: {e}")
            sentiment, sentiment_score = analyze_review_sentiment(rating, comment)
            sentiment_confidence = 0.7
            sentiment_summary = f"Análisis basado en rating {rating}/5"
            aspects = {}
            keywords = []

        # 4. Intentar guardar con usuario y análisis de sentimiento completo
        try:
            serializer.save(
                user=user,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                sentiment_confidence=sentiment_confidence,
                sentiment_summary=sentiment_summary,
                aspect_quality=aspects.get('product_quality'),
                aspect_value=aspects.get('value_for_money'),
                aspect_delivery=aspects.get('delivery_experience'),
                keywords=keywords if keywords else None
            )
        except IntegrityError:
            # Esto captura el error si la validación anterior fallara por alguna razón (ej. condición de carrera)
            raise drf_serializers.ValidationError({'detail': 'Error de integridad, posible reseña duplicada.'})
        except Exception as e:
            # Capturar otros posibles errores durante el save
            logger.error(f"Error al guardar reseña: {e}", exc_info=True)
            raise drf_serializers.ValidationError({'detail': f'Ocurrió un error inesperado al guardar la reseña: {str(e)}'})

    def get_permissions(self):
        """
        Asigna permisos según la acción
        """
        # GET (list, retrieve): Cualquiera puede leer
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        # POST (create): Usuario autenticado (validación de compra en perform_create)
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        # PUT, PATCH, DELETE: Solo el autor de la reseña
        else:
            permission_classes = [IsReviewAuthorOrReadOnly]
        return [permission() for permission in permission_classes]


@api_view(['POST'])
@permission_classes([IsAdminUser])
def analyze_old_reviews(request):
    """
    Endpoint temporal para analizar reseñas antiguas con Gemini AI.
    Solo accesible para administradores.
    
    POST /api/analyze-old-reviews/
    Parámetros opcionales:
    - dry_run: true/false (default: true)
    - batch_size: número de reseñas a procesar (default: 10)
    - max_reviews: límite máximo de reseñas a procesar (default: 100)
    """
    try:
        # Parámetros de la petición
        dry_run = request.data.get('dry_run', True)
        batch_size = int(request.data.get('batch_size', 10))
        max_reviews = int(request.data.get('max_reviews', 100))
        
        # Validar parámetros
        if batch_size < 1 or batch_size > 50:
            return Response(
                {'error': 'batch_size debe estar entre 1 y 50'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if max_reviews < 1 or max_reviews > 1000:
            return Response(
                {'error': 'max_reviews debe estar entre 1 y 1000'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener reseñas sin análisis
        reviews_to_analyze = Review.objects.filter(
            sentiment_confidence__isnull=True
        ).select_related('product', 'user')[:max_reviews]
        
        total_reviews = reviews_to_analyze.count()
        
        if total_reviews == 0:
            return Response({
                'message': 'No hay reseñas pendientes de análisis',
                'total_processed': 0,
                'dry_run': dry_run
            })
        
        processed = 0
        errors = 0
        results = []
        
        logger.info(f"🔄 Iniciando análisis de {total_reviews} reseñas antiguas (dry_run={dry_run})")
        
        for review in reviews_to_analyze:
            try:
                # Analizar con Gemini AI
                analysis = analyze_review_sentiment_advanced(
                    rating=review.rating,
                    comment=review.comment or '',
                    product_name=review.product.name
                )
                
                # Extraer datos
                sentiment, sentiment_score = extract_basic_sentiment(analysis)
                sentiment_confidence = analysis.get('confidence', 0.8)
                sentiment_summary = analysis.get('summary', '')
                aspects = analysis.get('aspects', {})
                keywords = analysis.get('keywords', [])
                
                review_data = {
                    'id': review.id,
                    'product': review.product.name,
                    'rating': review.rating,
                    'sentiment': sentiment,
                    'confidence': sentiment_confidence,
                    'summary': sentiment_summary
                }
                
                if not dry_run:
                    # Actualizar la reseña en la base de datos
                    with transaction.atomic():
                        review.sentiment = sentiment
                        review.sentiment_score = sentiment_score
                        review.sentiment_confidence = sentiment_confidence
                        review.sentiment_summary = sentiment_summary
                        review.aspect_quality = aspects.get('product_quality')
                        review.aspect_value = aspects.get('value_for_money')
                        review.aspect_delivery = aspects.get('delivery_experience')
                        review.keywords = keywords if keywords else None
                        review.save(update_fields=[
                            'sentiment', 'sentiment_score', 'sentiment_confidence',
                            'sentiment_summary', 'aspect_quality', 'aspect_value',
                            'aspect_delivery', 'keywords'
                        ])
                    
                    logger.info(f"✅ Reseña {review.id} actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                else:
                    logger.info(f"🔍 [DRY RUN] Reseña {review.id} sería actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                
                results.append(review_data)
                processed += 1
                
                # Procesar en lotes para no sobrecargar
                if processed % batch_size == 0:
                    logger.info(f"📊 Progreso: {processed}/{total_reviews} reseñas procesadas")
                
            except Exception as e:
                errors += 1
                logger.error(f"❌ Error procesando reseña {review.id}: {e}")
                results.append({
                    'id': review.id,
                    'error': str(e)
                })
        
        # Respuesta final
        response_data = {
            'message': f'Análisis completado. {"(DRY RUN)" if dry_run else ""}',
            'total_reviews': total_reviews,
            'processed': processed,
            'errors': errors,
            'dry_run': dry_run,
            'results': results[:10]  # Solo mostrar las primeras 10 para no sobrecargar
        }
        
        logger.info(f"🎉 Análisis completado: {processed} procesadas, {errors} errores")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint de análisis: {e}", exc_info=True)
        return Response(
            {'error': f'Error interno del servidor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado: Admin puede hacer todo, otros solo pueden leer.
    """
    def has_permission(self, request, view):
        # Permitir peticiones de lectura (GET, HEAD, OPTIONS) a todos
        if request.method in permissions.SAFE_METHODS:
            return True
        # Permitir escritura solo a administradores
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las categorías de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Category.objects.prefetch_related('products').all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class BrandViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las marcas de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Brand.objects.prefetch_related('products').all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    Optimizado con select_related y prefetch_related para reducir queries
    """
    queryset = Product.objects.select_related('category', 'brand').prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user'))
    ).all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """
        Opcionalmente filtra productos por categoría o marca usando query params.
        Ejemplo: /api/products/?category=1&brand=2
        Optimizado con select_related para evitar N+1 queries
        """
        queryset = Product.objects.select_related('category', 'brand').prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user'))
        )
        category_id = self.request.query_params.get('category', None)
        brand_id = self.request.query_params.get('brand', None)
        
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        
        if brand_id is not None:
            queryset = queryset.filter(brand_id=brand_id)
        
        return queryset


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las reseñas de productos.
    GET: Todos pueden ver
    POST: Usuario autenticado que haya comprado el producto
    PUT, PATCH, DELETE: Solo el autor de la reseña
    """
    queryset = Review.objects.all().select_related('user', 'product')
    serializer_class = ReviewSerializer

    def get_queryset(self):
        """
        Opcional: Filtrar reseñas por producto si se pasa ?product_id=X en la URL
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        """
        Asigna el usuario automáticamente, valida que haya comprado el producto
        y analiza automáticamente el sentimiento de la reseña con Gemini AI.
        """
        user = self.request.user
        product = serializer.validated_data['product']  # Obtener instancia del producto

        # 1. Validar si el usuario compró el producto
        if not HasPurchasedProduct.check_purchase(user, product.id):
            raise PermissionDenied(HasPurchasedProduct.message)

        # 2. Validar si ya existe una reseña (Hacerlo ANTES de intentar guardar)
        #    Es buena práctica, aunque el unique_together lo asegura en DB.
        if Review.objects.filter(product=product, user=user).exists():
            # Usar ValidationError que el frontend puede interpretar mejor como 400
            raise drf_serializers.ValidationError({'detail': 'Ya has dejado una reseña para este producto.'})

        # 3. Analizar sentimiento de la reseña con Gemini AI (análisis avanzado)
        rating = serializer.validated_data['rating']
        comment = serializer.validated_data.get('comment', '')
        
        try:
            # Análisis avanzado con Gemini
            analysis = analyze_review_sentiment_advanced(
                rating=rating, 
                comment=comment,
                product_name=product.name
            )
            
            # Extraer sentimiento básico para compatibilidad
            sentiment, sentiment_score = extract_basic_sentiment(analysis)
            
            # Extraer datos avanzados
            sentiment_confidence = analysis.get('confidence', 0.8)
            sentiment_summary = analysis.get('summary', '')
            aspects = analysis.get('aspects', {})
            keywords = analysis.get('keywords', [])
            
            logger.info(
                f"✨ Nueva reseña analizada con Gemini - "
                f"Producto: {product.id}, Rating: {rating}, "
                f"Sentimiento: {sentiment} (confianza: {sentiment_confidence:.2f})"
            )
            
        except Exception as e:
            # Fallback a análisis simple si Gemini falla
            logger.warning(f"⚠️ Gemini falló, usando análisis simple: {e}")
            sentiment, sentiment_score = analyze_review_sentiment(rating, comment)
            sentiment_confidence = 0.7
            sentiment_summary = f"Análisis basado en rating {rating}/5"
            aspects = {}
            keywords = []

        # 4. Intentar guardar con usuario y análisis de sentimiento completo
        try:
            serializer.save(
                user=user,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                sentiment_confidence=sentiment_confidence,
                sentiment_summary=sentiment_summary,
                aspect_quality=aspects.get('product_quality'),
                aspect_value=aspects.get('value_for_money'),
                aspect_delivery=aspects.get('delivery_experience'),
                keywords=keywords if keywords else None
            )
        except IntegrityError:
            # Esto captura el error si la validación anterior fallara por alguna razón (ej. condición de carrera)
            raise drf_serializers.ValidationError({'detail': 'Error de integridad, posible reseña duplicada.'})
        except Exception as e:
            # Capturar otros posibles errores durante el save
            logger.error(f"Error al guardar reseña: {e}", exc_info=True)
            raise drf_serializers.ValidationError({'detail': f'Ocurrió un error inesperado al guardar la reseña: {str(e)}'})

    def get_permissions(self):
        """
        Asigna permisos según la acción
        """
        # GET (list, retrieve): Cualquiera puede leer
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        # POST (create): Usuario autenticado (validación de compra en perform_create)
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        # PUT, PATCH, DELETE: Solo el autor de la reseña
        else:
            permission_classes = [IsReviewAuthorOrReadOnly]
        return [permission() for permission in permission_classes]


@api_view(['POST'])
@permission_classes([IsAdminUser])
def analyze_old_reviews(request):
    """
    Endpoint temporal para analizar reseñas antiguas con Gemini AI.
    Solo accesible para administradores.
    
    POST /api/analyze-old-reviews/
    Parámetros opcionales:
    - dry_run: true/false (default: true)
    - batch_size: número de reseñas a procesar (default: 10)
    - max_reviews: límite máximo de reseñas a procesar (default: 100)
    """
    try:
        # Parámetros de la petición
        dry_run = request.data.get('dry_run', True)
        batch_size = int(request.data.get('batch_size', 10))
        max_reviews = int(request.data.get('max_reviews', 100))
        
        # Validar parámetros
        if batch_size < 1 or batch_size > 50:
            return Response(
                {'error': 'batch_size debe estar entre 1 y 50'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if max_reviews < 1 or max_reviews > 1000:
            return Response(
                {'error': 'max_reviews debe estar entre 1 y 1000'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener reseñas sin análisis
        reviews_to_analyze = Review.objects.filter(
            sentiment_confidence__isnull=True
        ).select_related('product', 'user')[:max_reviews]
        
        total_reviews = reviews_to_analyze.count()
        
        if total_reviews == 0:
            return Response({
                'message': 'No hay reseñas pendientes de análisis',
                'total_processed': 0,
                'dry_run': dry_run
            })
        
        processed = 0
        errors = 0
        results = []
        
        logger.info(f"🔄 Iniciando análisis de {total_reviews} reseñas antiguas (dry_run={dry_run})")
        
        for review in reviews_to_analyze:
            try:
                # Analizar con Gemini AI
                analysis = analyze_review_sentiment_advanced(
                    rating=review.rating,
                    comment=review.comment or '',
                    product_name=review.product.name
                )
                
                # Extraer datos
                sentiment, sentiment_score = extract_basic_sentiment(analysis)
                sentiment_confidence = analysis.get('confidence', 0.8)
                sentiment_summary = analysis.get('summary', '')
                aspects = analysis.get('aspects', {})
                keywords = analysis.get('keywords', [])
                
                review_data = {
                    'id': review.id,
                    'product': review.product.name,
                    'rating': review.rating,
                    'sentiment': sentiment,
                    'confidence': sentiment_confidence,
                    'summary': sentiment_summary
                }
                
                if not dry_run:
                    # Actualizar la reseña en la base de datos
                    with transaction.atomic():
                        review.sentiment = sentiment
                        review.sentiment_score = sentiment_score
                        review.sentiment_confidence = sentiment_confidence
                        review.sentiment_summary = sentiment_summary
                        review.aspect_quality = aspects.get('product_quality')
                        review.aspect_value = aspects.get('value_for_money')
                        review.aspect_delivery = aspects.get('delivery_experience')
                        review.keywords = keywords if keywords else None
                        review.save(update_fields=[
                            'sentiment', 'sentiment_score', 'sentiment_confidence',
                            'sentiment_summary', 'aspect_quality', 'aspect_value',
                            'aspect_delivery', 'keywords'
                        ])
                    
                    logger.info(f"✅ Reseña {review.id} actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                else:
                    logger.info(f"🔍 [DRY RUN] Reseña {review.id} sería actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                
                results.append(review_data)
                processed += 1
                
                # Procesar en lotes para no sobrecargar
                if processed % batch_size == 0:
                    logger.info(f"📊 Progreso: {processed}/{total_reviews} reseñas procesadas")
                
            except Exception as e:
                errors += 1
                logger.error(f"❌ Error procesando reseña {review.id}: {e}")
                results.append({
                    'id': review.id,
                    'error': str(e)
                })
        
        # Respuesta final
        response_data = {
            'message': f'Análisis completado. {"(DRY RUN)" if dry_run else ""}',
            'total_reviews': total_reviews,
            'processed': processed,
            'errors': errors,
            'dry_run': dry_run,
            'results': results[:10]  # Solo mostrar las primeras 10 para no sobrecargar
        }
        
        logger.info(f"🎉 Análisis completado: {processed} procesadas, {errors} errores")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint de análisis: {e}", exc_info=True)
        return Response(
            {'error': f'Error interno del servidor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado: Admin puede hacer todo, otros solo pueden leer.
    """
    def has_permission(self, request, view):
        # Permitir peticiones de lectura (GET, HEAD, OPTIONS) a todos
        if request.method in permissions.SAFE_METHODS:
            return True
        # Permitir escritura solo a administradores
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las categorías de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Category.objects.prefetch_related('products').all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class BrandViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las marcas de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Brand.objects.prefetch_related('products').all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    Optimizado con select_related y prefetch_related para reducir queries
    """
    queryset = Product.objects.select_related('category', 'brand').prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user'))
    ).all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """
        Opcionalmente filtra productos por categoría o marca usando query params.
        Ejemplo: /api/products/?category=1&brand=2
        Optimizado con select_related para evitar N+1 queries
        """
        queryset = Product.objects.select_related('category', 'brand').prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user'))
        )
        category_id = self.request.query_params.get('category', None)
        brand_id = self.request.query_params.get('brand', None)
        
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        
        if brand_id is not None:
            queryset = queryset.filter(brand_id=brand_id)
        
        return queryset


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las reseñas de productos.
    GET: Todos pueden ver
    POST: Usuario autenticado que haya comprado el producto
    PUT, PATCH, DELETE: Solo el autor de la reseña
    """
    queryset = Review.objects.all().select_related('user', 'product')
    serializer_class = ReviewSerializer

    def get_queryset(self):
        """
        Opcional: Filtrar reseñas por producto si se pasa ?product_id=X en la URL
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        """
        Asigna el usuario automáticamente, valida que haya comprado el producto
        y analiza automáticamente el sentimiento de la reseña con Gemini AI.
        """
        user = self.request.user
        product = serializer.validated_data['product']  # Obtener instancia del producto

        # 1. Validar si el usuario compró el producto
        if not HasPurchasedProduct.check_purchase(user, product.id):
            raise PermissionDenied(HasPurchasedProduct.message)

        # 2. Validar si ya existe una reseña (Hacerlo ANTES de intentar guardar)
        #    Es buena práctica, aunque el unique_together lo asegura en DB.
        if Review.objects.filter(product=product, user=user).exists():
            # Usar ValidationError que el frontend puede interpretar mejor como 400
            raise drf_serializers.ValidationError({'detail': 'Ya has dejado una reseña para este producto.'})

        # 3. Analizar sentimiento de la reseña con Gemini AI (análisis avanzado)
        rating = serializer.validated_data['rating']
        comment = serializer.validated_data.get('comment', '')
        
        try:
            # Análisis avanzado con Gemini
            analysis = analyze_review_sentiment_advanced(
                rating=rating, 
                comment=comment,
                product_name=product.name
            )
            
            # Extraer sentimiento básico para compatibilidad
            sentiment, sentiment_score = extract_basic_sentiment(analysis)
            
            # Extraer datos avanzados
            sentiment_confidence = analysis.get('confidence', 0.8)
            sentiment_summary = analysis.get('summary', '')
            aspects = analysis.get('aspects', {})
            keywords = analysis.get('keywords', [])
            
            logger.info(
                f"✨ Nueva reseña analizada con Gemini - "
                f"Producto: {product.id}, Rating: {rating}, "
                f"Sentimiento: {sentiment} (confianza: {sentiment_confidence:.2f})"
            )
            
        except Exception as e:
            # Fallback a análisis simple si Gemini falla
            logger.warning(f"⚠️ Gemini falló, usando análisis simple: {e}")
            sentiment, sentiment_score = analyze_review_sentiment(rating, comment)
            sentiment_confidence = 0.7
            sentiment_summary = f"Análisis basado en rating {rating}/5"
            aspects = {}
            keywords = []

        # 4. Intentar guardar con usuario y análisis de sentimiento completo
        try:
            serializer.save(
                user=user,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                sentiment_confidence=sentiment_confidence,
                sentiment_summary=sentiment_summary,
                aspect_quality=aspects.get('product_quality'),
                aspect_value=aspects.get('value_for_money'),
                aspect_delivery=aspects.get('delivery_experience'),
                keywords=keywords if keywords else None
            )
        except IntegrityError:
            # Esto captura el error si la validación anterior fallara por alguna razón (ej. condición de carrera)
            raise drf_serializers.ValidationError({'detail': 'Error de integridad, posible reseña duplicada.'})
        except Exception as e:
            # Capturar otros posibles errores durante el save
            logger.error(f"Error al guardar reseña: {e}", exc_info=True)
            raise drf_serializers.ValidationError({'detail': f'Ocurrió un error inesperado al guardar la reseña: {str(e)}'})

    def get_permissions(self):
        """
        Asigna permisos según la acción
        """
        # GET (list, retrieve): Cualquiera puede leer
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        # POST (create): Usuario autenticado (validación de compra en perform_create)
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        # PUT, PATCH, DELETE: Solo el autor de la reseña
        else:
            permission_classes = [IsReviewAuthorOrReadOnly]
        return [permission() for permission in permission_classes]


@api_view(['POST'])
@permission_classes([IsAdminUser])
def analyze_old_reviews(request):
    """
    Endpoint temporal para analizar reseñas antiguas con Gemini AI.
    Solo accesible para administradores.
    
    POST /api/analyze-old-reviews/
    Parámetros opcionales:
    - dry_run: true/false (default: true)
    - batch_size: número de reseñas a procesar (default: 10)
    - max_reviews: límite máximo de reseñas a procesar (default: 100)
    """
    try:
        # Parámetros de la petición
        dry_run = request.data.get('dry_run', True)
        batch_size = int(request.data.get('batch_size', 10))
        max_reviews = int(request.data.get('max_reviews', 100))
        
        # Validar parámetros
        if batch_size < 1 or batch_size > 50:
            return Response(
                {'error': 'batch_size debe estar entre 1 y 50'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if max_reviews < 1 or max_reviews > 1000:
            return Response(
                {'error': 'max_reviews debe estar entre 1 y 1000'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener reseñas sin análisis
        reviews_to_analyze = Review.objects.filter(
            sentiment_confidence__isnull=True
        ).select_related('product', 'user')[:max_reviews]
        
        total_reviews = reviews_to_analyze.count()
        
        if total_reviews == 0:
            return Response({
                'message': 'No hay reseñas pendientes de análisis',
                'total_processed': 0,
                'dry_run': dry_run
            })
        
        processed = 0
        errors = 0
        results = []
        
        logger.info(f"🔄 Iniciando análisis de {total_reviews} reseñas antiguas (dry_run={dry_run})")
        
        for review in reviews_to_analyze:
            try:
                # Analizar con Gemini AI
                analysis = analyze_review_sentiment_advanced(
                    rating=review.rating,
                    comment=review.comment or '',
                    product_name=review.product.name
                )
                
                # Extraer datos
                sentiment, sentiment_score = extract_basic_sentiment(analysis)
                sentiment_confidence = analysis.get('confidence', 0.8)
                sentiment_summary = analysis.get('summary', '')
                aspects = analysis.get('aspects', {})
                keywords = analysis.get('keywords', [])
                
                review_data = {
                    'id': review.id,
                    'product': review.product.name,
                    'rating': review.rating,
                    'sentiment': sentiment,
                    'confidence': sentiment_confidence,
                    'summary': sentiment_summary
                }
                
                if not dry_run:
                    # Actualizar la reseña en la base de datos
                    with transaction.atomic():
                        review.sentiment = sentiment
                        review.sentiment_score = sentiment_score
                        review.sentiment_confidence = sentiment_confidence
                        review.sentiment_summary = sentiment_summary
                        review.aspect_quality = aspects.get('product_quality')
                        review.aspect_value = aspects.get('value_for_money')
                        review.aspect_delivery = aspects.get('delivery_experience')
                        review.keywords = keywords if keywords else None
                        review.save(update_fields=[
                            'sentiment', 'sentiment_score', 'sentiment_confidence',
                            'sentiment_summary', 'aspect_quality', 'aspect_value',
                            'aspect_delivery', 'keywords'
                        ])
                    
                    logger.info(f"✅ Reseña {review.id} actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                else:
                    logger.info(f"🔍 [DRY RUN] Reseña {review.id} sería actualizada: {sentiment} (confianza: {sentiment_confidence:.2f})")
                
                results.append(review_data)
                processed += 1
                
                # Procesar en lotes para no sobrecargar
                if processed % batch_size == 0:
                    logger.info(f"📊 Progreso: {processed}/{total_reviews} reseñas procesadas")
                
            except Exception as e:
                errors += 1
                logger.error(f"❌ Error procesando reseña {review.id}: {e}")
                results.append({
                    'id': review.id,
                    'error': str(e)
                })
        
        # Respuesta final
        response_data = {
            'message': f'Análisis completado. {"(DRY RUN)" if dry_run else ""}',
            'total_reviews': total_reviews,
            'processed': processed,
            'errors': errors,
            'dry_run': dry_run,
            'results': results[:10]  # Solo mostrar las primeras 10 para no sobrecargar
        }
        
        logger.info(f"🎉 Análisis completado: {processed} procesadas, {errors} errores")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint de análisis: {e}", exc_info=True)
        return Response(
            {'error': f'Error interno del servidor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
