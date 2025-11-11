# 🧪 GUÍA DE TESTING COMPLETO - SmartSales Backend

## 🎯 Objetivo

Esta guía te ayudará a verificar que todos los sistemas (Notificaciones + Ofertas + ML) funcionen correctamente antes del deploy.

---

## ⚙️ Pre-requisitos

1. ✅ Servidor Django corriendo: `python manage.py runserver`
2. ✅ Migraciones aplicadas
3. ✅ Usuario admin creado
4. ✅ Firebase configurado (smartsales-firebase-key.json)
5. ✅ Algunos productos existentes en la BD

---

## 📋 Checklist Rápido (5 minutos)

### 1. Verificar Sistema sin Errores

```bash
python manage.py check
```

**Esperado:** `System check identified no issues (0 silenced).`

---

### 2. Verificar Migraciones

```bash
python manage.py showmigrations
```

**Esperado:**
```
notifications
 [X] 0001_initial
offers
 [X] 0001_initial
```

---

### 3. Verificar Firebase

```bash
python manage.py shell
```

```python
import firebase_admin
app = firebase_admin.get_app()
print("✅ Firebase inicializado:", app.project_id)
exit()
```

**Esperado:** `✅ Firebase inicializado: smartsales-notifications`

---

### 4. Verificar Modelos

```bash
python manage.py shell
```

```python
from notifications.models import Notification
from offers.models import Offer
print("✅ Notificaciones:", Notification.objects.count())
print("✅ Ofertas:", Offer.objects.count())
exit()
```

---

## 🧪 Testing Automatizado

### Test 1: Sistema de Notificaciones

```bash
python test_notifications_api.py
```

**Pruebas incluidas:**
1. Autenticación
2. Listar notificaciones
3. Crear notificación de prueba
4. Marcar como leída
5. Obtener contador no leídas
6. Marcar todas como leídas
7. Obtener preferencias
8. Actualizar preferencias
9. Registrar dispositivo FCM
10. Listar dispositivos
11. Desactivar dispositivo
12. Estadísticas

**Resultado esperado:**
```
📈 RESUMEN DE PRUEBAS
Total de pruebas: 12
✅ Exitosas: 12
❌ Fallidas: 0
📊 Tasa de éxito: 100.0%
```

---

### Test 2: Sistema de Ofertas

```bash
python test_offers_api.py
```

**Pruebas incluidas:**
1. Autenticación
2. Crear oferta
3. Listar ofertas
4. Activar oferta
5. Obtener mis ofertas
6. Detalle de oferta
7. Registrar vista
8. Registrar click
9. Aplicar oferta al carrito
10. Estadísticas
11. Desactivar oferta

**Resultado esperado:**
```
📈 RESUMEN DE PRUEBAS
Total de pruebas: 11
✅ Exitosas: 11
❌ Fallidas: 0
📊 Tasa de éxito: 100.0%
```

---

## 🔧 Testing Manual (API)

### Setup

```bash
# Obtener token de autenticación
TOKEN=$(curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access')

echo $TOKEN
```

---

### 🔔 Notificaciones

#### 1. Listar Notificaciones

```bash
curl http://localhost:8000/api/notifications/ \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. Enviar Notificación de Prueba

```bash
curl -X POST http://localhost:8000/api/notifications/test/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Prueba Manual",
    "message": "Esta es una notificación de prueba",
    "channels": ["IN_APP"],
    "action_url": "/test"
  }'
```

#### 3. Obtener Preferencias

```bash
curl http://localhost:8000/api/notifications/preferences/ \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. Estadísticas

```bash
curl http://localhost:8000/api/notifications/stats/ \
  -H "Authorization: Bearer $TOKEN"
```

---

### 🎁 Ofertas

#### 1. Crear Oferta

```bash
curl -X POST http://localhost:8000/api/offers/offers/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Offer",
    "description": "Oferta de prueba",
    "offer_type": "DAILY_DEAL",
    "discount_percentage": "20.00",
    "start_date": "2024-12-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z",
    "status": "DRAFT",
    "priority": 5,
    "product_ids": [1, 2]
  }'
```

