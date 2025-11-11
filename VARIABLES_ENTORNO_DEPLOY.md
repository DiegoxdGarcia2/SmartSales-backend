# 🔐 VARIABLES DE ENTORNO PARA CLOUD RUN

## 📋 Checklist de Variables

### ✅ VARIABLES QUE YA TENEMOS

Estas son las variables que **YA ESTÁN CONFIGURADAS** en tu proyecto actual:

```bash
# Base de Datos PostgreSQL (Render)
DATABASE_URL=postgresql://smartsales_db_user:contraseña@dpg-xxx.oregon-postgres.render.com/smartsales_db

# Django Settings
DJANGO_SECRET_KEY=tu-secret-key-aqui
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*.run.app localhost 127.0.0.1

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Cloudinary (para imágenes)
CLOUDINARY_CLOUD_NAME=xxx
CLOUDINARY_API_KEY=xxx
CLOUDINARY_API_SECRET=xxx

# Frontend URL
FRONTEND_URL=http://localhost:3039  # Cambiar a URL de producción
```

---

### 🆕 VARIABLES NUEVAS NECESARIAS

Estas son las variables **QUE NECESITAMOS AGREGAR** para el nuevo sistema:

#### 1. Firebase (CRÍTICO - Sistema de Notificaciones)

```bash
# VAPID Key para Web Push
FIREBASE_WEB_PUSH_CERTIFICATE=7rVPMZoay6m1vIC8k61PaqIu5vL_cSSxm_04t2GxepQ
```

**📝 Nota:** El archivo `smartsales-firebase-key.json` **NO se sube** como variable de entorno.
Se debe subir a **Google Secret Manager** (ver instrucciones abajo).

---

#### 2. Email SMTP (Sistema de Notificaciones)

**OPCIÓN A: Gmail (Recomendado para pruebas)**
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password-de-gmail
DEFAULT_FROM_EMAIL=SmartSales <noreply@smartsales.com>
```

**OPCIÓN B: SendGrid (Recomendado para producción)**
```bash
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.tu-api-key-de-sendgrid
DEFAULT_FROM_EMAIL=SmartSales <noreply@smartsales.com>
```

**OPCIÓN C: Mailgun**
```bash
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_HOST_USER=postmaster@tu-dominio.mailgun.org
EMAIL_HOST_PASSWORD=tu-password-de-mailgun
DEFAULT_FROM_EMAIL=SmartSales <noreply@smartsales.com>
```

---

## 🔍 ¿QUÉ VARIABLES NECESITAS CONSEGUIR?

### 1️⃣ Email SMTP (REQUERIDO)

**Si usas Gmail:**
1. Ir a: https://myaccount.google.com/security
2. Activar "Verificación en 2 pasos"
3. Ir a: https://myaccount.google.com/apppasswords
4. Crear una contraseña de aplicación para "Correo"
5. Copiar la contraseña generada (16 caracteres)

**Usar:**
```bash
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx  # La contraseña de 16 caracteres
```

**Si usas SendGrid (gratis hasta 100 emails/día):**
1. Crear cuenta en: https://sendgrid.com/
2. Ir a: Settings → API Keys
3. Crear API Key con permisos de "Mail Send"
4. Copiar el API Key

**Usar:**
```bash
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxxxxxxxxxxxxx  # Tu API Key
```

---

### 2️⃣ Frontend URL (ACTUALIZAR)

Necesitas la URL de tu frontend en producción:

```bash
# Si tu frontend está en Vercel/Netlify
FRONTEND_URL=https://tu-app.vercel.app

# O si está en otro servicio
FRONTEND_URL=https://tu-dominio.com
```

---

### 3️⃣ Django Secret Key (GENERAR NUEVA)

Para producción, **NO uses** la secret key de desarrollo. Genera una nueva:

**Opción 1: Online**
- Ir a: https://djecrety.ir/
- Copiar la key generada

**Opción 2: Python**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📦 LISTA COMPLETA DE VARIABLES PARA CLOUD RUN

Copia este bloque y reemplaza los valores:

```bash
# ============================================
# DJANGO SETTINGS
# ============================================
DJANGO_SECRET_KEY=tu-nueva-secret-key-de-produccion-muy-larga-y-segura
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*.run.app localhost 127.0.0.1

# ============================================
# BASE DE DATOS
# ============================================
DATABASE_URL=postgresql://usuario:password@host/database

# ============================================
# STRIPE
# ============================================
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# ============================================
# CLOUDINARY (Imágenes)
# ============================================
CLOUDINARY_CLOUD_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret

# ============================================
# FIREBASE (Notificaciones Push)
# ============================================
FIREBASE_WEB_PUSH_CERTIFICATE=7rVPMZoay6m1vIC8k61PaqIu5vL_cSSxm_04t2GxepQ

# ============================================
# EMAIL SMTP (Notificaciones Email)
# ============================================
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password-de-16-caracteres
DEFAULT_FROM_EMAIL=SmartSales <noreply@smartsales.com>

