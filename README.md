# Asistente de Seguimiento de Compras y Pagos

Prueba de concepto de un agente conversacional para registrar, consultar y dar seguimiento a un flujo simplificado de compras y pagos.

La aplicación está dirigida principalmente a personal de **gerencia administrativa y operaciones de compras** que necesita consultar la relación entre proveedores, requisiciones, órdenes de compra, facturas y pagos sin navegar manualmente entre distintos documentos.

> Este proyecto es una prueba de concepto académica. No es un ERP, un sistema contable ni una plataforma productiva de cuentas por pagar.

---

## Problema

En un proceso de compras, la información suele estar distribuida entre varios documentos:

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

Esto dificulta responder rápidamente preguntas como:

* ¿Cuál es el estado de una requisición?
* ¿Qué proveedor fue utilizado?
* ¿Existe una orden de compra?
* ¿La orden ya tiene factura?
* ¿Cuándo vence la factura?
* ¿La factura ya fue pagada?
* ¿Qué pagos vencen próximamente?

El agente permite consultar y registrar esta información mediante lenguaje natural, utilizando exclusivamente tools expuestas por un servidor MCP.

### Usuario principal

El usuario principal es:

* Gerencia administrativa.
* Personal operativo de compras.
* Usuario evaluador de la prueba de concepto.

### Necesidad que aborda

La aplicación busca demostrar que un agente de IA puede:

1. Interpretar solicitudes en lenguaje natural.
2. Seleccionar una tool MCP.
3. Consultar información persistida.
4. Ejecutar operaciones controladas.
5. Mantener referencias dentro de una conversación.
6. Pedir confirmación antes de modificar información.
7. Mostrar evidencia de las tools utilizadas.

### Fuente de datos

La fuente de datos es una base local **SQLite** con información ficticia.

La base contiene:

* Proveedores.
* Requisiciones.
* Órdenes de compra.
* Facturas.
* Pagos.

No se utilizan datos reales ni información confidencial.

### Límites

La prueba de concepto no incluye:

* Actualización de registros.
* Eliminación de registros.
* Cancelaciones.
* Autorizaciones multinivel.
* Inicio de sesión.
* Roles y permisos reales.
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

Las requisiciones se crean directamente en estado `Autorizada`.

Cada requisición puede tener:

* Una sola descripción o partida.
* Una sola orden de compra.

Cada orden puede tener:

* Una sola factura.

Cada factura puede tener:

* Un solo pago completo.

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

Versión resumida:

```text
Streamlit
→ Agente LangChain + OpenAI
→ MCP
→ SQLite
```

### Componentes

#### Streamlit

Responsable de:

* Mostrar el chat.
* Mantener el identificador de sesión.
* Mostrar el historial.
* Presentar la respuesta del agente.
* Mostrar evidencia y tool calls.
* Reiniciar la conversación.
* Mostrar errores de forma comprensible.

#### Agente LangChain

Responsable de:

* Interpretar la solicitud del usuario.
* Seleccionar las tools MCP.
* Solicitar datos faltantes.
* Mantener referencias conversacionales.
* Pedir confirmación antes de escrituras.
* Resumir los resultados.
* Evitar inventar información.

#### OpenAI

Se utiliza como proveedor de inferencia para el modelo de lenguaje que ejecuta el razonamiento del agente y decide qué tools utilizar.

El modelo se configura mediante la variable:

```env
OPENAI_MODEL=
```

#### Servidor MCP

El servidor MCP está construido con FastMCP.

Es responsable de:

* Exponer las operaciones del dominio.
* Definir parámetros tipados.
* Validar entradas.
* Ejecutar reglas de negocio.
* Controlar operaciones de escritura.
* Devolver resultados estructurados.

#### SQLite

SQLite se utiliza para persistir los datos ficticios de la prueba de concepto.

---

## Flujo funcional

