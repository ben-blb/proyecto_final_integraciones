# Asistente de Seguimiento de Compras y Pagos

Prueba de concepto de un asistente conversacional capaz de registrar y consultar información básica de un flujo de compras mediante lenguaje natural.

El sistema utiliza:

* Python
* Streamlit
* LangChain
* OpenAI
* Model Context Protocol (MCP)
* FastMCP
* SQLite
* LangGraph para memoria conversacional

> Esta aplicación es una prueba de concepto académica. No pretende sustituir un ERP, un sistema contable ni una plataforma productiva de cuentas por pagar.

---

## Descripción

La información relacionada con una compra suele estar distribuida entre diferentes documentos:

```text
Proveedor
   ↓
Requisición
   ↓
Orden de compra
   ↓
Factura
   ↓
Vencimiento
   ↓
Pago
```

Esta PoC permite registrar una versión simplificada de esos documentos y consultar su trazabilidad mediante una interfaz conversacional.

El agente interpreta la solicitud del usuario, selecciona la tool MCP adecuada, consulta o modifica la base de datos y presenta una respuesta comprensible junto con evidencia de las tools utilizadas.

---

## Funcionalidades

El asistente permite:

* Registrar proveedores.
* Consultar proveedores.
* Crear requisiciones.
* Consultar requisiciones.
* Crear órdenes de compra.
* Registrar facturas.
* Calcular fechas de vencimiento.
* Registrar pagos completos.
* Consultar la trazabilidad completa de una compra.
* Consultar facturas próximas a vencer.
* Mantener referencias dentro de una misma conversación.
* Mostrar las tools MCP utilizadas.
* Solicitar confirmación antes de cualquier operación de escritura.

---

## Alcance

### Incluido

* Proveedores.
* Requisiciones simplificadas.
* Órdenes de compra.
* Facturas.
* Cálculo de vencimientos.
* Pagos completos.
* Consultas de trazabilidad.
* Consulta de próximos vencimientos.
* Memoria de corto plazo por sesión.
* Confirmación explícita para escrituras.
* Datos ficticios almacenados en SQLite.
* Interfaz web con Streamlit.
* Servidor MCP propio.
* Pruebas automatizadas básicas.

### Fuera de alcance

* Actualización de registros.
* Eliminación de registros.
* Cancelaciones.
* Autorizaciones multinivel.
* Usuarios y roles reales.
* Pagos parciales.
* Anticipos.
* Notas de crédito.
* Facturación parcial.
* Archivos adjuntos.
* Integración bancaria.
* Contabilidad.
* Presupuestos.
* Multiempresa.
* Auditoría productiva.
* Integraciones con sistemas externos.

---

## Arquitectura

```text
Usuario
   ↓
Streamlit
   ↓
Agente LangChain + OpenAI
   ↓
Cliente MCP
   ↓
Servidor FastMCP
   ↓
Servicios de negocio
   ↓
SQLite
```

### Responsabilidad de cada componente

#### Streamlit

* Presenta la interfaz de chat.
* Mantiene el identificador de sesión.
* Muestra el historial.
* Presenta las respuestas del agente.
* Muestra evidencia y llamadas a tools.
* Permite reiniciar la conversación.

#### Agente LangChain

* Interpreta las solicitudes.
* Selecciona las tools MCP.
* Solicita datos faltantes.
* Mantiene referencias dentro de la sesión.
* Pide confirmación antes de escrituras.
* Resume los resultados obtenidos.

#### Servidor MCP

* Expone las operaciones del dominio como tools.
* Define parámetros tipados.
* Valida entradas.
* Ejecuta las reglas de negocio.
* Devuelve respuestas estructuradas.

#### SQLite

* Persiste proveedores.
* Persiste requisiciones.
* Persiste órdenes de compra.
* Persiste facturas.
* Persiste pagos.

---

## Estructura del proyecto

