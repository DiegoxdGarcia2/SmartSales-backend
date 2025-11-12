# 🚀 Guía de Despliegue - Sistema de Notificaciones Completo

## 📋 Checklist Pre-Despliegue

### ✅ Verificar Migraciones
```bash
# En producción, ejecutar:
python manage.py showmigrations orders
# Debe mostrar: orders/000X_add_entregado_status [ ] (no aplicado)

python manage.py migrate orders
# Aplicar la migración del nuevo estado ENTREGADO
```

### ✅ Verificar Señales
Asegurarse de que estas líneas estén en `apps.py`:
```python
def ready(self):
    import notifications.signals  # ✅
    import orders.signals         # ✅
    import products.signals       # ✅
```

## 🎯 Configuración de Producción

### 1. Migraciones en Producción
```bash
# Conectar a Cloud SQL y ejecutar:
gcloud run jobs execute migrate-job --region=us-central1 --wait

# O directamente en Cloud Run:
kubectl exec -it deployment/smartsales-backend -- python manage.py migrate
```

### 2. Configurar Cron Jobs (Tareas Programadas)

#### Opción A: Cloud Scheduler (Recomendado)
```bash
# Crear job para verificar ofertas expirando cada 6 horas
gcloud scheduler jobs create http check-expiring-offers \
  --schedule="0 */6 * * *" \
  --uri="https://tu-dominio.run.app/api/notifications/debug/" \
  --http-method=POST \
  --headers="Authorization=Bearer TU_TOKEN_ADMIN,Content-Type=application/json" \
  --message-body='{"action": "check_expiring_offers"}' \
  --oidc-service-account-email=tu-service-account@tu-proyecto.iam.gserviceaccount.com
```

#### Opción B: Comando Directo en Cloud Run Jobs
```bash
# Crear job reutilizable
gcloud run jobs create check-offers \
  --image=gcr.io/tu-proyecto/smartsales-backend \
  --command="python manage.py check_expiring_offers --hours=24" \
  --region=us-central1

# Ejecutar manualmente
gcloud run jobs execute check-offers --region=us-central1 --wait
```

### 3. Configurar Firebase para Push Notifications

#### Paso 1: Verificar Credenciales
```bash
# Asegurarse de que existe el secret
gcloud secrets describe firebase-key --project=tu-proyecto

# Si no existe, crear:
echo $FIREBASE_SERVICE_ACCOUNT_JSON | gcloud secrets create firebase-key \
  --data-file=-
```

#### Paso 2: Verificar Configuración en settings.py
```python
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    'FIREBASE_CREDENTIALS_PATH',
    '/secrets/firebase.json'  # ✅ Para Cloud Run
)
```

#### Paso 3: Probar Push Notifications
```bash
# Desde el admin panel o API
POST /api/notifications/test/
{
  "title": "Prueba Push",
  "message": "Notificación de prueba",
  "channels": ["PUSH"]
}
```

## 🧪 Guía de Testing Completo

### 1. Probar Todas las Notificaciones
```bash
# Endpoint completo de testing
POST /api/notifications/debug/
{
  "action": "test_all_notifications"
}
```

### 2. Simular Flujo Completo de Usuario

#### Registro → Notificación Bienvenida
```bash
POST /api/auth/register/
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123"
}
# ✅ Debe recibir notificación de bienvenida
```

#### Compra → Notificaciones de Pago
```bash
# 1. Crear orden
POST /api/orders/create-order-from-cart/

# 2. Pagar con Stripe (simular webhook)
# ✅ Debe recibir: pago exitoso + orden confirmada
```

#### Admin cambia estado → Notificaciones
```bash
# Como admin
POST /api/orders/{order_id}/update_status/
{
  "status": "ENVIADO"
}
# ✅ Usuario debe recibir notificación de envío

POST /api/orders/{order_id}/update_status/
{
  "status": "ENTREGADO"
}
# ✅ Usuario debe recibir notificación de entrega
```

#### Producto vuelve a stock → Notificación
```bash
# Como admin, cambiar stock de 0 a 5
# ✅ Compradores anteriores deben recibir notificación
```

