"""
Script de prueba para verificar el funcionamiento de los endpoints de comprobantes.

Prueba:
1. Ver comprobante HTML (endpoint /receipt/<order_id>/)
2. Descargar comprobante PDF (endpoint /receipt/<order_id>/pdf/)

Uso:
    python test_pdf_download.py

Requisitos:
    - Tener un pedido existente (configurar ORDER_ID)
    - Tener credenciales de usuario válidas
    - Backend corriendo en BACKEND_URL
"""

import requests
import os
from pathlib import Path

# ============================================
# CONFIGURACIÓN - MODIFICAR SEGÚN TU ENTORNO
# ============================================

# URL del backend
BACKEND_URL = "https://smartsales-backend-891739940726.us-central1.run.app"  # Producción
# BACKEND_URL = "http://localhost:8000"  # Para desarrollo local

# ID de un pedido existente para probar
ORDER_ID = 1880  # Pedido del admin en producción (07 Nov 2025, PAGADO)

# Credenciales de usuario que es dueño del pedido
EMAIL = "admin@smartsales.com"
PASSWORD = "admin123"

# Directorio donde guardar el PDF de prueba
OUTPUT_DIR = Path("test_downloads")

# ============================================
# FIN DE CONFIGURACIÓN
# ============================================


def get_auth_token(email, password):
    """
    Obtiene el token JWT de autenticación.
    """
    print(f"\n🔐 Obteniendo token de autenticación para {email}...")
    
    login_url = f"{BACKEND_URL}/api/token/"
    
    try:
        response = requests.post(
            login_url,
            json={"username": email, "password": password}  # username acepta email
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access')
            print(f"✅ Token obtenido exitosamente")
            return token
        else:
            print(f"❌ Error al obtener token: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Excepción al obtener token: {e}")
        return None


def test_html_receipt(order_id, token):
    """
    Prueba 1: Ver comprobante en formato HTML.
    Este endpoint devuelve HTML que se puede ver en el navegador.
    """
    print(f"\n📄 TEST 1: Ver Comprobante HTML")
    print(f"   Endpoint: /api/orders/receipt/{order_id}/")
    
    url = f"{BACKEND_URL}/api/orders/receipt/{order_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            if 'text/html' in response.headers.get('Content-Type', ''):
                print(f"   ✅ HTML recibido correctamente ({len(response.text)} caracteres)")
                print(f"   📝 Primeros 200 caracteres:")
                print(f"      {response.text[:200]}...")
                return True
            else:
                print(f"   ⚠️ Content-Type inesperado")
                return False
        elif response.status_code == 403:
            print(f"   ❌ Acceso denegado: No tienes permiso para ver este pedido")
            return False
        elif response.status_code == 404:
            print(f"   ❌ Pedido no encontrado (ID: {order_id})")
            return False
        else:
            print(f"   ❌ Error inesperado: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        return False


def test_pdf_download(order_id, token):
    """
    Prueba 2: Descargar comprobante en formato PDF.
    Este endpoint debe forzar la descarga del archivo.
    """
    print(f"\n📥 TEST 2: Descargar Comprobante PDF")
    print(f"   Endpoint: /api/orders/receipt/{order_id}/pdf/")
    
    url = f"{BACKEND_URL}/api/orders/receipt/{order_id}/pdf/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, stream=True)
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Content-Disposition: {response.headers.get('Content-Disposition')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-Disposition', '')
            
            # Verificar que sea PDF
            if 'application/pdf' not in content_type:
                print(f"   ⚠️ Content-Type no es PDF: {content_type}")
                return False
            
            # Verificar que tenga header de descarga
            if 'attachment' not in content_disposition:
                print(f"   ⚠️ No tiene 'attachment' en Content-Disposition")
                print(f"      Esto significa que el navegador lo abrirá en vez de descargarlo")
                print(f"      Header actual: {content_disposition}")
            else:
                print(f"   ✅ Header de descarga correcto")
            
            # Guardar el PDF
            OUTPUT_DIR.mkdir(exist_ok=True)
            output_path = OUTPUT_DIR / f"comprobante_pedido_{order_id}_test.pdf"
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(output_path)
            print(f"   ✅ PDF guardado exitosamente")
            print(f"   📁 Ubicación: {output_path.absolute()}")
            print(f"   📊 Tamaño: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            
            # Verificar que sea un PDF válido (comienza con %PDF)
            with open(output_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    print(f"   ✅ Archivo PDF válido (header correcto)")
                else:
                    print(f"   ⚠️ No parece ser un PDF válido (header: {header})")
            
            return True
            
        elif response.status_code == 403:
            print(f"   ❌ Acceso denegado: No tienes permiso para descargar este pedido")
            return False
        elif response.status_code == 404:
            print(f"   ❌ Pedido no encontrado (ID: {order_id})")
            return False
        else:
            print(f"   ❌ Error inesperado: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unauthorized_access(order_id):
    """
    Prueba 3: Verificar que sin token no se puede acceder.
    """
    print(f"\n🔒 TEST 3: Verificar Protección de Autenticación")
    
    url = f"{BACKEND_URL}/api/orders/receipt/{order_id}/pdf/"
    
    try:
        response = requests.get(url)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print(f"   ✅ Correctamente protegido: requiere autenticación")
            return True
        else:
            print(f"   ⚠️ Inesperado: debería retornar 401")
            print(f"      Respuesta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        return False


def main():
    """
    Ejecuta todos los tests de los endpoints de comprobantes.
    """
    print("=" * 70)
    print("🧪 TEST DE ENDPOINTS DE COMPROBANTES DE PEDIDOS")
    print("=" * 70)
    print(f"\n📍 Backend URL: {BACKEND_URL}")
    print(f"🆔 Order ID: {ORDER_ID}")
    
    # Verificar configuración
    if EMAIL == "tu_email@ejemplo.com" or PASSWORD == "tu_password":
        print("\n⚠️ ERROR: Debes configurar EMAIL y PASSWORD en el script")
        print("   Edita las variables al inicio del archivo test_pdf_download.py")
        return
    
    # Test 3: Sin autenticación (debe fallar)
    test_unauthorized_access(ORDER_ID)
    
    # Obtener token
    token = get_auth_token(EMAIL, PASSWORD)
    if not token:
        print("\n❌ No se pudo obtener el token. Verifica las credenciales.")
        return
    
    # Test 1: HTML Receipt
    html_ok = test_html_receipt(ORDER_ID, token)
    
    # Test 2: PDF Download
    pdf_ok = test_pdf_download(ORDER_ID, token)
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE TESTS")
    print("=" * 70)
    print(f"   Test 1 (HTML Receipt):       {'✅ PASS' if html_ok else '❌ FAIL'}")
    print(f"   Test 2 (PDF Download):       {'✅ PASS' if pdf_ok else '❌ FAIL'}")
    print("=" * 70)
    
    if html_ok and pdf_ok:
        print("\n🎉 ¡Todos los tests pasaron!")
    else:
        print("\n⚠️ Algunos tests fallaron. Revisa los detalles arriba.")
    
    print("\n💡 DIAGNÓSTICO DEL PROBLEMA:")
    print("   Si el PDF se descarga pero 'no hace la descarga' en el navegador,")
    print("   verifica que el header Content-Disposition contenga 'attachment'.")
    print("   Si dice 'inline', el navegador abrirá el PDF en vez de descargarlo.")


if __name__ == "__main__":
    main()
