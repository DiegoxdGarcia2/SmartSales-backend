"""
Comando Django para generar asociaciones de productos usando Market Basket Analysis.
Aplica el algoritmo Apriori para encontrar productos frecuentemente comprados juntos.
"""

import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd

from orders.models import Order, OrderItem
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


class Command(BaseCommand):
    help = 'Genera asociaciones de productos basadas en órdenes pagadas usando Market Basket Analysis'

    def handle(self, *args, **options):
        """
        Ejecuta el análisis de asociaciones de productos.
        """
        self.stdout.write('=' * 70)
        self.stdout.write('🛒 ANÁLISIS DE ASOCIACIONES DE PRODUCTOS (MARKET BASKET ANALYSIS)')
        self.stdout.write('=' * 70)
        
        # ==================== 1. CARGAR DATOS ====================
        self.stdout.write('\n📊 Cargando datos de órdenes pagadas...')
        
        # Obtener OrderItems de órdenes pagadas
        qs = OrderItem.objects.filter(
            order__payment_status='pagado'
        ).values('order_id', 'product_id')
        
        if not qs.exists():
            self.stdout.write(self.style.ERROR('❌ No hay suficientes datos de órdenes pagadas.'))
            return
        
        # Convertir a DataFrame
        df = pd.DataFrame(list(qs))
        n_orders = df['order_id'].nunique()
        n_items = len(df)
        
        self.stdout.write(f'✅ Cargados {n_items} items de {n_orders} órdenes.')
        
        # ==================== 2. PREPARAR TRANSACCIONES ====================
        self.stdout.write('\n🔧 Preparando transacciones para Apriori...')
        
        # Agrupar productos por orden en listas
        transactions = df.groupby('order_id')['product_id'].apply(list).tolist()
        
        # Eliminar órdenes con un solo producto (no forman pares)
        transactions = [t for t in transactions if len(t) > 1]
        
        if len(transactions) < 10:
            self.stdout.write(self.style.ERROR('❌ No hay suficientes órdenes con múltiples productos para análisis.'))
            self.stdout.write(f'   Se necesitan al menos 10 transacciones multi-item, se encontraron {len(transactions)}.')
            return
        
        self.stdout.write(f'✅ Procesando {len(transactions)} transacciones multi-item...')
        
        # ==================== 3. CODIFICAR TRANSACCIONES ====================
        self.stdout.write('\n🔢 Codificando transacciones (One-Hot Encoding)...')
        
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions)
        df_encoded = pd.DataFrame(te_ary, columns=te.columns_)
        
        self.stdout.write(f'✅ DataFrame codificado: {df_encoded.shape[0]} transacciones x {df_encoded.shape[1]} productos.')
        
        # ==================== 4. APLICAR ALGORITMO APRIORI ====================
        self.stdout.write('\n🔍 Calculando itemsets frecuentes (Apriori)...')
        
        # min_support: Frecuencia mínima para considerar un itemset
        # 0.005 = 0.5% de las transacciones deben contener el itemset
        # Usamos un threshold bajo para capturar incluso patrones débiles en datos sintéticos
        min_support = 0.005
        
        frequent_itemsets = apriori(
            df_encoded, 
            min_support=min_support, 
            use_colnames=True,
            max_len=None  # Buscar itemsets de cualquier tamaño
        )
        
        if frequent_itemsets.empty:
            self.stdout.write(self.style.WARNING(f'⚠️  No se encontraron itemsets frecuentes con soporte mínimo {min_support}.'))
            self.stdout.write('   Guardando archivo JSON vacío...')
            associations_dict = {}
        else:
            # Verificar si hay itemsets de tamaño 2+
            frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
            itemsets_by_size = frequent_itemsets.groupby('length').size()
            
            self.stdout.write(f'✅ Encontrados {len(frequent_itemsets)} itemsets frecuentes.')
            self.stdout.write(f'   Distribución por tamaño:')
            for size, count in itemsets_by_size.items():
                self.stdout.write(f'     - Tamaño {size}: {count} itemsets')
            
            # Filtrar itemsets de tamaño 2+ para generar reglas
            frequent_pairs = frequent_itemsets[frequent_itemsets['length'] >= 2]
            
            if frequent_pairs.empty:
                self.stdout.write(self.style.WARNING('⚠️  No se encontraron pares de productos (itemsets de tamaño 2+).'))
                self.stdout.write('   Los datos sintéticos no tienen suficiente co-ocurrencia de productos.')
                self.stdout.write('\n🔄 Generando asociaciones alternativas basadas en categorías...')
                
                # Estrategia alternativa: Productos de la misma categoría
                from products.models import Product
                
                products = Product.objects.select_related('category').all()
                category_dict = {}
                
                # Agrupar productos por categoría
                for product in products:
                    if product.category:
                        cat_id = product.category.id
                        if cat_id not in category_dict:
                            category_dict[cat_id] = []
                        category_dict[cat_id].append(product.id)
                
                # Crear asociaciones: cada producto recomienda otros de su categoría
                associations_dict = {}
                for cat_id, product_ids in category_dict.items():
                    if len(product_ids) > 1:  # Solo si hay más de 1 producto en la categoría
                        for prod_id in product_ids:
                            # Recomendar los demás productos de la categoría (excluir el mismo)
                            others = [p for p in product_ids if p != prod_id]
                            if others:
                                associations_dict[str(prod_id)] = others[:5]  # Limitar a 5 recomendaciones
                
                self.stdout.write(f'✅ Generadas {len(associations_dict)} asociaciones basadas en categorías.')
                associations_dict = {str(k): v for k, v in associations_dict.items()}
            else:
                # ==================== 5. GENERAR REGLAS DE ASOCIACIÓN ====================
                self.stdout.write('\n📋 Generando reglas de asociación...')
                
                # min_threshold (lift): Métrica para medir qué tan fuerte es la asociación
                # lift > 1 sugiere una asociación positiva
                # lift = 1.05 significa que es 5% más probable comprar B si ya compraste A
                # Usamos un threshold bajo para capturar incluso asociaciones débiles en datos sintéticos
                min_lift = 1.05
                
                rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
                
                if rules.empty:
                    self.stdout.write(self.style.WARNING(f'⚠️  No se generaron reglas de asociación con lift mínimo {min_lift}.'))
                    self.stdout.write('   Guardando archivo JSON vacío...')
                    associations_dict = {}
                else:
                    self.stdout.write(f'✅ Generadas {len(rules)} reglas iniciales.')
                    
                    # Filtrar y formatear reglas (solo pares simples A -> B)
                    rules['antecedent_len'] = rules['antecedents'].apply(lambda x: len(x))
                    rules['consequent_len'] = rules['consequents'].apply(lambda x: len(x))
                    
                    # Quedarnos solo con reglas simples 1 -> 1
                    simple_rules = rules[(rules['antecedent_len'] == 1) & (rules['consequent_len'] == 1)].copy()
                    
                    if simple_rules.empty:
                        self.stdout.write(self.style.WARNING('⚠️  No se encontraron reglas simples (1 -> 1).'))
                        associations_dict = {}
                    else:
                        self.stdout.write(f'✅ Filtradas {len(simple_rules)} reglas simples (1 -> 1).')
                        
                        # Convertir frozensets a IDs simples
                        simple_rules['antecedent_id'] = simple_rules['antecedents'].apply(lambda x: list(x)[0])
                        simple_rules['consequent_id'] = simple_rules['consequents'].apply(lambda x: list(x)[0])
                        
                        # Ordenar por lift (más relevante primero)
                        simple_rules = simple_rules.sort_values('lift', ascending=False)
                        
                        # Crear diccionario final {antecedent_id: [list of consequent_ids]}
                        associations_dict = simple_rules.groupby('antecedent_id')['consequent_id'].apply(list).to_dict()
                        
                        self.stdout.write(f'✅ Formateadas {len(associations_dict)} asociaciones A -> [B1, B2, ...].')
                        
                        # Mostrar ejemplo de las mejores asociaciones
                        self.stdout.write('\n📊 Muestra de las mejores asociaciones (top 5):')
                        for i, row in simple_rules.head(5).iterrows():
                            self.stdout.write(
                                f'   Producto {row["antecedent_id"]} -> {row["consequent_id"]} '
                                f'(lift: {row["lift"]:.2f}, conf: {row["confidence"]:.2%})'
                            )
        
        # ==================== 6. GUARDAR ASOCIACIONES ====================
        ASSOC_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
        ASSOC_PATH = os.path.join(ASSOC_DIR, 'product_associations.json')
        
        os.makedirs(ASSOC_DIR, exist_ok=True)
        
        self.stdout.write(f'\n💾 Guardando asociaciones en {ASSOC_PATH}...')
        
        # Convertir claves a string para JSON (si son enteros)
        associations_json = {str(k): v for k, v in associations_dict.items()}
        
        with open(ASSOC_PATH, 'w') as f:
            json.dump(associations_json, f, indent=4)
        
        self.stdout.write(self.style.SUCCESS('✅ Asociaciones guardadas exitosamente.'))
        
        # ==================== 7. RESUMEN FINAL ====================
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ ANÁLISIS DE ASOCIACIONES COMPLETADO'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'📊 Resumen:')
        self.stdout.write(f'  - Órdenes analizadas: {n_orders}')
        self.stdout.write(f'  - Items totales: {n_items}')
        self.stdout.write(f'  - Transacciones multi-item: {len(transactions)}')
        self.stdout.write(f'  - Productos únicos: {df_encoded.shape[1]}')
        self.stdout.write(f'  - Asociaciones generadas: {len(associations_dict)}')
        self.stdout.write(f'  - Archivo: {ASSOC_PATH}')
        self.stdout.write('=' * 70)