```text
Registrar proveedor
        ↓
Crear requisición
        ↓
Crear orden de compra
        ↓
Registrar factura
        ↓
Calcular vencimiento
        ↓
Registrar pago
        ↓
Consultar trazabilidad
```

---

## Tools MCP

### Tools de escritura

Todas las tools de escritura requieren una confirmación explícita del usuario antes de ejecutarse.

| Tool                  | Propósito                                        | Entrada principal                                                      | Salida principal                    | Riesgo                                                                                  |
| --------------------- | ------------------------------------------------ | ---------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------- |
| `registrar_proveedor` | Registrar un proveedor y su condición de pago    | Nombre, RFC, condición, días de crédito y confirmación                 | ID del proveedor creado             | Medio: crea información persistente y puede duplicar proveedores si no se valida el RFC |
| `crear_requisicion`   | Crear una requisición simplificada               | Solicitante, área, tipo, descripción, importe, proyecto y confirmación | Folio y estado de la requisición    | Medio: crea un documento de compra                                                      |
| `crear_orden_compra`  | Crear una orden desde una requisición autorizada | Folio de requisición, proveedor, importe y confirmación                | Folio de orden de compra            | Alto: vincula proveedor y requisición y cambia el estado del flujo                      |
| `registrar_factura`   | Registrar una factura y calcular su vencimiento  | Orden, número, fecha, subtotal, impuestos, total y confirmación        | ID de factura, vencimiento y estado | Alto: crea una cuenta por pagar y actualiza estados                                     |
| `registrar_pago`      | Registrar el pago completo de una factura        | Factura, fecha, importe, medio, referencia y confirmación              | ID del pago y estado final          | Alto: marca documentos como pagados                                                     |

### Tools de lectura

| Tool                            | Propósito                                       | Entrada principal    | Salida principal                              | Riesgo                                                       |
| ------------------------------- | ----------------------------------------------- | -------------------- | --------------------------------------------- | ------------------------------------------------------------ |
| `consultar_proveedor`           | Buscar un proveedor                             | ID, RFC o nombre     | Datos del proveedor                           | Bajo: operación de solo lectura                              |
| `consultar_requisicion`         | Consultar una requisición                       | Folio                | Datos y estado de la requisición              | Bajo: operación de solo lectura                              |
| `consultar_trazabilidad_compra` | Recuperar la cadena completa de documentos      | Folio de requisición | Requisición, orden, proveedor, factura y pago | Bajo: expone información relacionada, pero no modifica datos |
| `listar_pagos_por_vencer`       | Consultar facturas pendientes próximas a vencer | Número de días       | Lista de facturas y fechas de vencimiento     | Bajo: operación de solo lectura                              |

---

## Confirmación de escrituras

El agente no debe ejecutar inmediatamente una operación que modifique la base de datos.

El proceso obligatorio es:

```text
Solicitud del usuario
        ↓
Validación de datos
        ↓
Resumen de la operación
        ↓
Solicitud de confirmación
        ↓
Confirmación explícita
        ↓
Ejecución de la tool MCP
```

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

Solo después de esa confirmación se llama la tool con:

```python
confirmar=True
```

La confirmación:

* Solo aplica a la acción pendiente.
* Solo es válida dentro de la misma sesión.
* No debe reutilizarse para otra operación.
* No debe provocar una escritura duplicada.

---

## Reglas de negocio

### Proveedores

* El nombre es obligatorio.
* El RFC es obligatorio.
* El RFC no puede estar duplicado.
* La condición debe ser `contado` o `credito`.
* Un proveedor de contado debe tener cero días de crédito.
* Un proveedor a crédito debe tener más de cero días de crédito.

### Requisiciones

* Se crean directamente en estado `Autorizada`.
* El importe debe ser mayor que cero.
* Cada requisición puede generar una sola orden de compra.

### Órdenes de compra

* La requisición debe existir.
* La requisición debe estar autorizada.
* El proveedor debe existir.
* El importe debe ser mayor que cero.
* No se puede crear una segunda orden para la misma requisición.

