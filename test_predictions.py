import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
import requests

User = get_user_model()

# Verificar si existe el superusuario
if not User.objects.filter(email='admin@smartsales.com').exists():
    print("Creando superusuario...")
    User.objects.create_superuser(
        username='admin',
        email='admin@smartsales.com',
        password='admin123',
        first_name='Admin',
        last_name='SmartSales'
    )
    print("✅ Superusuario creado: admin@smartsales.com / admin123")
else:
    print("✅ Superusuario ya existe: admin@smartsales.com")

# Obtener token
print("\n🔑 Obteniendo token de autenticación...")
response = requests.post('http://127.0.0.1:8000/api/token/', json={
    'username': 'admin',
    'password': 'admin123'
})

if response.status_code == 200:
    token = response.json()['access']
    print(f"✅ Token obtenido exitosamente")
    
    # Probar endpoint de predicciones
    print("\n📊 Probando endpoint de predicciones...")
    headers = {'Authorization': f'Bearer {token}'}
    predictions_response = requests.get(
        'http://127.0.0.1:8000/api/analytics/predictions/sales/monthly/',
        headers=headers
    )
    
    if predictions_response.status_code == 200:
        data = predictions_response.json()
        print(f"\n✅ Predicciones obtenidas exitosamente!")
        print(f"\n📅 Último mes histórico: {data['model_info']['last_historical_month']}")
        print(f"🔮 Predicciones para los próximos {data['model_info']['prediction_months']} meses:\n")
        
        for pred in data['predictions']:
            print(f"  • {pred['month']}: ${pred['predicted_sales']:,.2f}")
    else:
        print(f"\n❌ Error al obtener predicciones: {predictions_response.status_code}")
        print(predictions_response.json())
else:
    print(f"❌ Error al obtener token: {response.status_code}")
    print(response.json())