#### 2. Listar Ofertas

```bash
curl http://localhost:8000/api/offers/offers/ \
  -H "Authorization: Bearer $TOKEN"
```

#### 3. Activar Oferta (Admin)

```bash
curl -X POST http://localhost:8000/api/offers/offers/1/activate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notify_users": false}'
```

#### 4. Mis Ofertas

```bash
curl http://localhost:8000/api/offers/offers/my_offers/ \
  -H "Authorization: Bearer $TOKEN"
```

#### 5. Aplicar Oferta al Carrito

```bash
curl -X POST http://localhost:8000/api/offers/offers/apply_to_cart/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "offer_id": 1,
    "cart_total": "100.00",
    "product_ids": [1, 2]
  }'
```

#### 6. Estadísticas (Admin)

```bash
curl http://localhost:8000/api/offers/offers/stats/ \
  -H "Authorization: Bearer $TOKEN"
```

---

### 🤖 Machine Learning

#### 1. Generar Recomendaciones ML

```bash
curl -X POST http://localhost:8000/api/offers/offers/generate_ml_recommendations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "max_recommendations": 5
  }'
```

#### 2. Optimizar Descuento

```bash
curl -X POST http://localhost:8000/api/offers/offers/optimize_discount/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "target_sales_increase": 1.5
  }'
```

#### 3. Top Recomendaciones

```bash
curl http://localhost:8000/api/offers/recommendations/top_recommendations/?limit=5 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎨 Testing en Admin de Django

### 1. Acceder al Admin

```
http://localhost:8000/admin/
```

### 2. Verificar Apps Instaladas

- ✅ Notifications
  - Notifications
  - Notification preferences
  - Device tokens

- ✅ Offers
  - Offers
  - Offer products
  - User offer interactions
  - Offer recommendations

### 3. Crear Oferta Desde Admin

1. Ir a: `Admin > Offers > Offers`
2. Click "Add Offer"
3. Llenar campos:
   - Name: "Test Admin Offer"
   - Type: Flash Sale
   - Discount: 30%
   - Dates: Start: hoy, End: mañana
4. En "Offer products" inline, agregar 2-3 productos
5. Save

### 4. Verificar Estadísticas Visuales

- Badges de colores en estados
- Display de vistas/clicks/conversiones
- Barra de progreso en recomendaciones

---

## 🔍 Verificación de Integraciones

### 1. Ofertas → Notificaciones

```python
# En Django shell
python manage.py shell
```

```python
from offers.models import Offer
from offers.services import OfferService

# Obtener una oferta
offer = Offer.objects.first()

# Activar con notificaciones
OfferService.activate_offer(offer.id, notify_users=True)

# Verificar que se enviaron notificaciones
from notifications.models import Notification
Notification.objects.filter(type='NEW_OFFER').count()
# Debe ser > 0
```

### 2. ML → Recomendaciones

```python
from offers.ml_models import OfferRecommendationEngine
from django.contrib.auth import get_user_model

User = get_user_model()
engine = OfferRecommendationEngine()

# Generar recomendaciones para un usuario
user = User.objects.first()
recommendations = engine.generate_recommendations_for_user(user, max_recommendations=5)

print(f"Generadas {len(recommendations)} recomendaciones")
for rec in recommendations:
    print(f"  - {rec.offer.name}: Score {rec.score:.2f}")
```

### 3. Stripe → Notificaciones

```python
# Simular webhook de Stripe (requiere setup de Stripe test)
# Ver: orders/views.py: StripeWebhookView

# Alternativamente, crear pedido y completar manualmente
from orders.models import Order
from notifications.services import NotificationService

order = Order.objects.first()
NotificationService.notify_order_confirmed(
    user=order.user,
    order_number=order.order_number,
    action_url=f'/orders/{order.id}'
)