### Facturas

* La orden debe existir.
* Cada orden puede tener una sola factura.
* La fecha debe utilizar el formato `AAAA-MM-DD`.
* El subtotal y los impuestos no pueden ser negativos.
* El total debe ser mayor que cero.
* Debe cumplirse:

```text
subtotal + impuestos = total
```

Se permite una tolerancia mínima por redondeo.

### Vencimiento

Para un proveedor de contado:

```text
fecha_vencimiento = fecha_factura
```

Para un proveedor a crédito:

```text
fecha_vencimiento = fecha_factura + dias_credito
```

### Pagos

* La factura debe existir.
* La factura no debe estar pagada.
* El importe debe coincidir con el total de la factura.
* No se permiten pagos parciales.
* La referencia es obligatoria.
* Los medios permitidos son:

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

### Actualización interna de estados

Aunque no existen tools públicas para actualizar registros, las operaciones del flujo actualizan estados internamente.

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

## Memoria

La aplicación mantiene memoria de corto plazo por conversación.

### Identificador de sesión

Streamlit genera un `session_id` único para cada sesión.

Este valor se utiliza como `thread_id` en la configuración del agente:

```python
config = {
    "configurable": {
        "thread_id": session_id
    }
}
```

Esto permite que el agente mantenga referencias como:

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

El agente debe recordar que la segunda solicitud hace referencia a `REQ-0003`.

### Implementación

La memoria se implementa con:

```python
from langgraph.checkpoint.memory import InMemorySaver
```

```python
memory = InMemorySaver()
```

### Ventana de mensajes

La implementación actual conserva el historial asociado al `session_id` durante la vida del proceso.

Actualmente no se aplica una ventana fija de `N` mensajes en esta PoC.

Si se configura una ventana, debe documentarse aquí el valor utilizado:

```text
Ventana configurada: N mensajes
```

Por ejemplo:

```text
Ventana configurada: 20 mensajes
```

No debe declararse un valor fijo en este README si el código todavía no implementa el recorte del historial.

### Limitaciones de memoria

* La memoria es temporal.
* Se reinicia cuando el proceso se detiene.
* No se comparte entre diferentes `session_id`.
* No es memoria de largo plazo.
* No reemplaza la persistencia de SQLite.
* Reiniciar la conversación desde Streamlit genera un nuevo `session_id`.
* Si se despliega en varias instancias, cada instancia puede tener memoria independiente.

---

## Estructura del repositorio

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

| Archivo            | Responsabilidad                                       |
| ------------------ | ----------------------------------------------------- |
| `app_streamlit.py` | Interfaz web y estado de la sesión                    |
| `agent_core.py`    | Modelo, prompt, memoria, tools y ejecución del agente |
| `mcp_server.py`    | Servidor FastMCP y exposición de tools                |
| `services.py`      | Validaciones y reglas de negocio                      |
| `database.py`      | Conexión, tablas y transacciones SQLite               |
| `seed_data.py`     | Inicialización de datos ficticios                     |
| `tests/`           | Pruebas automatizadas                                 |

---

## Requisitos

