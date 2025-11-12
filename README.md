# 🚀 SmartSales365 - Backend

API REST para el sistema de gestión de ventas **SmartSales365**, desarrollado con Django REST Framework, PostgreSQL y autenticación JWT.

**Sistema completo con Machine Learning, Notificaciones Multi-Canal y Sistema de Ofertas Inteligente.**

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Stack Tecnológico](#-stack-tecnológico)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Endpoints Disponibles](#-endpoints-disponibles)
- [Documentación API](#-documentación-api)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Fase de Desarrollo](#-fase-de-desarrollo)

---

## ✨ Características

### Core
- ✅ **Autenticación JWT** con tokens de acceso y refresco
- ✅ **Modelo de usuario personalizado** con roles (ADMINISTRADOR, CLIENTE)
- ✅ **Registro de usuarios** con validación de contraseñas
- ✅ **Documentación automática** con Swagger/OpenAPI
- ✅ **CORS configurado** para integración con frontend React
- ✅ **Base de datos PostgreSQL** para producción
- ✅ **Django REST Framework** para APIs robustas

### 🔔 Sistema de Notificaciones (NUEVO)
- ✅ **3 Canales de notificación**: IN_APP, PUSH (Firebase FCM), EMAIL (SMTP)
- ✅ **9 Tipos de notificaciones**: Pedidos, Pagos, Ofertas, Sistema
- ✅ **Preferencias configurables** por usuario y canal
- ✅ **Firebase Cloud Messaging** para notificaciones push
- ✅ **Templates HTML responsive** para emails
- ✅ **Gestión de dispositivos FCM**
- ✅ **Integración con Stripe webhooks**

### 🎁 Sistema de Ofertas (NUEVO)
- ✅ **5 tipos de ofertas**: Flash Sale, Daily Deal, Seasonal, Clearance, Personalized
- ✅ **Tracking completo**: Vistas, clicks, conversiones
- ✅ **Aplicación automática** de ofertas al carrito
- ✅ **Restricciones avanzadas**: Monto mínimo, usos máximos, usuarios específicos
- ✅ **Estadísticas en tiempo real** y analytics
- ✅ **Admin personalizado** con badges y visualizaciones

### 🤖 Machine Learning (NUEVO)
- ✅ **Recomendaciones personalizadas** basadas en comportamiento del usuario
- ✅ **Scoring multi-factor**: Historial (40%), Interacciones (20%), Popularidad (15%), Descuento (15%), Urgencia (10%)
- ✅ **Optimización de descuentos** con análisis de elasticidad de precio
- ✅ **Proyección de impacto** en ventas y revenue
- ✅ **Análisis de competencia** y posicionamiento
- ✅ **Tracking de efectividad** de recomendaciones ML

---

## 🛠 Stack Tecnológico

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| Python | 3.13+ | Lenguaje base |
| Django | 5.2+ | Framework web |
| Django REST Framework | - | API REST |
| PostgreSQL | 14+ | Base de datos |
| djangorestframework-simplejwt | - | Autenticación JWT |
| drf-spectacular | - | Documentación OpenAPI/Swagger |
| django-cors-headers | - | Manejo de CORS |
| psycopg2-binary | - | Adaptador PostgreSQL |
| **firebase-admin** | **6.5.0** | **Notificaciones Push (FCM)** |
| **Stripe** | - | **Procesamiento de pagos** |
| **Cloudinary** | - | **Almacenamiento de imágenes** |
| **WeasyPrint** | - | **Generación de PDFs** |
| **NumPy** | - | **Análisis numérico para ML** |

---

## 📦 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.13+** - [Descargar](https://www.python.org/downloads/)
- **PostgreSQL 14+** - [Descargar](https://www.postgresql.org/download/)
- **pip** - Gestor de paquetes de Python
- **Git** - Control de versiones

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/DiegoxdGarcia2/SmartSales-backend.git
cd SmartSales-backend
```

### 2. Crear y activar entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración

### 1. Configurar PostgreSQL

Crea la base de datos en PostgreSQL:

```sql
CREATE DATABASE smartsales_db;
```

### 2. Variables de entorno (Opcional)

Puedes crear un archivo `.env` para sobrescribir las configuraciones por defecto:

```env
DB_NAME=smartsales_db
DB_USER=postgres
DB_PASSWORD=admin123
DB_HOST=localhost
DB_PORT=5432
```

**Valores por defecto:**
- `DB_NAME`: `smartsales_db`
- `DB_USER`: `postgres`
- `DB_PASSWORD`: `admin123`
- `DB_HOST`: `localhost`
- `DB_PORT`: `5432`

### 3. Ejecutar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Crear superusuario

```bash
python manage.py createsuperuser
```

---

## 🎯 Uso

### Iniciar el servidor de desarrollo

```bash
python manage.py runserver
```

El servidor estará disponible en: **http://localhost:8000**

---

## 📡 Endpoints Disponibles

### 🔐 Autenticación

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| POST | `/api/users/register/` | Registrar nuevo usuario | No requerida |
| POST | `/api/token/` | Obtener tokens JWT | No requerida |
| POST | `/api/token/refresh/` | Refrescar access token | Refresh token |
| GET | `/api/users/profiles/` | Listar perfiles de clientes | JWT (Admin: todos, Cliente: propio) |
| GET | `/api/users/profiles/{id}/` | Ver perfil específico | JWT |
| POST | `/api/users/profiles/` | Crear perfil de cliente | JWT |
| PUT/PATCH | `/api/users/profiles/{id}/` | Actualizar perfil | JWT |
| DELETE | `/api/users/profiles/{id}/` | Eliminar perfil | JWT (Solo Admin) |

### 📦 Productos y Categorías

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/categories/` | Listar todas las categorías | No requerida |
| GET | `/api/categories/{id}/` | Ver categoría específica | No requerida |
| POST | `/api/categories/` | Crear nueva categoría | JWT (Solo Admin) |
| PUT/PATCH | `/api/categories/{id}/` | Actualizar categoría | JWT (Solo Admin) |
| DELETE | `/api/categories/{id}/` | Eliminar categoría | JWT (Solo Admin) |
| GET | `/api/products/` | Listar todos los productos | No requerida |
| GET | `/api/products/?category={id}` | Filtrar productos por categoría | No requerida |
| GET | `/api/products/{id}/` | Ver producto específico | No requerida |
| POST | `/api/products/` | Crear nuevo producto | JWT (Solo Admin) |
| PUT/PATCH | `/api/products/{id}/` | Actualizar producto | JWT (Solo Admin) |
| DELETE | `/api/products/{id}/` | Eliminar producto | JWT (Solo Admin) |

### 🔔 Notificaciones (NUEVO)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/notifications/notifications/` | Listar notificaciones del usuario | JWT |
| GET | `/api/notifications/notifications/{id}/` | Ver notificación específica | JWT |
| GET | `/api/notifications/notifications/unread_count/` | Contador de no leídas | JWT |
| POST | `/api/notifications/notifications/{id}/mark_as_read/` | Marcar como leída | JWT |
| POST | `/api/notifications/notifications/mark_all_as_read/` | Marcar todas como leídas | JWT |
| DELETE | `/api/notifications/notifications/delete_read/` | Eliminar leídas | JWT |
| GET | `/api/notifications/notifications/stats/` | Estadísticas de notificaciones | JWT |
| GET | `/api/notifications/preferences/` | Obtener preferencias | JWT |
| PATCH | `/api/notifications/preferences/` | Actualizar preferencias | JWT |
| GET | `/api/notifications/fcm-tokens/` | Listar dispositivos FCM | JWT |
| POST | `/api/notifications/fcm-tokens/` | Registrar token FCM | JWT |
| DELETE | `/api/notifications/fcm-tokens/{id}/` | Eliminar dispositivo | JWT |
| POST | `/api/notifications/test/` | Enviar notificación de prueba | JWT |

### 🎁 Ofertas (NUEVO)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/offers/offers/` | Listar ofertas | Pública (solo activas) |
| GET | `/api/offers/offers/active/` | Ofertas activas públicas | Pública |
| GET | `/api/offers/offers/featured/` | Ofertas destacadas | Pública |
| GET | `/api/offers/offers/personalized/` | Ofertas personalizadas ML | JWT |
| GET | `/api/offers/offers/{id}/` | Ver detalle de oferta | Pública/JWT |
| POST | `/api/offers/offers/` | Crear oferta | JWT (Solo Admin) |
| PUT/PATCH | `/api/offers/offers/{id}/` | Actualizar oferta | JWT (Solo Admin) |
| POST | `/api/offers/offers/{id}/activate/` | Activar oferta | JWT (Solo Admin) |
| POST | `/api/offers/offers/{id}/deactivate/` | Desactivar oferta | JWT (Solo Admin) |
| GET | `/api/offers/offers/{id}/track_view/` | Registrar vista | JWT |
| POST | `/api/offers/offers/{id}/track_click/` | Registrar click | JWT |
| POST | `/api/offers/offers/apply_to_cart/` | Aplicar oferta al carrito | JWT |
| GET | `/api/offers/offers/my_offers/` | Mis ofertas disponibles | JWT |
| GET | `/api/offers/offers/stats/` | Estadísticas generales | JWT (Admin) |
| GET | `/api/offers/categories/` | Tipos de ofertas disponibles | Pública |

### 🤖 Machine Learning (NUEVO)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| POST | `/api/offers/offers/generate_ml_recommendations/` | Generar recomendaciones | JWT (Admin) |
| POST | `/api/offers/offers/optimize_discount/` | Optimizar descuento de producto | JWT (Admin) |
| GET | `/api/offers/recommendations/` | Mis recomendaciones ML | JWT |
| GET | `/api/offers/recommendations/top_recommendations/` | Top N recomendaciones | JWT |
| POST | `/api/offers/recommendations/{id}/mark_clicked/` | Marcar recomendación clickeada | JWT |
| POST | `/api/offers/recommendations/{id}/mark_converted/` | Marcar conversión | JWT |

### 📚 Documentación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/docs/` | Interfaz Swagger UI |
| GET | `/api/redoc/` | Interfaz Redoc |
| GET | `/api/schema/` | Schema OpenAPI (JSON) |

### 👨‍💼 Administración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/admin/` | Panel de administración Django |

---

## 📖 Documentación API

Accede a la documentación interactiva de la API:

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **Redoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)

---

## 📁 Estructura del Proyecto

```
SmartSales-backend/
│
├── smartsales_backend/          # Configuración principal del proyecto
│   ├── settings.py              # Configuración Django + Firebase + Email
│   ├── urls.py                  # URLs principales
│   ├── wsgi.py                  # Configuración WSGI
│   └── asgi.py                  # Configuración ASGI
│
├── users/                       # App de gestión de usuarios
│   ├── migrations/              # Migraciones de base de datos
│   ├── models.py               # Modelo User y ClientProfile
│   ├── serializers.py          # Serializers (User, Register, ClientProfile)
│   ├── views.py                # Vistas (RegisterView, ClientProfileViewSet)
│   ├── urls.py                 # URLs de la app users
│   └── admin.py                # Configuración del admin
│
├── products/                    # App de gestión de productos
│   ├── migrations/              # Migraciones de base de datos
│   ├── models.py               # Modelos Category y Product
│   ├── serializers.py          # Serializers (Category, Product)
│   ├── views.py                # ViewSets (CategoryViewSet, ProductViewSet)
│   ├── urls.py                 # URLs de la app products
│   └── admin.py                # Configuración del admin
│
├── orders/                      # App de gestión de pedidos
│   ├── migrations/              # Migraciones de base de datos
│   ├── models.py               # Modelos Order, OrderItem, Payment
│   ├── serializers.py          # Serializers para pedidos
│   ├── views.py                # ViewSets + Stripe webhooks
│   ├── urls.py                 # URLs de la app orders
│   └── admin.py                # Configuración del admin
│
├── notifications/ (NUEVO)       # App de notificaciones
│   ├── migrations/              # Migraciones de base de datos
│   ├── models.py               # Notification, NotificationPreference, DeviceToken
│   ├── serializers.py          # Serializers para notificaciones
│   ├── services.py             # NotificationService (lógica centralizada)
│   ├── views.py                # ViewSets (NotificationViewSet, etc.)
│   ├── urls.py                 # URLs de la app notifications
│   └── admin.py                # Configuración del admin
│
├── offers/ (NUEVO)              # App de ofertas y ML
│   ├── migrations/              # Migraciones de base de datos
│   ├── models.py               # Offer, OfferProduct, UserOfferInteraction, OfferRecommendation
│   ├── serializers.py          # Serializers para ofertas
│   ├── services.py             # OfferService (lógica de negocio)
│   ├── ml_models.py            # OfferRecommendationEngine + DiscountOptimizer
│   ├── views.py                # ViewSets (OfferViewSet, etc.)
│   ├── urls.py                 # URLs de la app offers
│   ├── admin.py                # Admin personalizado con badges
│   └── management/commands/    # Comandos personalizados
│       └── create_sample_offers.py
│
├── templates/                   # Templates HTML
│   └── emails/                  # Templates para emails
│       └── notification.html
│
├── .gitignore                   # Archivos ignorados por Git
├── requirements.txt             # Dependencias del proyecto
├── manage.py                    # Script de gestión de Django
├── populate_offers.py           # Script para crear ofertas de prueba
└── README.md                    # Este archivo
```

---

## 🏗️ Fase de Desarrollo

### ✅ FASE 1: Núcleo y Autenticación (Completada)

- [x] Configuración inicial del proyecto Django
- [x] Configuración de PostgreSQL
- [x] Modelo de usuario personalizado con roles
- [x] Sistema de autenticación JWT
- [x] Endpoint de registro de usuarios
- [x] Documentación Swagger/OpenAPI
- [x] Configuración de CORS
- [x] Panel de administración configurado

### ✅ FASE 2: Módulo de Gestión Comercial (Completada)

- [x] App `products` creada
- [x] Modelo `Category` (categorías de productos)
- [x] Modelo `Product` (productos con precio, stock, marca, garantía)
- [x] Modelo `ClientProfile` (perfiles extendidos de clientes)
- [x] CRUD completo para categorías (ViewSet)
- [x] CRUD completo para productos (ViewSet)
- [x] CRUD de perfiles de clientes (ViewSet)
- [x] Permisos: Admin puede todo, público puede ver productos
- [x] Filtrado de productos por categoría
- [x] Serializers con validaciones
- [x] Panel de administración para productos y categorías

### ✅ FASE 3: Gestión de Pedidos y Pagos (Completada)

- [x] Modelo `Order` (pedidos con estados)
- [x] Modelo `OrderItem` (items del pedido)
- [x] Modelo `Payment` (pagos con Stripe)
- [x] Carrito de compras funcional
- [x] Proceso de checkout completo
- [x] Integración con Stripe Checkout
- [x] Webhooks de Stripe para actualización de estados
- [x] Historial de pedidos por cliente
- [x] Comprobantes de pedido (HTML y PDF)

### ✅ FASE 4: Sistema de Notificaciones (NUEVO - Completada)

- [x] App `notifications` creada
- [x] Modelo `Notification` (3 canales: IN_APP, PUSH, EMAIL)
- [x] Modelo `NotificationPreference` (preferencias por usuario)
- [x] Modelo `DeviceToken` (gestión de dispositivos FCM)
- [x] NotificationService centralizado
- [x] 9 tipos de notificaciones implementados
- [x] Firebase Cloud Messaging configurado
- [x] Templates HTML responsive para emails
- [x] Integración con webhooks de Stripe
- [x] API REST completa (15+ endpoints)
- [x] Panel de administración

### ✅ FASE 5: Sistema de Ofertas y Machine Learning (NUEVO - Completada)

- [x] App `offers` creada
- [x] Modelo `Offer` (5 tipos de ofertas)
- [x] Modelo `OfferProduct` (productos en ofertas)
- [x] Modelo `UserOfferInteraction` (tracking)
- [x] Modelo `OfferRecommendation` (recomendaciones ML)
- [x] OfferService con lógica de negocio
- [x] OfferRecommendationEngine (scoring multi-factor)
- [x] DiscountOptimizer (optimización de descuentos)
- [x] Tracking de vistas, clicks y conversiones
- [x] Aplicación automática de ofertas al carrito
- [x] API REST completa (20+ endpoints)
- [x] Admin personalizado con badges
- [x] Integración con sistema de notificaciones
- [x] Ofertas personalizadas por usuario

### � Estadísticas del Proyecto

- **Total de Apps**: 5 (users, products, orders, notifications, offers)
- **Modelos totales**: 16
- **Endpoints API**: 60+
- **Líneas de código**: ~10,000+
- **Cobertura de funcionalidad**: Backend 100% ✅

### 🔜 FASE 6: Frontend (Próximamente)

- [ ] Implementación de Service Worker para notificaciones
- [ ] Integración de Firebase FCM en React
- [ ] UI de notificaciones
- [ ] UI de ofertas y aplicación en carrito
- [ ] Dashboard de recomendaciones ML
- [ ] Reportes y analytics visuales

---

## 👨‍💻 Autor

**Diego García**

- GitHub: [@DiegoxdGarcia2](https://github.com/DiegoxdGarcia2)

---

## 📄 Licencia

Este proyecto es parte de un desarrollo académico para **Sistemas Informáticos 2**.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz un Fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/NuevaCaracteristica`)
3. Commit tus cambios (`git commit -m 'Add: Nueva característica'`)
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Abre un Pull Request

---

## 📞 Soporte

Si encuentras algún problema o tienes alguna pregunta, por favor abre un [issue](https://github.com/DiegoxdGarcia2/SmartSales-backend/issues).

---

**Desarrollado con ❤️ para SmartSales365**
