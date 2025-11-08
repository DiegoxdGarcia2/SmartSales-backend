# 🎨 Frontend Integration Guide - Nuevas Funcionalidades ML

## 📍 Cambios a Implementar en el Frontend

### Ubicación del Frontend
```
D:\2doParcialSI2\Frontend\smartsales-frontend>
```

---

## 🤖 1. Nueva Sección: Machine Learning Dashboard

### Crear: `src/pages/MLDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import api from '../services/api'; // Tu instancia de axios configurada

interface ModelInfo {
  status: string;
  model_exists: boolean;
  predictions_exist: boolean;
  model_info?: {
    trained_at: string;
    size_mb: number;
    algorithm: string;
    features_count: number;
    features: string[];
  };
  performance_metrics?: {
    rmse: number;
    mape: number;
    n_train_samples: number;
    n_test_samples: number;
  };
  predictions?: {
    count: number;
    first_month: string;
    last_month: string;
  };
}

interface Prediction {
  month: string;
  predicted_sales: number;
}

interface PredictionsResponse {
  status: string;
  predictions: Prediction[];
  metadata: {
    prediction_count: number;
    first_month: string;
    last_month: string;
    model: {
      algorithm: string;
      trained_at: string;
      rmse: number;
      mape: number;
      accuracy_percentage: number;
    };
  };
}

