"""
Script de testing para la API de notificaciones de SmartSales.
Prueba todos los endpoints principales del sistema de notificaciones.
"""
import requests
import json
from datetime import datetime

# Configuración
BACKEND_URL = "http://localhost:8000"
EMAIL = "admin@smartsales.com"
PASSWORD = "admin123"

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
ENDC = '\033[0m'


def print_test(name):
    print(f"\n{BLUE}{'='*60}{ENDC}")
    print(f"{BLUE}TEST: {name}{ENDC}")
    print(f"{BLUE}{'='*60}{ENDC}")


def print_success(message):
    print(f"{GREEN}✅ {message}{ENDC}")


def print_error(message):
    print(f"{RED}❌ {message}{ENDC}")


def print_info(message):
    print(f"{YELLOW}ℹ️  {message}{ENDC}")


def authenticate():
    """Obtiene un token JWT"""
    print_test("AUTENTICACIÓN")
    
    response = requests.post(
        f"{BACKEND_URL}/api/token/",
        json={"username": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code == 200:
        token = response.json()['access']
        print_success(f"Autenticado como {EMAIL}")
        return token
    else:
        print_error(f"Error de autenticación: {response.status_code}")
        print_error(response.text)
        return None


def test_get_notifications(token):
    """Obtiene la lista de notificaciones"""
    print_test("LISTAR NOTIFICACIONES")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/api/notifications/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 0)
        print_success(f"Notificaciones obtenidas: {count}")
        
        if count > 0:
            print_info("Últimas 3 notificaciones:")
            for notif in data['results'][:3]:
                print(f"   - [{notif['type']}] {notif['title']} - {notif['time_ago']}")
        
        return True
    else:
        print_error(f"Error: {response.status_code}")
        print_error(response.text)
        return False


def test_unread_count(token):
    """Obtiene el conteo de notificaciones no leídas"""
    print_test("CONTEO DE NO LEÍDAS")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/api/notifications/unread_count/", headers=headers)
    
    if response.status_code == 200:
        count = response.json()['unread_count']
        print_success(f"Notificaciones no leídas: {count}")
        return count
    else:
        print_error(f"Error: {response.status_code}")
        return None


def test_send_test_notification(token):
    """Envía una notificación de prueba"""
    print_test("ENVIAR NOTIFICACIÓN DE PRUEBA")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": f"🧪 Test {datetime.now().strftime('%H:%M:%S')}",
        "message": "Esta es una notificación de prueba del sistema SmartSales.",
        "channels": ["IN_APP"]  # Solo IN_APP para evitar emails en testing
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/notifications/test/",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Notificación de prueba enviada")
        print_info(f"Resultados: {json.dumps(data['results'], indent=2)}")
        return True
    else:
        print_error(f"Error: {response.status_code}")
        print_error(response.text)
        return False


def test_get_preferences(token):
    """Obtiene las preferencias de notificación"""
    print_test("OBTENER PREFERENCIAS")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/api/notifications/preferences/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        prefs = data['preferences']
        print_success("Preferencias obtenidas")
        print_info("Preferencias de PEDIDOS:")
        print(f"   - In-App: {prefs['orders_in_app']}")
        print(f"   - Push: {prefs['orders_push']}")
        print(f"   - Email: {prefs['orders_email']}")
        return True
    else:
        print_error(f"Error: {response.status_code}")
        return False


def test_update_preferences(token):
    """Actualiza las preferencias de notificación"""
    print_test("ACTUALIZAR PREFERENCIAS")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "offers_push": True,  # Habilitar push para ofertas
        "system_email": False  # Deshabilitar email para sistema
    }
    
    response = requests.patch(
        f"{BACKEND_URL}/api/notifications/preferences/",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        print_success("Preferencias actualizadas")
        prefs = response.json()['preferences']
        print_info(f"Ofertas Push: {prefs['offers_push']}")
        print_info(f"Sistema Email: {prefs['system_email']}")
        return True
    else:
        print_error(f"Error: {response.status_code}")
        print_error(response.text)
        return False


def test_mark_as_read(token, notification_id):
    """Marca una notificación como leída"""
    print_test(f"MARCAR COMO LEÍDA (ID: {notification_id})")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BACKEND_URL}/api/notifications/{notification_id}/mark_as_read/",
        headers=headers
    )
    
    if response.status_code == 200:
        print_success(f"Notificación {notification_id} marcada como leída")
        return True
    else:
        print_error(f"Error: {response.status_code}")
        return False


