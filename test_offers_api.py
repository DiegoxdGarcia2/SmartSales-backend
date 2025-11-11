"""
Script para probar el sistema de ofertas de SmartSales.
Prueba creación de ofertas, aplicación a carrito, tracking y notificaciones.
"""
import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000/api"
USERNAME = "admin"  # Cambiar por tu usuario admin
PASSWORD = "admin"  # Cambiar por tu contraseña

class OffersAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        self.test_results = []
    
    def log_test(self, test_name, success, response_data=None, error=None):
        """Registra el resultado de una prueba"""
        result = {
            'test': test_name,
            'success': success,
            'response': response_data,
            'error': str(error) if error else None
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status}: {test_name}")
        if response_data:
            print(f"Response: {json.dumps(response_data, indent=2)}")
        if error:
            print(f"Error: {error}")
    
    def authenticate(self):
        """Autenticación"""
        print("\n" + "="*60)
        print("🔐 AUTENTICACIÓN")
        print("="*60)
        
        try:
            response = self.session.post(
                f"{BASE_URL}/token/",
                json={"username": USERNAME, "password": PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access']
                self.user_id = data['user']['id']
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                self.log_test("Autenticación", True, data)
                return True
            else:
                self.log_test("Autenticación", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Autenticación", False, error=str(e))
            return False
    
    def test_create_offer(self):
        """Prueba crear una oferta"""
        print("\n" + "="*60)
        print("🎁 CREAR OFERTA")
        print("="*60)
        
        # Fecha de inicio: ahora
        # Fecha de fin: 7 días después
        start_date = datetime.now().isoformat()
        end_date = (datetime.now() + timedelta(days=7)).isoformat()
        
        offer_data = {
            "name": "Oferta de Prueba - Black Friday",
            "description": "Descuento especial en productos seleccionados",
            "offer_type": "SEASONAL",
            "discount_percentage": "25.00",
            "start_date": start_date,
            "end_date": end_date,
            "status": "DRAFT",
            "max_uses": 100,
            "max_uses_per_user": 2,
            "min_purchase_amount": "50.00",
            "priority": 10,
            "product_ids": [1, 2, 3]  # IDs de productos existentes
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/offers/offers/",
                json=offer_data
            )
            
            if response.status_code == 201:
                data = response.json()
                self.offer_id = data['id']
                self.log_test("Crear oferta", True, data)
                return data['id']
            else:
                self.log_test("Crear oferta", False, error=f"{response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Crear oferta", False, error=str(e))
            return None
    
    def test_list_offers(self):
        """Prueba listar ofertas"""
        print("\n" + "="*60)
        print("📋 LISTAR OFERTAS")
        print("="*60)
        
        try:
            response = self.session.get(f"{BASE_URL}/offers/offers/")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(f"Listar ofertas ({len(data)} encontradas)", True, data)
                return True
            else:
                self.log_test("Listar ofertas", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Listar ofertas", False, error=str(e))
            return False
    
    def test_activate_offer(self, offer_id):
        """Prueba activar una oferta"""
        print("\n" + "="*60)
        print("⚡ ACTIVAR OFERTA")
        print("="*60)
        
        try:
            response = self.session.post(
                f"{BASE_URL}/offers/offers/{offer_id}/activate/",
                json={"notify_users": False}  # No notificar en pruebas
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Activar oferta", True, data)
                return True
            else:
                self.log_test("Activar oferta", False, error=f"{response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Activar oferta", False, error=str(e))
            return False
    
    def test_get_my_offers(self):
        """Prueba obtener ofertas del usuario"""
        print("\n" + "="*60)
        print("🎯 MIS OFERTAS")
        print("="*60)
        
        try:
            response = self.session.get(f"{BASE_URL}/offers/offers/my_offers/")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(f"Mis ofertas ({len(data)} disponibles)", True, data)
                return True
            else:
                self.log_test("Mis ofertas", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Mis ofertas", False, error=str(e))
            return False
    
    def test_track_view(self, offer_id):
        """Prueba registrar vista de oferta"""
        print("\n" + "="*60)
        print("👁 REGISTRAR VISTA")
        print("="*60)
        
        try:
            response = self.session.get(f"{BASE_URL}/offers/offers/{offer_id}/track_view/")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Registrar vista", True, data)
                return True
            else:
                self.log_test("Registrar vista", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Registrar vista", False, error=str(e))
            return False
    
    def test_track_click(self, offer_id):
        """Prueba registrar click en oferta"""
        print("\n" + "="*60)
        print("🖱 REGISTRAR CLICK")
        print("="*60)
        
        try:
            response = self.session.post(
                f"{BASE_URL}/offers/offers/{offer_id}/track_click/",
                json={"product_id": 1}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Registrar click", True, data)
                return True
            else:
                self.log_test("Registrar click", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Registrar click", False, error=str(e))
            return False
    
    def test_apply_to_cart(self, offer_id):
        """Prueba aplicar oferta al carrito"""
        print("\n" + "="*60)
        print("🛒 APLICAR OFERTA AL CARRITO")
        print("="*60)
        
        cart_data = {
            "offer_id": offer_id,
            "cart_total": "100.00",
            "product_ids": [1, 2]
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/offers/offers/apply_to_cart/",
                json=cart_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Aplicar oferta al carrito", True, data)
                return True
            else:
                self.log_test("Aplicar oferta al carrito", False, error=f"{response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Aplicar oferta al carrito", False, error=str(e))
            return False
    
    def test_offer_stats(self):
        """Prueba obtener estadísticas de ofertas"""
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DE OFERTAS")
        print("="*60)
        
        try:
            response = self.session.get(f"{BASE_URL}/offers/offers/stats/")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Estadísticas de ofertas", True, data)
                return True
            else:
                self.log_test("Estadísticas de ofertas", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Estadísticas de ofertas", False, error=str(e))
            return False
    
    def test_get_offer_detail(self, offer_id):
        """Prueba obtener detalle de oferta"""
        print("\n" + "="*60)
        print("🔍 DETALLE DE OFERTA")
        print("="*60)
        
        try:
            response = self.session.get(f"{BASE_URL}/offers/offers/{offer_id}/")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Detalle de oferta", True, data)
                return True
            else:
                self.log_test("Detalle de oferta", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Detalle de oferta", False, error=str(e))
            return False
    
    def test_deactivate_offer(self, offer_id):
        """Prueba desactivar una oferta"""
        print("\n" + "="*60)
        print("⏸ DESACTIVAR OFERTA")
        print("="*60)
        
        try:
            response = self.session.post(f"{BASE_URL}/offers/offers/{offer_id}/deactivate/")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Desactivar oferta", True, data)
                return True
            else:
                self.log_test("Desactivar oferta", False, error=response.text)
                return False
                
        except Exception as e:
            self.log_test("Desactivar oferta", False, error=str(e))
            return False
    
    def print_summary(self):
        """Imprime resumen de pruebas"""
        print("\n" + "="*60)
        print("📈 RESUMEN DE PRUEBAS")
        print("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['success'])
        failed = total - passed
        
        print(f"\nTotal de pruebas: {total}")
        print(f"✅ Exitosas: {passed}")
        print(f"❌ Fallidas: {failed}")
        print(f"📊 Tasa de éxito: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n⚠️ Pruebas fallidas:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['error']}")
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        print("\n" + "="*60)
        print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE OFERTAS")
        print("="*60)
        
        # Autenticación
        if not self.authenticate():
            print("\n❌ Error de autenticación. Verifica las credenciales.")
            return
        
        # Crear oferta
        offer_id = self.test_create_offer()
        if not offer_id:
            print("\n⚠️ No se pudo crear oferta. Algunas pruebas no se ejecutarán.")
            return
        
        # Ejecutar pruebas
        self.test_list_offers()
        self.test_activate_offer(offer_id)
        self.test_get_my_offers()
        self.test_get_offer_detail(offer_id)
        self.test_track_view(offer_id)
        self.test_track_click(offer_id)
        self.test_apply_to_cart(offer_id)
        self.test_offer_stats()
        self.test_deactivate_offer(offer_id)
        
        # Resumen
        self.print_summary()


if __name__ == "__main__":
    tester = OffersAPITester()
    tester.run_all_tests()