const MLDashboard: React.FC = () => {
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [predictions, setPredictions] = useState<PredictionsResponse | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingMessage, setTrainingMessage] = useState('');
  const [loading, setLoading] = useState(true);

  // Cargar información del modelo al montar
  useEffect(() => {
    loadModelInfo();
    loadPredictions();
  }, []);

  const loadModelInfo = async () => {
    try {
      const response = await api.get('/analytics/model-info/');
      setModelInfo(response.data);
    } catch (error) {
      console.error('Error al cargar info del modelo:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPredictions = async () => {
    try {
      const response = await api.get('/analytics/predictions/sales/monthly/');
      setPredictions(response.data);
    } catch (error) {
      console.error('Error al cargar predicciones:', error);
    }
  };

  const handleTrainModel = async () => {
    if (!confirm('¿Está seguro de reentrenar el modelo? Esto puede tomar 1-2 minutos.')) {
      return;
    }

    setIsTraining(true);
    setTrainingMessage('Entrenando modelo... Por favor espere.');

    try {
      const response = await api.post('/analytics/train-model/');
      
      if (response.data.status === 'success') {
        setTrainingMessage('✅ Modelo entrenado exitosamente!');
        // Recargar datos
        setTimeout(() => {
          loadModelInfo();
          loadPredictions();
          setTrainingMessage('');
        }, 2000);
      } else {
        setTrainingMessage(`❌ Error: ${response.data.message}`);
      }
    } catch (error: any) {
      setTrainingMessage(`❌ Error al entrenar: ${error.response?.data?.message || error.message}`);
    } finally {
      setIsTraining(false);
    }
  };

  if (loading) {
    return <div className="loading">Cargando información del modelo...</div>;
  }

  return (
    <div className="ml-dashboard">
      <h1>🤖 Dashboard de Machine Learning</h1>

      {/* Card: Estado del Modelo */}
      <div className="card model-status">
        <h2>📊 Estado del Modelo</h2>
        {modelInfo?.status === 'not_trained' ? (
          <div className="alert alert-warning">
            <p>⚠️ El modelo aún no ha sido entrenado.</p>
            <button onClick={handleTrainModel} disabled={isTraining}>
              {isTraining ? 'Entrenando...' : 'Entrenar Modelo'}
            </button>
          </div>
        ) : (
          <div className="model-details">
            <div className="metric">
              <span className="label">Algoritmo:</span>
              <span className="value">{modelInfo?.model_info?.algorithm}</span>
            </div>
            <div className="metric">
              <span className="label">Entrenado:</span>
              <span className="value">
                {modelInfo?.model_info?.trained_at 
                  ? new Date(modelInfo.model_info.trained_at).toLocaleString('es-ES')
                  : 'N/A'}
              </span>
            </div>
            <div className="metric">
              <span className="label">Tamaño:</span>
              <span className="value">{modelInfo?.model_info?.size_mb} MB</span>
            </div>
            <div className="metric">
              <span className="label">Features:</span>
              <span className="value">{modelInfo?.model_info?.features_count}</span>
            </div>
          </div>
        )}
      </div>

      {/* Card: Métricas de Rendimiento */}
      {modelInfo?.performance_metrics && (
        <div className="card performance-metrics">
          <h2>📈 Métricas de Rendimiento</h2>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">RMSE</div>
              <div className="metric-value">
                ${modelInfo.performance_metrics.rmse.toLocaleString('es-ES')}
              </div>
              <div className="metric-description">Error promedio</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">MAPE</div>
              <div className="metric-value">
                {modelInfo.performance_metrics.mape?.toFixed(2)}%
              </div>
              <div className="metric-description">Error porcentual</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Precisión</div>
              <div className="metric-value">
                {predictions?.metadata?.model?.accuracy_percentage?.toFixed(1)}%
              </div>
              <div className="metric-description">Precisión estimada</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Datos</div>
              <div className="metric-value">
                {modelInfo.performance_metrics.n_train_samples}
              </div>
              <div className="metric-description">Muestras de entrenamiento</div>
            </div>
          </div>
        </div>
      )}

      {/* Card: Predicciones */}
      {predictions && predictions.status === 'success' && (
        <div className="card predictions">
          <h2>🔮 Predicciones de Ventas</h2>
          <p className="subtitle">
            {predictions.metadata.prediction_count} meses predichos 
            ({predictions.metadata.first_month} - {predictions.metadata.last_month})
          </p>
          
          <div className="predictions-table">
            <table>
              <thead>
                <tr>
                  <th>Mes</th>
                  <th>Ventas Predichas</th>
                </tr>
              </thead>
              <tbody>
                {predictions.predictions.map((pred) => (
                  <tr key={pred.month}>
                    <td>{pred.month}</td>
                    <td>${pred.predicted_sales.toLocaleString('es-ES', { minimumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Gráfica (opcional - usar recharts o chart.js) */}
          {/* <LineChart data={predictions.predictions} /> */}
        </div>
      )}

      {/* Botón de Reentrenamiento */}
      {modelInfo?.model_exists && (
        <div className="card actions">
          <h2>⚙️ Acciones</h2>
          <button 
            onClick={handleTrainModel} 
            disabled={isTraining}
            className="btn btn-primary"
          >
            {isTraining ? '🔄 Entrenando...' : '🔄 Reentrenar Modelo'}
          </button>
          {trainingMessage && (
            <div className={`message ${trainingMessage.includes('✅') ? 'success' : 'error'}`}>
              {trainingMessage}
            </div>
          )}
          <p className="help-text">
            💡 Reentrenar el modelo con los datos más recientes puede mejorar la precisión de las predicciones.
          </p>
        </div>
      )}
    </div>
  );
};

export default MLDashboard;
```

### CSS: `src/pages/MLDashboard.css`

```css
.ml-dashboard {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.ml-dashboard h1 {
  font-size: 2rem;
  margin-bottom: 2rem;
  color: #1a202c;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.card h2 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #2d3748;
}

/* Estado del Modelo */
.model-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.metric {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
  background: #f7fafc;
  border-radius: 4px;
}

.metric .label {
  font-size: 0.875rem;
  color: #718096;
  margin-bottom: 0.25rem;
}

.metric .value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
}

/* Métricas de Rendimiento */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.metric-card {
  text-align: center;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.metric-label {
  font-size: 0.875rem;
  opacity: 0.9;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.metric-description {
  font-size: 0.75rem;
  opacity: 0.8;
}

/* Predicciones */
.predictions-table {
  overflow-x: auto;
  margin-top: 1rem;
}

.predictions-table table {
  width: 100%;
  border-collapse: collapse;
}

.predictions-table th,
.predictions-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.predictions-table th {
  background: #edf2f7;
  font-weight: 600;
  color: #4a5568;
}

.predictions-table tbody tr:hover {
  background: #f7fafc;
}

/* Botones */
.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #4299e1;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #3182ce;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(66, 153, 225, 0.4);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Mensajes */
.message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.message.success {
  background: #c6f6d5;
  color: #22543d;
}

.message.error {
  background: #fed7d7;
  color: #742a2a;
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.alert-warning {
  background: #fef5e7;
  color: #d68910;
  border-left: 4px solid #f39c12;
}

.help-text {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #718096;
}

.loading {
  text-align: center;
  padding: 3rem;
  font-size: 1.25rem;
  color: #718096;
}
```

---

## 🔗 2. Agregar Ruta en el Router

En `src/App.tsx` o tu archivo de rutas:

```typescript
import MLDashboard from './pages/MLDashboard';

// Dentro de tus rutas:
<Route path="/ml-dashboard" element={<MLDashboard />} />
```

## 🧭 3. Agregar Link en el Menú de Navegación

```tsx
<NavLink to="/ml-dashboard">
  🤖 Machine Learning
</NavLink>
```

---

## 📄 4. Integrar en Página de Pedidos (Descarga PDF)

En tu componente de detalle de pedido (`OrderDetail.tsx` o similar):

```typescript
const handleDownloadPDF = async (orderId: number) => {
  try {
    // Solicitar el PDF como blob
    const response = await api.get(`/orders/receipt/${orderId}/pdf/`, {
      responseType: 'blob', // ¡IMPORTANTE! Esto indica que es un archivo binario
      headers: {
        'Accept': 'application/pdf',
      }
    });
    
    // Verificar que sea un PDF
    const contentType = response.headers['content-type'];
    if (!contentType || !contentType.includes('application/pdf')) {
      throw new Error('La respuesta no es un PDF válido');
    }
    
    // Crear Blob con el tipo correcto
    const blob = new Blob([response.data], { type: 'application/pdf' });
    
    // Obtener nombre del archivo del header Content-Disposition (si existe)
    const contentDisposition = response.headers['content-disposition'];
    let filename = `comprobante_pedido_${orderId}.pdf`;
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }
    
    // Crear URL temporal para el blob
    const url = window.URL.createObjectURL(blob);
    
    // Crear elemento <a> invisible para forzar descarga
    const link = document.createElement('a');
    link.href = url;
    link.download = filename; // Nombre del archivo a descargar
    link.style.display = 'none';
    
    // Agregar al DOM, hacer click y remover
    document.body.appendChild(link);
    link.click();
    
    // Limpiar después de un pequeño delay
    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    }, 100);
    
    // Notificación de éxito
    console.log(`✅ PDF descargado: ${filename}`);
    // Opcional: usar una librería de notificaciones en vez de alert
    // toast.success('Comprobante descargado exitosamente');
    
  } catch (error: any) {
    console.error('Error al descargar PDF:', error);
    
    // Manejo específico de errores
    if (error.response?.status === 403) {
      alert('❌ No tienes permiso para descargar este comprobante');
    } else if (error.response?.status === 404) {
      alert('❌ Pedido no encontrado');
    } else {
      alert('❌ Error al descargar el comprobante. Intenta de nuevo.');
    }
  }
};

// OPCIÓN 2: Con manejo de loading state
const [isDownloading, setIsDownloading] = useState(false);

const handleDownloadPDFWithLoading = async (orderId: number) => {
  setIsDownloading(true);
  
  try {
    const response = await api.get(`/orders/receipt/${orderId}/pdf/`, {
      responseType: 'blob',
      headers: { 'Accept': 'application/pdf' },
    });
    
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `comprobante_pedido_${orderId}.pdf`;
    document.body.appendChild(link);
    link.click();
    
    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    }, 100);
    
  } catch (error) {
    console.error('Error:', error);
    alert('❌ Error al descargar el comprobante');
  } finally {
    setIsDownloading(false);
  }
};

// En el JSX:
<button 
  onClick={() => handleDownloadPDF(order.id)}
  disabled={isDownloading}
  className="btn-download-pdf"
>
  {isDownloading ? (
    <>
      <span className="spinner"></span>
      Descargando...
    </>
  ) : (
    <>
      📄 Descargar Comprobante PDF
    </>
  )}
</button>

// OPCIÓN 3: Con dos botones (Ver y Descargar)
<div className="receipt-actions">
  {/* Ver en nueva pestaña */}
  <button 
    onClick={() => window.open(`/api/orders/receipt/${order.id}/`, '_blank')}
    className="btn-view"
  >
    👁️ Ver Comprobante
  </button>
  
  {/* Descargar PDF */}
  <button 
    onClick={() => handleDownloadPDF(order.id)}
    className="btn-download"
  >
    📥 Descargar PDF
  </button>
</div>
```

### 🔧 Configuración de Axios (api.ts)

Asegúrate de que tu instancia de axios esté configurada correctamente:

```typescript
// src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://smartsales-backend-891739940726.us-central1.run.app/api',
  // baseURL: 'http://localhost:8000/api', // Para desarrollo local
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token'); // O donde guardes el token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado o inválido
      console.log('Token inválido, redirigiendo a login...');
      // localStorage.removeItem('access_token');
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## 🧪 PRUEBAS A REALIZAR

### ✅ 1. Pruebas de Machine Learning Dashboard

#### Test 1.1: Cargar Información del Modelo
```bash
Pasos:
1. Ir a http://localhost:3039/ml-dashboard
2. Verificar que se muestra:
   - Estado del modelo (entrenado/no entrenado)
   - Fecha de entrenamiento
   - Algoritmo (RandomForestRegressor)
   - Métricas (RMSE, MAPE, Precisión)
   
Resultado Esperado:
✅ Se muestra toda la información correctamente
✅ Métricas tienen valores numéricos
✅ Fecha de entrenamiento en formato local
```

#### Test 1.2: Ver Predicciones
```bash
Pasos:
1. En el dashboard, verificar sección "Predicciones de Ventas"
2. Verificar que se muestran 6 meses futuros
3. Verificar formato de montos (con separadores de miles)

Resultado Esperado:
✅ Se muestran 6 predicciones
✅ Fechas en formato YYYY-MM
✅ Montos con formato $ y decimales
```

#### Test 1.3: Reentrenar Modelo
```bash
Pasos:
1. Click en botón "🔄 Reentrenar Modelo"
2. Confirmar diálogo
3. Esperar 30-60 segundos
4. Verificar mensaje de éxito

Resultado Esperado:
✅ Botón muestra "Entrenando..." mientras procesa
✅ Mensaje "✅ Modelo entrenado exitosamente!"
✅ Métricas se actualizan automáticamente
✅ Nueva fecha de entrenamiento
```

### ✅ 2. Pruebas de Descarga de PDF

#### Test 2.1: Descargar Comprobante Exitoso
```bash
Pasos:
1. Ir a detalle de un pedido PAGADO (ej: /order/1880)
2. Click en "📄 Descargar Comprobante PDF"
3. Verificar descarga automática

Resultado Esperado:
✅ Se descarga archivo comprobante_pedido_XXXX.pdf
✅ PDF contiene:
   - Logo de SmartSales
   - Información del pedido (ID, fecha, estado)
   - Tabla de productos
   - Total del pedido
   - Información de garantías
```

#### Test 2.2: Verificar Permisos
```bash
Pasos:
1. Como usuario normal, intentar descargar comprobante de OTRO usuario
2. Verificar error 403

Resultado Esperado:
✅ Error: "No tienes permiso para descargar este comprobante"
✅ Solo el dueño del pedido o admin puede descargar
```

### ✅ 3. Pruebas de Análisis de Sentimiento (Reseñas)

#### Test 3.1: Crear Reseña con Análisis Gemini
```bash
Pasos:
1. Comprar un producto
2. Dejar reseña con comentario detallado:
   "Excelente producto, muy buena calidad. El precio es justo, 
    aunque la entrega tardó un poco más de lo esperado."
3. Verificar respuesta de la API

Resultado Esperado en Response:
✅ sentiment: "POSITIVO"
✅ sentiment_confidence: ~0.85-0.95
✅ sentiment_summary: "Cliente satisfecho con la calidad..."
✅ aspect_quality: 5
✅ aspect_value: 4
✅ aspect_delivery: 3
✅ keywords: ["excelente", "calidad", "precio justo", "entrega tardó"]
```

#### Test 3.2: Mostrar Análisis en Frontend
```bash
Pasos:
1. Ver detalle de producto con reseñas
2. Verificar que se muestran nuevos campos:
   - Badge de sentimiento (POSITIVO/NEUTRO/NEGATIVO)
   - Confianza del análisis
   - Resumen automático
   - Aspectos (calidad, valor, entrega) con estrellas
   - Keywords como tags

Resultado Esperado:
✅ Se visualizan todos los campos nuevos
✅ UI intuitiva y profesional
```

### ✅ 4. Pruebas de Reportes Dinámicos (Verificar que sigue funcionando)

#### Test 4.1: Lenguaje Natural Escrito
```bash
Pasos:
1. Ir a sección de reportes
2. Ingresar: "ventas de lavadoras samsung de los últimos 6 meses en formato json"
3. Verificar respuesta

Resultado Esperado:
✅ Retorna JSON (no Excel)
✅ Filtra por categoría Lavadoras
✅ Filtra por marca Samsung
✅ Rango de 6 meses
```

#### Test 4.2: Reportes por Voz
```bash
Pasos:
1. Click en botón de micrófono
2. Decir: "dame las ventas de televisores samsung del último mes"
3. Verificar procesamiento

Resultado Esperado:
✅ Audio se transcribe correctamente
✅ Gemini parsea los parámetros
✅ Retorna datos correctos en JSON/Excel/PDF
```

---

## 🐛 Troubleshooting

### Error: "401 Unauthorized" en ML Dashboard
**Solución**: Verificar que el token JWT está incluido en headers de api.ts

### Error: PDF no se descarga
**Solución**: Asegurar `responseType: 'blob'` en el request de axios

### Error: Modelo no entrenado
**Solución**: Ir a /ml-dashboard y click en "Entrenar Modelo"

### Error: Reentrenamiento tarda mucho
**Normal**: El proceso puede tomar 30-60 segundos. No cerrar el navegador.

---

## 📚 URLs de Prueba en Producción

```
Backend Base URL:
https://smartsales-backend-891739940726.us-central1.run.app

Endpoints Nuevos:
- GET  /api/analytics/model-info/
- POST /api/analytics/train-model/
- GET  /api/analytics/predictions/sales/monthly/
- GET  /api/orders/receipt/<order_id>/pdf/

Frontend (supuesto):
http://localhost:3039
```

---

## ✅ Checklist de Integración

- [ ] Crear componente MLDashboard.tsx
- [ ] Añadir estilos MLDashboard.css
- [ ] Agregar ruta /ml-dashboard al router
- [ ] Añadir link en menú de navegación
- [ ] Implementar descarga de PDF en OrderDetail
- [ ] Actualizar componente de reseñas para mostrar análisis Gemini
- [ ] Probar cada funcionalidad según la guía
- [ ] Verificar que reportes dinámicos siguen funcionando

---

**¡Listo para integrar! 🚀**