def test_statistics(token):
    """Obtiene estadísticas de notificaciones"""
    print_test("ESTADÍSTICAS")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/api/notifications/stats/", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print_success("Estadísticas obtenidas:")
        print(f"   - Total: {stats['total']}")
        print(f"   - No leídas: {stats['unread']}")
        print(f"   - Leídas: {stats['read']}")
        print(f"   - Recientes (24h): {stats['recent_count']}")
        
        if stats.get('by_type'):
            print_info("Por tipo:")
            for tipo, count in stats['by_type'].items():
                print(f"   - {tipo}: {count}")
        
        return True
    else:
        print_error(f"Error: {response.status_code}")
        return False


def test_register_device_token(token):
    """Registra un token FCM de prueba"""
    print_test("REGISTRAR TOKEN FCM")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "token": f"test_token_{datetime.now().timestamp()}",
        "device_type": "WEB",
        "device_name": "Test Device - Chrome"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/notifications/devices/",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 201:
        device = response.json()
        print_success(f"Token registrado (ID: {device['id']})")
        print_info(f"Dispositivo: {device['device_name']}")
        return device['id']
    else:
        print_error(f"Error: {response.status_code}")
        print_error(response.text)
        return None


def test_list_devices(token):
    """Lista los dispositivos registrados"""
    print_test("LISTAR DISPOSITIVOS")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/api/notifications/devices/", headers=headers)
    
    if response.status_code == 200:
        devices = response.json()
        count = len(devices)
        print_success(f"Dispositivos registrados: {count}")
        
        for device in devices[:3]:  # Mostrar solo los primeros 3
            status = "🟢 Activo" if device['is_active'] else "🔴 Inactivo"
            print(f"   - {device['device_name']} ({device['device_type']}) - {status}")
        
        return True
    else:
        print_error(f"Error: {response.status_code}")
        return False


def run_all_tests():
    """Ejecuta todos los tests"""
    print(f"\n{BLUE}{'='*60}{ENDC}")
    print(f"{BLUE}INICIANDO TESTS DE API DE NOTIFICACIONES{ENDC}")
    print(f"{BLUE}{'='*60}{ENDC}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Usuario: {EMAIL}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Autenticar
    token = authenticate()
    if not token:
        print_error("No se pudo autenticar. Abortando tests.")
        return
    
    # 2. Listar notificaciones
    test_get_notifications(token)
    
    # 3. Conteo de no leídas
    unread_count = test_unread_count(token)
    
    # 4. Estadísticas
    test_statistics(token)
    
    # 5. Enviar notificación de prueba
    if test_send_test_notification(token):
        # Verificar que se creó
        test_get_notifications(token)
        new_unread = test_unread_count(token)
        
        if new_unread and unread_count is not None and new_unread > unread_count:
            print_success(f"✅ Nueva notificación creada (no leídas: {unread_count} → {new_unread})")
    
    # 6. Preferencias
    test_get_preferences(token)
    test_update_preferences(token)
    
    # 7. Dispositivos
    device_id = test_register_device_token(token)
    test_list_devices(token)
    
    # 8. Marcar como leída (si hay alguna no leída)
    if unread_count and unread_count > 0:
        # Obtener una notificación no leída
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/api/notifications/?unread=true&limit=1", headers=headers)
        if response.status_code == 200 and response.json()['results']:
            notification_id = response.json()['results'][0]['id']
            test_mark_as_read(token, notification_id)
            # Verificar que el conteo bajó
            test_unread_count(token)
    
    print(f"\n{GREEN}{'='*60}{ENDC}")
    print(f"{GREEN}TESTS COMPLETADOS{ENDC}")
    print(f"{GREEN}{'='*60}{ENDC}\n")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrumpidos por el usuario{ENDC}")
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