```text
asistente_compras_poc/
├── app_streamlit.py
├── agent_core.py
├── mcp_server.py
├── database.py
├── services.py
├── seed_data.py
├── data/
│   └── compras.db
├── tests/
│   ├── test_services.py
│   ├── test_mcp.py
│   └── test_agent.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Archivos principales

| Archivo            | Responsabilidad                         |
| ------------------ | --------------------------------------- |
| `app_streamlit.py` | Interfaz conversacional                 |
| `agent_core.py`    | Configuración y ejecución del agente    |
| `mcp_server.py`    | Servidor FastMCP y definición de tools  |
| `services.py`      | Reglas de negocio                       |
| `database.py`      | Conexión, tablas y transacciones SQLite |
| `seed_data.py`     | Datos ficticios para demostración       |
| `tests/`           | Pruebas automatizadas                   |

---

## Tools MCP

### Tools de escritura

Todas requieren confirmación explícita.

| Tool                  | Descripción                                     |
| --------------------- | ----------------------------------------------- |
| `registrar_proveedor` | Registra un proveedor y sus condiciones de pago |
| `crear_requisicion`   | Crea una requisición simplificada               |
| `crear_orden_compra`  | Genera una orden desde una requisición          |
| `registrar_factura`   | Registra una factura y calcula su vencimiento   |
| `registrar_pago`      | Registra el pago completo de una factura        |

### Tools de lectura

| Tool                            | Descripción                                  |
| ------------------------------- | -------------------------------------------- |
| `consultar_proveedor`           | Busca un proveedor por ID, RFC o nombre      |
| `consultar_requisicion`         | Consulta una requisición por folio           |
| `consultar_trazabilidad_compra` | Recupera la cadena completa de una compra    |
| `listar_pagos_por_vencer`       | Lista facturas pendientes dentro de un rango |

---

## Reglas de negocio

### Proveedores

* El nombre es obligatorio.
* El RFC es obligatorio y no puede repetirse.
* La condición de pago debe ser `contado` o `credito`.
* Un proveedor de contado debe tener cero días de crédito.
* Un proveedor a crédito debe tener más de cero días de crédito.

### Requisiciones

* Se crean directamente con estado `Autorizada`.
* Solo tienen una descripción o partida simplificada.
* El importe estimado debe ser mayor que cero.
* Cada requisición puede tener una sola orden de compra.

### Órdenes de compra

* La requisición debe existir.
* La requisición debe estar autorizada.
* El proveedor debe existir.
* No puede existir otra orden para la misma requisición.
* El importe debe ser mayor que cero.

### Facturas

* La orden de compra debe existir.
* Cada orden puede tener una sola factura.
* La fecha debe utilizar formato ISO:

```text
AAAA-MM-DD
```

* El total debe ser consistente:

```text
subtotal + impuestos = total
```

* Para proveedores de contado:

```text
fecha_vencimiento = fecha_factura
```

* Para proveedores a crédito:

```text
fecha_vencimiento = fecha_factura + dias_credito
```

### Pagos

* La factura debe existir.
* La factura no debe estar pagada.
* Solo se permiten pagos completos.
* El importe debe coincidir con el total de la factura.
* El medio debe pertenecer al catálogo permitido:

```text
transferencia
efectivo
tarjeta
cheque
```

---

## Estados

### Requisición

```text
Autorizada
En compra
Facturada
Pagada
```

### Orden de compra

```text
Emitida
Facturada
Pagada
```

### Factura

```text
Pendiente
Vencida
Pagada
```

Los estados se actualizan internamente cuando se crean documentos posteriores.

Por ejemplo:

```text
crear_orden_compra
→ requisición: En compra

registrar_factura
→ requisición: Facturada
→ orden: Facturada

registrar_pago
→ requisición: Pagada
→ orden: Pagada
→ factura: Pagada
```

---

## Confirmación de operaciones

El agente no debe realizar una escritura inmediatamente después de recibir la solicitud.

Primero debe:

1. Reunir todos los datos necesarios.
2. Resumir la operación.
3. Solicitar confirmación.
4. Ejecutar la tool únicamente después de recibir una confirmación explícita.

Ejemplo:

```text
Usuario:
Registra al proveedor Mobiliario Central con RFC MCE010101ABC
y 30 días de crédito.

Agente:
Se registrará Mobiliario Central con condición de crédito
a 30 días. ¿Confirmas?

Usuario:
Sí, confirma.
```

La confirmación aplica únicamente a la acción pendiente dentro de la misma sesión.

---

## Requisitos

* Python 3.11 o superior.
* Una clave de API de OpenAI.
* Acceso local a los puertos utilizados por Streamlit y el servidor MCP.

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd asistente_compras_poc
```

### 2. Crear el entorno virtual

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Configura:

```env
OPENAI_API_KEY=tu_clave_de_openai
OPENAI_MODEL=nombre_del_modelo
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
DATABASE_PATH=data/compras.db
```

No publiques el archivo `.env`.

---

## Inicialización de la base de datos

Para crear las tablas:

```bash
python database.py
```

Para cargar datos ficticios:

```bash
python seed_data.py
```

La base se creará en:

```text
data/compras.db
```

---

## Ejecución

La aplicación requiere dos procesos.

### Terminal 1: servidor MCP

```bash
source .venv/bin/activate
python mcp_server.py
```

El servidor estará disponible en:

```text
http://127.0.0.1:8000/mcp
```

### Terminal 2: interfaz Streamlit

```bash
source .venv/bin/activate
streamlit run app_streamlit.py
```

La interfaz estará disponible normalmente en:

```text
http://localhost:8501
```

---

## Flujo de demostración

Ejecuta los siguientes mensajes dentro de la misma conversación.