* Python 3.11 o superior.
* Clave de API de OpenAI.
* Acceso a los puertos del servidor MCP y Streamlit.
* Git, en caso de clonar el repositorio.

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd asistente_compras_poc
```

### 2. Crear un entorno virtual

macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

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

En Windows:

```powershell
Copy-Item .env.example .env
```

Configura las siguientes variables:

```env
OPENAI_API_KEY=tu_clave_de_openai
OPENAI_MODEL=nombre_del_modelo
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
DATABASE_PATH=data/compras.db
```

### Variables

| Variable         | Propósito                                        |
| ---------------- | ------------------------------------------------ |
| `OPENAI_API_KEY` | Clave utilizada para invocar el modelo de OpenAI |
| `OPENAI_MODEL`   | Modelo utilizado por el agente                   |
| `MCP_SERVER_URL` | Dirección del servidor MCP                       |
| `DATABASE_PATH`  | Ruta del archivo SQLite                          |

No publiques el archivo `.env`.

### 5. Inicializar la base de datos

```bash
python database.py
```

### 6. Cargar datos ficticios

```bash
python seed_data.py
```

Este paso puede omitirse si se desea iniciar con una base vacía.

### 7. Ejecutar el servidor MCP

En una terminal:

```bash
source .venv/bin/activate
python mcp_server.py
```

En Windows:

```powershell
.venv\Scripts\Activate.ps1
python mcp_server.py
```

El endpoint local predeterminado es:

```text
http://127.0.0.1:8000/mcp
```

### 8. Ejecutar Streamlit

En una segunda terminal:

```bash
source .venv/bin/activate
streamlit run app_streamlit.py
```

En Windows:

```powershell
.venv\Scripts\Activate.ps1
streamlit run app_streamlit.py
```

La interfaz estará disponible normalmente en:

```text
http://localhost:8501
```

---

## Despliegue

La aplicación puede publicarse utilizando un servicio que permita ejecutar procesos Python persistentes.

La arquitectura de despliegue puede utilizar dos servicios:

```text
Servicio de Streamlit
        ↓
MCP_SERVER_URL
        ↓
Servicio FastMCP
        ↓
Base de datos
```

También es posible ejecutar Streamlit y FastMCP dentro del mismo servicio:

```text
Contenedor o Web Service
├── Streamlit
├── FastMCP
└── SQLite
```

### Configuración de `MCP_SERVER_URL`

En local:

```env
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
```

Si MCP está publicado como servicio independiente:

```env
MCP_SERVER_URL=https://<URL_DEL_SERVIDOR_MCP>/mcp
```

Esta variable debe configurarse en el panel de variables de entorno del hosting donde se publique Streamlit.

### Ejemplo de publicación en Render

Configuración sugerida:

```text
Build command:
pip install -r requirements.txt

Start command:
bash start.sh
```

Variables de entorno:

```env
OPENAI_API_KEY=<SECRETO>
OPENAI_MODEL=<MODELO>
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
DATABASE_PATH=data/compras.db
```

Ejemplo de `start.sh`:

```bash
#!/usr/bin/env bash

set -e

python database.py
python seed_data.py

python mcp_server.py &

sleep 3

exec streamlit run app_streamlit.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-8501}" \
  --server.headless true
