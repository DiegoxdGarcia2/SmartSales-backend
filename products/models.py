from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField


class Category(models.Model):
    """
    Modelo para las categorías de productos.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Brand(models.Model):
    """
    Modelo para las marcas de productos.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    warranty_info = models.TextField(
        blank=True,
        null=True,
        verbose_name='Información de Garantía'
    )
    warranty_duration_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Duración de Garantía (meses)',
        help_text='Duración estándar de la garantía para esta marca en meses (ej: 12 para 1 año).'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Modelo para los productos del sistema.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Nombre',
        db_index=True  # Índice para búsquedas por nombre
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio',
        db_index=True  # Índice para ordenamiento/filtrado por precio
    )
    stock = models.IntegerField(
        default=0,
        verbose_name='Stock'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Categoría',
        db_index=True  # Índice para filtrado por categoría
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True,
        verbose_name='Marca',
        db_index=True  # Índice para filtrado por marca
    )
    image = CloudinaryField(
        blank=True,
        null=True,
        verbose_name='Imagen del Producto'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
        db_index=True  # Índice para ordenamiento por fecha
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'brand']),  # Índice compuesto para filtros combinados
            models.Index(fields=['-created_at', 'category']),  # Para listados por categoría ordenados
        ]
    
    def __str__(self):
        return self.name


class Review(models.Model):
    """
    Modelo para las reseñas de productos.
    """
    product = models.ForeignKey(
        Product,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name='Producto',
        db_index=True  # Índice para consultas por producto
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name='Usuario',
        db_index=True  # Índice para consultas por usuario
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Calificación (1-5)',
        db_index=True  # Índice para filtrado/ordenamiento por rating
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name='Comentario'
    )
    
    # Campos de Análisis de Sentimiento
    SENTIMENT_CHOICES = [
        ('POSITIVO', 'Positivo'),
        ('NEUTRO', 'Neutro'),
        ('NEGATIVO', 'Negativo'),
    ]
    
    sentiment = models.CharField(
        max_length=10,
        choices=SENTIMENT_CHOICES,
        blank=True,
        null=True,
        verbose_name='Sentimiento',
        db_index=True  # Índice para filtrado por sentimiento
    )
    sentiment_score = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Puntuación de Sentimiento',
        help_text='Puntuación compuesta VADER (-1 a 1)'
    )
    
    # Campos de Análisis Avanzado (Gemini AI)
    sentiment_confidence = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Confianza del Análisis',
        help_text='Nivel de confianza del análisis de sentimiento (0-1)',
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    sentiment_summary = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Resumen del Sentimiento',
        help_text='Breve resumen del sentimiento analizado por IA'
    )
    aspect_quality = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Aspecto: Calidad del Producto',
        help_text='Evaluación de calidad del producto (1-5)',
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    aspect_value = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Aspecto: Relación Precio-Valor',
        help_text='Evaluación de relación precio-calidad (1-5)',
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    aspect_delivery = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Aspecto: Experiencia de Entrega',
        help_text='Evaluación de la experiencia de entrega (1-5)',
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    keywords = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Palabras Clave',
        help_text='Palabras clave extraídas del comentario por IA'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
        db_index=True  # Índice para ordenamiento por fecha
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )

    class Meta:
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        # Evitar que un usuario deje más de una reseña por producto
        unique_together = ('product', 'user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),  # Para reviews de un producto ordenadas
            models.Index(fields=['product', 'rating']),  # Para filtrar por rating en un producto
        ]

    def __str__(self):
        return f'Reseña de {self.user.username} para {self.product.name} ({self.rating} estrellas)'