# Verificar
from notifications.models import Notification
Notification.objects.filter(type='ORDER_CONFIRMED', user=order.user).exists()
```

---

## 📊 Verificación de Performance

### 1. Queries Optimizados

```python
from django.db import connection
from django.test.utils import override_settings

# Habilitar logging de queries
import logging
logging.basicConfig()
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

# Listar ofertas (debe usar select_related/prefetch_related)
from offers.models import Offer
offers = Offer.objects.all()[:10]

# Contar queries
len(connection.queries)
# Debe ser bajo (< 5 queries)
```

### 2. Índices en Base de Datos

```bash
python manage.py sqlmigrate offers 0001
python manage.py sqlmigrate notifications 0001
```

Verificar que se crearon índices:
- `CREATE INDEX ... ON offers_offer (status, start_date, end_date)`
- `CREATE INDEX ... ON notifications_notification (user_id, created_at)`
- etc.

---

## 🐛 Troubleshooting

### Error: "Firebase credentials not found"

**Solución:**
```bash
# Verificar que existe el archivo
ls smartsales-firebase-key.json

# Verificar path en settings.py
grep FIREBASE_CREDENTIALS_PATH smartsales_backend/settings.py
```

---

### Error: "Offer does not exist"

**Solución:**
```python
# Crear oferta de prueba
python manage.py shell
```

```python
from offers.models import Offer
from products.models import Product
from datetime import datetime, timedelta
from django.utils import timezone

offer = Offer.objects.create(
    name="Test Offer",
    offer_type="DAILY_DEAL",
    discount_percentage=20,
    start_date=timezone.now(),
    end_date=timezone.now() + timedelta(days=7),
    status="ACTIVE"
)

# Agregar productos
from offers.models import OfferProduct
products = Product.objects.all()[:3]
for p in products:
    OfferProduct.objects.create(offer=offer, product=p)
```

---

### Error: "No active offers"

**Solución:**
1. Verificar fechas: `start_date <= now <= end_date`
2. Verificar status: `status='ACTIVE'`
3. Verificar max_uses: no debe estar lleno

```python
from offers.models import Offer
from django.utils import timezone

now = timezone.now()
Offer.objects.filter(
    status='ACTIVE',
    start_date__lte=now,
    end_date__gte=now
).count()
```

---

### Error en ML: "Not enough data"

**Solución:**
El ML necesita datos históricos:
- Pedidos completados
- Interacciones con ofertas
- Productos con categorías

Crear datos de prueba:
```python
# Ver: test_offers_api.py para ejemplos
```

---

## ✅ Checklist Final de Testing

### Backend

- [ ] `python manage.py check` sin errores
- [ ] Firebase inicializado correctamente
- [ ] Test de notificaciones pasa (12/12)
- [ ] Test de ofertas pasa (11/11)
- [ ] API responde en todos los endpoints
- [ ] Admin de Django accesible

### Integraciones

- [ ] Ofertas activan notificaciones
- [ ] ML genera recomendaciones
- [ ] Stripe webhooks funcionan (si configurado)
- [ ] Email SMTP funciona (si configurado)

### Datos

- [ ] Al menos 1 oferta activa
- [ ] Al menos 3 productos
- [ ] Al menos 1 usuario con pedidos
- [ ] Al menos 5 notificaciones

---

## 🎯 Criterio de Éxito

**LISTO PARA DEPLOY si:**

✅ Todos los tests automáticos pasan (23/23)
✅ No hay errores en `python manage.py check`
✅ Firebase se inicializa correctamente
✅ API responde en todos los endpoints probados
✅ Admin funciona correctamente
✅ Integraciones verificadas

---

## 📞 Soporte

Si encuentras errores:

1. Revisa logs: `tail -f smartsales_backend.log`
2. Revisa Django shell para debugging
3. Consulta documentación:
   - `docs/NOTIFICACIONES_SISTEMA_COMPLETO.md`
   - `docs/OFERTAS_SISTEMA_COMPLETO.md`
4. Revisa código fuente con comentarios

---

**Última actualización:** Diciembre 2024
**Versión:** 2.0.0