```

### Persistencia

Si el hosting no conserva archivos entre reinicios, la base SQLite puede perder sus cambios.

En ese escenario:

* La base debe regenerarse con `seed_data.py`.
* Los datos deben considerarse temporales.
* La aplicación debe utilizarse únicamente como demostración.

Para conservar información permanentemente sería necesario migrar la persistencia a una base administrada, por ejemplo PostgreSQL.

### Despliegue actual

Completar con los datos reales:

```text
Hosting de Streamlit: <RENDER / STREAMLIT CLOUD / OTRO>
Hosting de MCP: <MISMO SERVICIO / SERVICIO INDEPENDIENTE>
Base de datos: SQLite
```

---

## Pruebas

Ejecuta todas las pruebas:

```bash
pytest -q
```

Ejecuta solamente las pruebas de servicios:

```bash
pytest tests/test_services.py -q
```

Ejecuta las pruebas MCP:

```bash
pytest tests/test_mcp.py -q
```

Ejecuta las pruebas del agente:

```bash
pytest tests/test_agent.py -q
```

---

## Casos de prueba

### 1. Consulta directa

Entrada:

```text
¿Cuál es el estado de REQ-0003?
```

Resultado esperado:

* Utiliza `consultar_requisicion`.
* Devuelve información almacenada.
* No inventa datos.

### 2. Consulta compuesta

Entrada:

```text
Consulta REQ-0003 y dime si su pago está vencido.
```

Resultado esperado:

* Utiliza `consultar_trazabilidad_compra`.
* Recupera la factura.
* Evalúa su fecha de vencimiento y estado.

### 3. Memoria conversacional

Primer turno:

```text
Consulta REQ-0003.
```

Segundo turno:

```text
Ahora muéstrame toda su trazabilidad.
```

Resultado esperado:

* Conserva el folio de la requisición.
* No vuelve a pedirlo.
* Utiliza `consultar_trazabilidad_compra`.

### 4. Registro con confirmación

Entrada:

```text
Registra al proveedor Mobiliario Central con RFC MCE010101ABC
y 30 días de crédito.
```

Resultado esperado:

* Resume la operación.
* Solicita confirmación.
* No ejecuta la escritura todavía.

Segundo turno:

```text
Sí, confirma.
```

Resultado esperado:

* Utiliza `registrar_proveedor`.
* Envía `confirmar=true`.
* Devuelve el ID generado.

### 5. Registro inexistente

Entrada:

```text
Consulta REQ-9999.
```

Resultado esperado:

* Indica que no existe.
* No inventa resultados.

### 6. Validación de factura

Entrada:

```text
Registra una factura con subtotal 100, impuestos 16 y total 200.
```

Resultado esperado:

* Detecta que los importes son inconsistentes.
* No registra la factura.

### 7. Operación fuera de alcance

Entrada:

```text
Elimina REQ-0003.
```

Resultado esperado:

* Indica que la eliminación no está soportada.
* No intenta llamar una tool de escritura.

### 8. Consulta de vencimientos

Entrada:

```text
¿Qué pagos vencen en los próximos siete días?
```

Resultado esperado:

* Utiliza `listar_pagos_por_vencer`.
* Devuelve facturas pendientes dentro del rango.

---

## Happy path

Ejecutar los siguientes mensajes dentro de la misma conversación.

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

### 3. Crear orden

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

Resultado esperado:

```text
Proveedor
→ Requisición Pagada
→ Orden Pagada
→ Factura Pagada
→ Pago registrado
```

---

## Evidencia de tools

Streamlit muestra las llamadas realizadas por el agente.

Ejemplo de tool call:

```json
{
  "tipo": "tool_call",
  "tool": "consultar_requisicion",
  "argumentos": {
    "folio": "REQ-0003"
  }
}
```

Ejemplo de resultado:

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

Esta evidencia permite comprobar que el agente utilizó una fuente real y no generó la respuesta únicamente con el modelo de lenguaje.

---

## Seguridad

* No publicar `.env`.
* No publicar claves de OpenAI.
* No subir `.streamlit/secrets.toml`.
* Utilizar únicamente datos ficticios.
* Utilizar consultas SQL parametrizadas.
* No exponer una tool genérica para ejecutar SQL.
* Validar las entradas dentro de los servicios.
* Solicitar confirmación para toda escritura.
* No almacenar información sensible en SQLite.
* No mostrar secretos en capturas de pantalla.

---

## Limitaciones conocidas

* La memoria se pierde al reiniciar el proceso.
* No existe un límite explícito de mensajes mientras no se implemente una ventana.
* SQLite puede perder información en hostings con almacenamiento efímero.
* No existe autenticación.
* No existen roles ni permisos.
* No se manejan múltiples partidas.
* No se permiten pagos parciales.
* No se manejan archivos adjuntos.
* No existe integración contable o bancaria.
* Los folios utilizan un esquema consecutivo simplificado.
* El comportamiento del agente depende del modelo configurado.
* La aplicación contiene únicamente datos ficticios.

---

## Enlaces

* Aplicación pública: https://proyecto-final-integraciones.onrender.com/
* Repositorio: https://github.com/ben-blb/proyecto_final_integraciones

---

## Autor

* Nombre: `Benjamin Lopez Briones`
* Materia: Estrategias de Integración
* Proyecto: Sistema de Agentes MCP