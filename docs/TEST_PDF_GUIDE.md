# 🧪 Guía de Uso del Script de Prueba de PDF

## 📋 Antes de Ejecutar

### 1. Instalar Dependencias
```bash
pip install requests
```

### 2. Configurar el Script

Abre `test_pdf_download.py` y modifica estas variables:

```python
# URL del backend (usar producción o local)
BACKEND_URL = "https://smartsales-backend-891739940726.us-central1.run.app"
# BACKEND_URL = "http://localhost:8000"  # Para desarrollo local

# ID de un pedido existente (IMPORTANTE: debe ser un pedido TUYO)
ORDER_ID = 1880  # ⚠️ CAMBIAR por un ID válido

# Credenciales del usuario DUEÑO del pedido
EMAIL = "tu_email@ejemplo.com"  # ⚠️ CAMBIAR
PASSWORD = "tu_password"  # ⚠️ CAMBIAR
```

### 3. Obtener un ORDER_ID Válido

Necesitas el ID de un pedido que pertenezca al usuario con las credenciales configuradas.

#### Opción A: Desde el Frontend
1. Ir a la sección "Mis Pedidos"
2. Abrir un pedido
3. Copiar el ID de la URL (ej: `/order/1880` → ID es `1880`)

#### Opción B: Desde la API
```bash
# Obtener token
curl -X POST https://smartsales-backend-891739940726.us-central1.run.app/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"tu_email@ejemplo.com","password":"tu_password"}'

# Ver tus pedidos (usar el token del paso anterior)
curl https://smartsales-backend-891739940726.us-central1.run.app/api/orders/orders/ \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

---

## 🚀 Ejecutar el Test

```bash
cd D:\2doParcialSI2\SmartSales-Backend
python test_pdf_download.py
```

---

## 📊 Resultados Esperados

### ✅ Test Exitoso

```
======================================================================
🧪 TEST DE ENDPOINTS DE COMPROBANTES DE PEDIDOS
======================================================================

📍 Backend URL: https://smartsales-backend-891739940726.us-central1.run.app
🆔 Order ID: 1880

🔒 TEST 3: Verificar Protección de Autenticación
   Status Code: 401
   ✅ Correctamente protegido: requiere autenticación

🔐 Obteniendo token de autenticación para usuario@ejemplo.com...
✅ Token obtenido exitosamente

📄 TEST 1: Ver Comprobante HTML
   Endpoint: /api/orders/receipt/1880/
   Status Code: 200
   Content-Type: text/html; charset=utf-8
   ✅ HTML recibido correctamente (45678 caracteres)
   📝 Primeros 200 caracteres:
      <!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">...

📥 TEST 2: Descargar Comprobante PDF
   Endpoint: /api/orders/receipt/1880/pdf/
   Status Code: 200
   Content-Type: application/pdf
   Content-Disposition: attachment; filename="comprobante_pedido_1880.pdf"
   ✅ Header de descarga correcto
   ✅ PDF guardado exitosamente
   📁 Ubicación: D:\2doParcialSI2\SmartSales-Backend\test_downloads\comprobante_pedido_1880_test.pdf
   📊 Tamaño: 89,234 bytes (87.14 KB)
   ✅ Archivo PDF válido (header correcto)

======================================================================
📊 RESUMEN DE TESTS
======================================================================
   Test 1 (HTML Receipt):       ✅ PASS
   Test 2 (PDF Download):       ✅ PASS
======================================================================

🎉 ¡Todos los tests pasaron!

💡 DIAGNÓSTICO DEL PROBLEMA:
   Si el PDF se descarga pero 'no hace la descarga' en el navegador,
   verifica que el header Content-Disposition contenga 'attachment'.
   Si dice 'inline', el navegador abrirá el PDF en vez de descargarlo.
```

### ❌ Errores Comunes

#### Error: Credenciales Incorrectas
```
❌ Error al obtener token: 401
   Respuesta: {"detail":"No active account found with the given credentials"}
```
**Solución**: Verificar EMAIL y PASSWORD en el script.

#### Error: Pedido No Encontrado
```
❌ Pedido no encontrado (ID: 1880)
```
**Solución**: Cambiar ORDER_ID por un ID válido de un pedido que exista.

#### Error: Sin Permisos
```
❌ Acceso denegado: No tienes permiso para descargar este pedido
```
**Solución**: El pedido pertenece a otro usuario. Usar un ORDER_ID de un pedido del usuario autenticado.

#### Error: WeasyPrint No Instalado
```
❌ Error de configuración del servidor: WeasyPrint no disponible
```
**Solución**: En el backend ejecutar:
```bash
pip install weasyprint==66.0
```

---

## 🔍 Verificar el PDF Descargado

Después de ejecutar el test, verifica el archivo descargado:

```bash
# Ver si existe el archivo
ls test_downloads/

# Abrir el PDF (Windows)
start test_downloads/comprobante_pedido_1880_test.pdf

# O manualmente navegar a:
D:\2doParcialSI2\SmartSales-Backend\test_downloads\
```

El PDF debe contener:
- ✅ Logo de SmartSales
- ✅ Información del pedido (ID, fecha, estado)
- ✅ Tabla de productos
- ✅ Subtotal, impuestos y total
- ✅ Información de garantías

---

## 🐛 Diagnóstico del Problema "No Descarga"

### Síntoma
El endpoint funciona (genera el PDF), pero en el frontend no se descarga automáticamente.

### Posibles Causas

#### 1. **Header Content-Disposition Incorrecto**

**Verificar**:
El test mostrará:
```
Content-Disposition: attachment; filename="comprobante_pedido_1880.pdf"
```

Si muestra `inline` en vez de `attachment`:
```
Content-Disposition: inline; filename="comprobante_pedido_1880.pdf"
```

**Solución**: Ya se actualizó el código backend para forzar `attachment`.

#### 2. **Frontend No Maneja Blob Correctamente**

**Verificar en el código frontend**:
```typescript
// ❌ INCORRECTO
const response = await api.get(`/orders/receipt/${orderId}/pdf/`);
// Sin responseType: 'blob', axios trata de parsear como JSON

// ✅ CORRECTO
const response = await api.get(`/orders/receipt/${orderId}/pdf/`, {
  responseType: 'blob'  // ← IMPORTANTE
});
```

#### 3. **Bloqueador de Popups del Navegador**

Algunos navegadores bloquean descargas automáticas.

**Solución**: 
- Verificar que no hay bloqueador de popups activo
- La descarga debe iniciarse desde un evento de usuario (click)

#### 4. **CORS o Headers Faltantes**

**Verificar en el test**:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="..."
Content-Length: 89234
```

Si falta alguno, puede causar problemas.

---

## 🎯 Siguiente Paso

Si el test pasa ✅, el problema está en el **frontend**.

Verifica en tu código React/TypeScript:
1. ¿Usas `responseType: 'blob'`?
2. ¿Creas el blob correctamente?
3. ¿Usas `link.download` con el nombre del archivo?
4. ¿El click se ejecuta desde un evento de usuario?

Consulta la guía actualizada en:
```
docs/FRONTEND_INTEGRATION_PROMPT.md
Sección: "📄 4. Integrar en Página de Pedidos (Descarga PDF)"
```

---

## 📞 Soporte

Si el test falla o tienes dudas, reporta:
1. Output completo del test
2. ORDER_ID usado
3. Status codes recibidos
4. Contenido del archivo test_downloads/comprobante_pedido_XXXX_test.pdf

¡Buena suerte! 🚀