#### Crear oferta → Notificaciones
```bash
POST /api/offers/
{
  "name": "Oferta Test",
  "offer_type": "FLASH_SALE",
  "discount_percentage": 30,
  "start_date": "2025-11-12T10:00:00Z",
  "end_date": "2025-11-13T10:00:00Z",
  "products": [1, 2, 3]
}

POST /api/offers/{id}/activate/
{
  "notify_users": true
}
# ✅ Usuarios deben recibir notificación de nueva oferta
```

### 3. Verificar Estado de Notificaciones
```bash
# Ver todas las notificaciones del usuario
GET /api/notifications/

# Ver estado completo de debug
GET /api/notifications/debug/

# Ver preferencias
GET /api/notifications/preferences/
```

## 📊 Monitoreo y Logs

### 1. Logs de Notificaciones
```bash
# Ver logs de notificaciones en Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=smartsales-backend" \
  --filter="NOTIFICACIÓN OR notification" \
  --limit=50

# Buscar errores específicos
gcloud logging read "resource.type=cloud_run_revision" \
  --filter="severity>=ERROR AND (notification OR firebase OR signal)" \
  --limit=20
```

### 2. Métricas a Monitorear
- ✅ **Tasa de envío exitoso** de notificaciones push
- ✅ **Tasa de apertura** de notificaciones in-app
- ✅ **Errores de Firebase** (tokens inválidos, etc.)
- ✅ **Notificaciones por tipo** (pagos, ofertas, sistema)

### 3. Alertas Recomendadas
```bash
# Crear alerta para errores de notificaciones
gcloud monitoring alert-policies create notification-errors \
  --display-name="Errores de Notificaciones" \
  --condition="resource.type=cloud_run_revision AND metric.type=run.googleapis.com/request_count AND metric.label.response_code_class=5xx" \
  --notification-channels=tu-canal-email
```

## 🔧 Solución de Problemas

### Push Notifications no llegan
```bash
# 1. Verificar token FCM del usuario
GET /api/notifications/debug/

# 2. Probar envío directo
POST /api/notifications/test/
{
  "title": "Test Push",
  "message": "Test message",
  "channels": ["PUSH"]
}

# 3. Verificar Firebase credentials
gcloud secrets access firebase-key --format="value" | head -20
```

### Notificaciones duplicadas
```bash
# Verificar señales no se ejecutan múltiples veces
# Revisar logs por "NOTIFICACIÓN" para detectar duplicados
```

### Ofertas no notifican expiración
```bash
# Ejecutar manualmente
POST /api/notifications/debug/
{
  "action": "check_expiring_offers"
}

# Verificar que el cron job está activo
gcloud scheduler jobs list
```

## 📱 Integración con Frontend

### Endpoints para Frontend
```javascript
// Obtener notificaciones del usuario
GET /api/notifications/

// Marcar como leída
POST /api/notifications/{id}/mark_as_read/

// Marcar todas como leídas
POST /api/notifications/mark_all_as_read/

// Obtener preferencias
GET /api/notifications/preferences/

// Actualizar preferencias
PATCH /api/notifications/preferences/
{
  "orders_push": true,
  "offers_email": false
}

// Registrar token FCM
POST /api/fcm-tokens/
{
  "token": "fcm_token_aqui",
  "device_type": "WEB"
}
```

### Manejo de Push en Frontend
```javascript
// Solicitar permiso para notificaciones
if ('Notification' in window) {
  Notification.requestPermission().then(permission => {
    if (permission === 'granted') {
      // Registrar token con backend
      getFCMToken().then(token => {
        fetch('/api/fcm-tokens/', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({token, device_type: 'WEB'})
        });
      });
    }
  });
}

// Escuchar mensajes push
import { onMessage } from 'firebase/messaging';
onMessage(messaging, (payload) => {
  // Mostrar notificación local
  new Notification(payload.notification.title, {
    body: payload.notification.body,
    icon: '/icon.png'
  });
});
```

## 🎉 Checklist Final

- [ ] Migraciones aplicadas en producción
- [ ] Cron job configurado para ofertas expirando
- [ ] Firebase configurado correctamente
- [ ] Testing completo realizado
- [ ] Logs monitoreados
- [ ] Frontend integrado
- [ ] Documentación actualizada

¡El sistema de notificaciones está 100% funcional! 🚀