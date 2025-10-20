# 🚀 SmartSales365 - Backend

API REST para el sistema de gestión de ventas **SmartSales365**, desarrollado con Django REST Framework, PostgreSQL y autenticación JWT.

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

- ✅ **Autenticación JWT** con tokens de acceso y refresco
- ✅ **Modelo de usuario personalizado** con roles (ADMINISTRADOR, CLIENTE)
- ✅ **Registro de usuarios** con validación de contraseñas
- ✅ **Documentación automática** con Swagger/OpenAPI
- ✅ **CORS configurado** para integración con frontend React
- ✅ **Base de datos PostgreSQL** para producción
- ✅ **Django REST Framework** para APIs robustas

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
│   ├── settings.py              # Configuración de Django
│   ├── urls.py                  # URLs principales
│   ├── wsgi.py                  # Configuración WSGI
│   └── asgi.py                  # Configuración ASGI
│
├── users/                       # App de gestión de usuarios
│   ├── migrations/              # Migraciones de base de datos
│   ├── models.py               # Modelo User personalizado
│   ├── serializers.py          # Serializers (UserSerializer, RegisterSerializer)
│   ├── views.py                # Vistas (RegisterView)
│   ├── urls.py                 # URLs de la app users
│   └── admin.py                # Configuración del admin
│
├── .gitignore                   # Archivos ignorados por Git
├── requirements.txt             # Dependencias del proyecto
├── manage.py                    # Script de gestión de Django
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

### 🔜 FASE 2: Gestión de Productos (Próximamente)

- [ ] Modelo de Productos
- [ ] CRUD de productos
- [ ] Categorías y filtros
- [ ] Gestión de inventario

### 🔜 FASE 3: Gestión de Ventas (Próximamente)

- [ ] Modelo de Ventas y Detalles
- [ ] Carrito de compras
- [ ] Proceso de checkout
- [ ] Historial de ventas

### 🔜 FASE 4: Reportes y Analytics (Próximamente)

- [ ] Dashboard de ventas
- [ ] Reportes en PDF
- [ ] Estadísticas y gráficos
- [ ] Análisis de productos más vendidos

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