### 1. Crear proveedor

```text
Registra al proveedor Mobiliario Central con RFC MCE010101ABC
y 30 días de crédito.
```

```text
Sí, confirma.
```

### 2. Crear requisición

```text
Crea una requisición para mobiliario por $18,500 MXN,
solicitada por Ana Torres, del área de Operaciones,
tipo Compra operativa.
```

```text
Confirma.
```

### 3. Crear orden de compra

```text
Crea una orden para esa requisición usando el proveedor anterior
por $18,500 MXN.
```

```text
Confirma.
```

### 4. Registrar factura

```text
Registra la factura F-9085 para esa orden, con fecha 2026-07-26,
subtotal $18,500, impuestos $2,960 y total $21,460 MXN.
```

```text
Confirma.
```

### 5. Registrar pago

```text
Registra el pago completo de esa factura por transferencia,
con fecha 2026-08-20 y referencia TRX-1005.
```

```text
Sí, confirma el pago.
```

### 6. Consultar trazabilidad

```text
Muéstrame toda la trazabilidad de esa requisición.
```

El resultado esperado es:

```text
Proveedor
→ Requisición Pagada
→ Orden Pagada
→ Factura Pagada
→ Pago registrado
```

---

## Ejemplos de consulta

### Consultar una requisición

```text
¿Cuál es el estado de la requisición REQ-0003?
```

### Consultar trazabilidad

```text
Muéstrame toda la trazabilidad de REQ-0003.
```

### Consultar vencimiento

```text
¿Cuándo vence la factura asociada a REQ-0003?
```

### Consultar pagos próximos

```text
¿Qué pagos vencen en los próximos siete días?
```

### Consultar proveedor

```text
Busca al proveedor con RFC MCE010101ABC.
```

---

## Memoria conversacional

La aplicación mantiene memoria de corto plazo mediante un identificador de sesión.

Esto permite utilizar referencias como:

```text
esa requisición
el proveedor anterior
esa orden
esa factura
su vencimiento
págala
```

Ejemplo:

```text
Usuario:
Consulta REQ-0003.

Usuario:
Ahora muéstrame toda su trazabilidad.
```

Mientras se mantenga el mismo `session_id`, el agente debe conservar la referencia a `REQ-0003`.

La memoria actual es temporal y se pierde cuando se reinicia el proceso.

---

## Pruebas

Ejecuta todas las pruebas:

```bash
pytest -q
```

---

## Escenarios mínimos de prueba

### Consulta directa

```text
¿Cuál es el estado de REQ-0003?
```

Resultado esperado:

* Utiliza `consultar_requisicion`.
* Devuelve información de la base.
* No inventa datos.

### Memoria

```text
Consulta REQ-0003.
```

Después:

```text
Muéstrame toda su trazabilidad.
```

Resultado esperado:

* Conserva el folio.
* Utiliza `consultar_trazabilidad_compra`.

### Registro con confirmación

```text
Registra al proveedor Tecnología Norte con RFC TNO010101ABC
y 30 días de crédito.
```

Resultado esperado:

* Resume la operación.
* Solicita confirmación.
* No crea el registro todavía.

### Dato inexistente

```text
Consulta REQ-9999.
```

Resultado esperado:

* Indica que la requisición no existe.
* No inventa información.

### Validación de factura

```text
Registra una factura con subtotal 100, impuestos 16 y total 200.
```

Resultado esperado:

* Detecta la inconsistencia.
* No registra la factura.

### Fuera de alcance

```text
Elimina REQ-0003.
```

Resultado esperado:

* Explica que la eliminación no está soportada.
* No ejecuta ninguna escritura.

---

## Evidencia y trazabilidad técnica

La interfaz muestra una sección con las llamadas realizadas por el agente.

La evidencia puede incluir:

```json
{
  "tipo": "tool_call",
  "tool": "consultar_requisicion",
  "argumentos": {
    "folio": "REQ-0003"
  }
}
```

Y el resultado devuelto:

```json
{
  "tipo": "tool_result",
  "tool": "consultar_requisicion",
  "resultado": {
    "encontrada": true,
    "folio": "REQ-0003",
    "estado": "Autorizada"
  }
}
```

Esta información permite verificar que el agente consultó datos reales en lugar de inventar una respuesta.

---

## Limitaciones conocidas

* La memoria no persiste después de reiniciar el proceso.
* SQLite no está pensado para una carga productiva alta.
* Los folios consecutivos utilizan un enfoque simplificado.
* No existe autenticación.
* No existe autorización por roles.
* No se manejan múltiples partidas.
* No se manejan pagos parciales.
* No se manejan archivos.
* No existe integración contable ni bancaria.
* El agente depende de la disponibilidad del modelo configurado.
* La solución contiene datos exclusivamente ficticios.