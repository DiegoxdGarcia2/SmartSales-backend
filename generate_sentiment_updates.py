"""
Script para generar SQL UPDATE statements para actualizar sentimientos en producción.
SOLO actualiza los campos sentiment y sentiment_score, NO modifica ni borra otros datos.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from products.models import Review

print("=" * 80)
print("🔧 GENERANDO SQL UPDATES PARA SENTIMIENTOS")
print("=" * 80)

# Obtener todas las reseñas con sentimiento calculado
reviews = Review.objects.filter(sentiment__isnull=False).order_by('id')
total = reviews.count()

print(f"\n📊 Total de reseñas con sentimiento: {total}")
print(f"🔄 Generando archivo SQL...")

# Crear archivo SQL
output_file = 'update_sentiments_production.sql'

with open(output_file, 'w', encoding='utf-8') as f:
    # Header del archivo
    f.write("-- ============================================================================\n")
    f.write("-- ACTUALIZACIÓN DE SENTIMIENTOS EN PRODUCCIÓN\n")
    f.write("-- ============================================================================\n")
    f.write("-- Este script SOLO actualiza los campos sentiment y sentiment_score\n")
    f.write("-- NO modifica, borra ni altera otros datos (usuarios, productos, órdenes)\n")
    f.write(f"-- Total de reseñas a actualizar: {total}\n")
    f.write("-- Fecha de generación: 30 de octubre de 2025\n")
    f.write("-- ============================================================================\n\n")
    
    f.write("-- Iniciar transacción (puedes hacer ROLLBACK si algo sale mal)\n")
    f.write("BEGIN;\n\n")
    
    f.write("-- Estadísticas ANTES de actualizar\n")
    f.write("SELECT \n")
    f.write("    COUNT(*) as total_reviews,\n")
    f.write("    COUNT(sentiment) as reviews_con_sentiment,\n")
    f.write("    COUNT(*) - COUNT(sentiment) as reviews_sin_sentiment\n")
    f.write("FROM products_review;\n\n")
    
    # Generar UPDATEs
    f.write("-- ============================================================================\n")
    f.write("-- COMANDOS UPDATE (solo sentiment y sentiment_score)\n")
    f.write("-- ============================================================================\n\n")
    
    count = 0
    for review in reviews:
        # Escapar valores NULL o strings
        sentiment_value = f"'{review.sentiment}'" if review.sentiment else 'NULL'
        score_value = f"{review.sentiment_score}" if review.sentiment_score is not None else 'NULL'
        
        f.write(f"UPDATE products_review SET sentiment = {sentiment_value}, sentiment_score = {score_value} WHERE id = {review.id};\n")
        
        count += 1
        if count % 500 == 0:
            f.write(f"\n-- Progreso: {count}/{total} actualizadas\n\n")
    
    f.write("\n-- ============================================================================\n")
    f.write("-- Estadísticas DESPUÉS de actualizar\n")
    f.write("-- ============================================================================\n\n")
    f.write("SELECT \n")
    f.write("    COUNT(*) as total_reviews,\n")
    f.write("    COUNT(sentiment) as reviews_con_sentiment,\n")
    f.write("    COUNT(*) - COUNT(sentiment) as reviews_sin_sentiment,\n")
    f.write("    SUM(CASE WHEN sentiment = 'POSITIVO' THEN 1 ELSE 0 END) as positivas,\n")
    f.write("    SUM(CASE WHEN sentiment = 'NEUTRO' THEN 1 ELSE 0 END) as neutras,\n")
    f.write("    SUM(CASE WHEN sentiment = 'NEGATIVO' THEN 1 ELSE 0 END) as negativas\n")
    f.write("FROM products_review;\n\n")
    
    f.write("-- Si todo se ve bien, ejecuta: COMMIT;\n")
    f.write("-- Si algo salió mal, ejecuta: ROLLBACK;\n")
    f.write("COMMIT;\n")

print(f"\n✅ Archivo generado: {output_file}")
print(f"📝 Total de UPDATE statements: {count}")

# Estadísticas de distribución
positivas = Review.objects.filter(sentiment='POSITIVO').count()
neutras = Review.objects.filter(sentiment='NEUTRO').count()
negativas = Review.objects.filter(sentiment='NEGATIVO').count()

print(f"\n📈 Distribución de sentimientos:")
print(f"  😊 Positivas: {positivas} ({positivas/total*100:.1f}%)")
print(f"  😐 Neutras: {neutras} ({neutras/total*100:.1f}%)")
print(f"  😞 Negativas: {negativas} ({negativas/total*100:.1f}%)")

print("\n" + "=" * 80)
print("📋 INSTRUCCIONES PARA EJECUTAR EN RENDER:")
print("=" * 80)
print("1. Sube este archivo a tu repositorio (opcional) o cópialo")
print("2. En Render Dashboard → tu servicio → Shell")
print("3. Ejecuta: psql $DATABASE_URL")
print("4. Copia y pega el contenido del archivo SQL")
print("5. Si todo se ve bien, el COMMIT ya se ejecutará automáticamente")
print("6. Verifica con: SELECT COUNT(*), sentiment FROM products_review GROUP BY sentiment;")
print("=" * 80)