# ============================================
# FRONTEND
# ============================================
FRONTEND_URL=https://tu-frontend.vercel.app
```

---

## 🔐 FIREBASE CREDENTIALS (Secret Manager)

El archivo `smartsales-firebase-key.json` **NO se pone en variables de entorno**.

### Método 1: Google Secret Manager (RECOMENDADO)

```bash
# 1. Subir el archivo a Secret Manager
gcloud secrets create firebase-credentials \
    --data-file=smartsales-firebase-key.json \
    --replication-policy="automatic"

# 2. Dar permisos al servicio de Cloud Run
gcloud secrets add-iam-policy-binding firebase-credentials \
    --member="serviceAccount:PROJECT_ID-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# 3. Montar el secret en Cloud Run (en el deploy)
gcloud run deploy smartsales-backend \
    --source . \
    --region us-central1 \
    --set-secrets="/app/smartsales-firebase-key.json=firebase-credentials:latest"
```

### Método 2: Variable de Entorno (NO RECOMENDADO pero funciona)

```bash
# Convertir a base64
base64 smartsales-firebase-key.json > firebase-base64.txt

# Agregar como variable
FIREBASE_CREDENTIALS_BASE64=contenido-del-archivo-base64

# Modificar settings.py para decodificar
```

---

## 🚀 COMANDO COMPLETO DE DEPLOY

Una vez que tengas todas las variables, usa este comando:

```bash
gcloud run deploy smartsales-backend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --timeout 300 \
    --set-env-vars "\
DJANGO_SECRET_KEY=tu-secret-key,\
DJANGO_DEBUG=False,\
DJANGO_ALLOWED_HOSTS=*.run.app,\
DATABASE_URL=tu-database-url,\
STRIPE_PUBLISHABLE_KEY=tu-stripe-pk,\
STRIPE_SECRET_KEY=tu-stripe-sk,\
STRIPE_WEBHOOK_SECRET=tu-webhook-secret,\
CLOUDINARY_CLOUD_NAME=tu-cloudinary,\
CLOUDINARY_API_KEY=tu-api-key,\
CLOUDINARY_API_SECRET=tu-api-secret,\
FIREBASE_WEB_PUSH_CERTIFICATE=7rVPMZoay6m1vIC8k61PaqIu5vL_cSSxm_04t2GxepQ,\
EMAIL_HOST=smtp.gmail.com,\
EMAIL_PORT=587,\
EMAIL_HOST_USER=tu-email@gmail.com,\
EMAIL_HOST_PASSWORD=tu-app-password,\
DEFAULT_FROM_EMAIL=SmartSales <noreply@smartsales.com>,\
FRONTEND_URL=https://tu-frontend.vercel.app" \
    --set-secrets="/app/smartsales-firebase-key.json=firebase-credentials:latest"
```

---

## 📝 RESUMEN: ¿QUÉ NECESITAS HACER AHORA?

### ✅ Ya tienes (del proyecto anterior):
- [x] DATABASE_URL
- [x] DJANGO_SECRET_KEY (pero deberías generar una nueva)
- [x] STRIPE keys
- [x] CLOUDINARY keys

### ❓ NECESITAS CONSEGUIR:

1. **Email SMTP** (Elige una opción):
   - [ ] Gmail App Password (más fácil)
   - [ ] SendGrid API Key (mejor para producción)
   - [ ] Otro proveedor SMTP

2. **Frontend URL** (actualizar):
   - [ ] URL de producción de tu frontend

3. **Firebase Credentials**:
   - [x] Ya tienes el archivo `smartsales-firebase-key.json`
   - [ ] Subirlo a Google Secret Manager

4. **Nueva Secret Key** (opcional pero recomendado):
   - [ ] Generar nueva secret key para producción

---

## 🆘 Si tienes dudas sobre alguna variable

**Firebase:**
- Ya está configurado ✅
- Solo necesitas subirlo a Secret Manager

**Email:**
- Lo más fácil: Usar Gmail con App Password
- Ver instrucciones arriba

**Frontend URL:**
- ¿Dónde vas a desplegar tu frontend?
  - Vercel: `https://tu-app.vercel.app`
  - Netlify: `https://tu-app.netlify.app`
  - Otro: Tu dominio personalizado

---

## 🔍 Verificar que todo esté bien

Antes del deploy, verifica:

```bash
# 1. Firebase credentials existe
ls smartsales-firebase-key.json

# 2. Todas las variables están en un archivo .env (local)
cat .env

# 3. Test local con variables
python manage.py check --deploy
```

---

## 📞 CONTACTO

Si necesitas ayuda con alguna variable específica, dime cuál y te ayudo a conseguirla.

**Variables más importantes:**
1. 🔴 **EMAIL_HOST_USER** y **EMAIL_HOST_PASSWORD** - SIN ESTO no funcionan las notificaciones por email
2. 🟡 **FRONTEND_URL** - Importante para links en notificaciones
3. 🟢 **FIREBASE_WEB_PUSH_CERTIFICATE** - Ya la tenemos ✅

---

**Última actualización:** Diciembre 2024
