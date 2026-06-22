# Panel Físico de Estado del Agente (Arduino + Cursor Hooks)

> Original design document (Spanish). Phase 1 (Python hooks) is implemented in this repository.
>
> **Alcance actual:** solo display del estado del agente (Cursor → hardware). El botón físico y el path MCP (`get_pending_events`) fueron removidos del roadmap; ver [`roadmap.md`](roadmap.md).

## 1. Objetivo del proyecto

Construir un panel físico conectado a un Arduino que:

1. **Muestra el estado del agente de IA (Cursor) en tiempo real** en una pantalla OLED — ej. "Pensando...", "Ejecutando: npm test", "Error", "Listo". Esto se logra de forma **determinística**, sin depender de que el modelo "decida" reportar su estado.
2. **Tiene un botón físico** que el usuario puede presionar para enviar una señal/evento que el agente puede consultar (ej. "pausar", "resumen del día", "confirmar acción").

---

## 2. Decisión de arquitectura (actualizada)

### Hallazgo clave: Cursor Hooks

Cursor tiene una feature nativa llamada **Hooks**: 12 eventos del ciclo de vida del agente que, al dispararse, ejecutan automáticamente un comando externo (definido en `.cursor/hooks.json`), pasándole el contexto del evento como JSON por **stdin**. Esto es nativo, documentado y determinístico — **no depende de que el LLM decida llamar una tool**, Cursor lo dispara siempre.

Hooks relevantes para este proyecto:

| Hook | Cuándo dispara | Uso para el panel |
|---|---|---|
| `beforeSubmitPrompt` | El usuario envía un prompt | Display → "Procesando prompt..." |
| `afterAgentThought` | El agente está razonando | Display → "Pensando..." |
| `beforeShellExecution` | Antes de correr un comando de shell | Display → "Ejecutando: `<comando>`" |
| `afterShellExecution` | Después de correr un comando | Display → resultado (éxito/error) |
| `beforeMCPExecution` / `afterMCPExecution` | Antes/después de invocar una tool MCP | Display → "Usando tool: `<nombre>`" |
| `afterAgentResponse` | El agente terminó de responder | Display → "Listo" |
| `stop` | Fin de sesión, con score de completitud | Display → resumen final |

Referencia de implementación de terceros (solo como inspiración del patrón, **no se usa como dependencia** — ver sección 8): [`naoufalelh/cursor-langfuse`](https://github.com/naoufalelh/cursor-langfuse), que registra un único `hook-handler.js` para los 12 hooks y enruta cada evento a Langfuse. Nuestro handler hace lo mismo pero enruta al Arduino por serial en lugar de a Langfuse.

### Por qué este cambio es mejor que la versión anterior

La primera versión de este proyecto planteaba que el **agente llamara una tool MCP propia** (`set_agent_status`) para reportar su estado, instruido por una regla de proyecto. Eso funciona, pero depende de que el modelo "se acuerde" de llamarla en cada paso — es indirecto y no 100% confiable.

Con hooks nativos, **Cursor mismo dispara el evento siempre**, sin intervención del modelo. Es más simple y más confiable para todo lo que es *reportar* estado.

### Dónde sigue siendo necesario el MCP

El **botón físico → agente** sigue funcionando vía MCP, porque ahí sí necesitamos que el *agente* consulte algo activamente (no hay un hook de "el usuario presionó un botón externo"; los hooks de Cursor solo cubren eventos *del propio Cursor*, no de hardware externo). Entonces:

- **Cursor → Arduino (estado)**: vía **Hooks** (determinístico, automático).
- **Arduino → Cursor (botón)**: vía **MCP tool** (`get_pending_events`), que el agente consulta cuando se le indique en las Rules del proyecto.

---

## 3. Arquitectura

```
┌──────────────────────────────────────────────┐
│                   Cursor                      │
│                                                │
│  dispara hooks automáticamente:               │
│  beforeShellExecution, afterAgentThought, etc │
└───────────────────┬────────────────────────────┘
                     │  JSON por stdin (hook nativo)
                     ▼
        ┌─────────────────────────┐
        │   hook-handler (Python   │
        │   o Node), registrado   │
        │   en .cursor/hooks.json │
        └────────────┬─────────────┘
                     │  escribe por serial: STATUS|estado|mensaje
                     ▼
              ┌─────────────┐
              │   Arduino    │
              │  Uno / Nano  │
              └──────┬──────┘
                     │ I2C              │ pin digital
              ┌──────┴──────┐    ┌──────┴──────┐
              │ OLED SSD1306 │    │   Botón      │
              │  128x64      │    │ (pull-up)    │
              └─────────────┘    └──────┬──────┘
                                         │ al presionar:
                                         │ EVENT|button_pressed (por serial)
                                         ▼
                          ┌──────────────────────────┐
                          │  Servidor MCP (Python,    │
                          │  FastMCP) — lee serial en │
                          │  background, expone tool  │
                          │  get_pending_events()     │
                          └──────────────┬─────────────┘
                                         │  el agente la llama cuando
                                         │  se le indica en las Rules
                                         ▼
                                  Cursor (agente)
```

**Nota de implementación importante:** tanto el hook-handler como el servidor MCP necesitan hablar con el Arduino por el mismo puerto serial. Un puerto serial solo lo puede tener abierto un proceso a la vez de forma fiable. Dos opciones:

- **Opción simple (recomendada para empezar):** un único proceso long-running (el servidor MCP) es el único que abre el puerto serial. El hook-handler, en lugar de escribir directo al serial, le manda el comando a ese proceso por una vía simple (ej. HTTP local en `localhost:PUERTO`, o un archivo/pipe que el servidor MCP esté vigilando). Así no hay contención del puerto.
- **Opción alterna:** el hook-handler escribe directo al serial y se cierra inmediatamente (los hooks son procesos de vida corta), y el servidor MCP abre el puerto solo cuando necesita leer eventos del botón, cerrándolo después. Más simple de razonar pero más frágil (riesgo de colisión si ambos intentan abrir el puerto en el mismo instante).

Se sugiere la **opción simple**: el servidor MCP expone también un mini endpoint HTTP local (ej. `http://127.0.0.1:8765/status`) que el hook-handler llama con un POST conteniendo el estado. Todo el tráfico al Arduino pasa por un solo proceso.

---

## 4. Lista de materiales

| Componente | Cantidad | Notas |
|---|---|---|
| Arduino Uno o Nano | 1 | Ya lo tienes |
| Protoboard | 1 | Ya la tienes |
| Pantalla OLED I2C SSD1306 (128x64, 0.96") | 1 | ~3-5 USD. Verificar si es de 3.3V o 5V (la mayoría aceptan ambos, revisar etiqueta del módulo) |
| Pulsador (push button / tactile switch 4 patas) | 1 | Común en kits de protoboard |
| Cables jumper macho-macho | ~6-8 | Para OLED (4) y botón (2) |
| Resistencia 10kΩ | 0 o 1 | Opcional: usamos `INPUT_PULLUP` interno del Arduino, así que NO es necesaria salvo que se prefiera pull-down externo |
| Cable USB | 1 | El que ya usas para programar el Arduino (alimentación + datos) |

### Conexiones

**OLED SSD1306 (I2C):**
| Pin OLED | Pin Arduino Uno/Nano |
|---|---|
| VCC | 5V |
| GND | GND |
| SDA | A4 |
| SCL | A5 |

**Botón:**
| Pata botón | Conexión |
|---|---|
| Pata 1 | Pin digital D2 (soporta interrupciones por hardware en Uno) |
| Pata 2 | GND |

Configurar el pin D2 como `INPUT_PULLUP` en el firmware — el pin lee HIGH en reposo y LOW al presionar, sin necesitar resistencia externa.

---

## 5. Protocolo de comunicación serial (Arduino ↔ proceso Python)

USB serial, **9600 baudios**. Texto plano, líneas terminadas en `\n`, campos separados por `|` (fácil de depurar a ojo con el Monitor Serial).

### PC → Arduino (comandos de estado)
```
STATUS|<estado>|<mensaje>
```
- `<estado>`: palabra corta, ej. `idle`, `thinking`, `running_shell`, `running_mcp`, `success`, `error`, `waiting`.
- `<mensaje>`: texto libre corto (máx ~20 caracteres para que entre bien en el OLED), sin el carácter `|`.

Ejemplos:
```
STATUS|thinking|Pensando...
STATUS|running_shell|npm test
STATUS|running_mcp|Tool: web_search
STATUS|success|Listo
STATUS|error|Build fallo
```

### Arduino → PC (eventos de hardware)
```
EVENT|<tipo_evento>
```
Ejemplo:
```
EVENT|button_pressed
```

El firmware debe:
- Leer continuamente el puerto serial; al recibir una línea `STATUS|...`, parsearla y redibujar el OLED.
- Detectar flancos de bajada en el botón con debounce (~200-300ms) y emitir `EVENT|button_pressed` exactamente una vez por presión.

---

## 6. Componentes de software a construir

### 6.1 Firmware Arduino (`.ino`)
- Librerías: `Wire.h` (I2C), `Adafruit_GFX.h`, `Adafruit_SSD1306.h`.
- `setup()`: serial a 9600, inicializar OLED, pin de botón como `INPUT_PULLUP`, pantalla inicial ("Esperando...").
- `loop()`: leer línea serial si disponible → parsear `STATUS|...` → redibujar OLED. Revisar botón con debounce → en flanco de presión → enviar `EVENT|button_pressed`.

### 6.2 Proceso Python único (recomendado: un solo servicio long-running con dos responsabilidades)

**A. Servidor MCP** (usando `fastmcp` o el SDK `mcp` oficial):
| Tool | Parámetros | Qué hace |
|---|---|---|
| `get_pending_events` | (ninguno) | Devuelve y limpia la lista de eventos recibidos del Arduino desde la última llamada |

**B. Mini servidor HTTP local** (puede ser el mismo proceso, usando algo ligero como `Flask` o incluso `http.server` con un handler simple):
- Endpoint `POST /status` que recibe `{"estado": "...", "mensaje": "..."}` y lo traduce al comando serial `STATUS|estado|mensaje`.
- Este es el endpoint al que apunta el hook-handler de Cursor.

**C. Hilo de lectura serial en background:**
- Mantiene la conexión serial abierta (`pyserial`), lee continuamente, y cuando detecta `EVENT|...`, lo agrega a una cola/lista en memoria para que `get_pending_events` la consuma.

### 6.3 Hook handler de Cursor (`.cursor/hooks/hook-handler.py` o `.js`)
- Se registra en `.cursor/hooks.json` para los hooks listados en la sección 2.
- Recibe el JSON del evento por stdin.
- Mapea el tipo de hook + datos del evento a un `estado` y `mensaje` cortos (ej. `beforeShellExecution` con comando `npm test` → `estado=running_shell`, `mensaje=npm test`).
- Hace un `POST` a `http://127.0.0.1:<puerto>/status` con ese payload.
- Debe ser **no bloqueante y tolerante a fallos**: si el POST falla (ej. el servidor Python no está corriendo), debe loguear el error a stderr y devolver `{"continue": true, "permission": "allow"}` para no interrumpir a Cursor nunca.

---

## 7. Integración con Cursor

1. **Hooks** — crear `.cursor/hooks.json` en la raíz del proyecto, registrando el handler para cada hook de interés.
2. **MCP** — agregar el servidor MCP en `~/.cursor/mcp.json`.
3. **Rules de proyecto** — una regla simple indicando que el agente consulte `get_pending_events` al iniciar conversaciones.

---

## 8. Sobre el repo de referencia (`naoufalelh/cursor-langfuse`)

- Es un proyecto personal/ejemplo. **No se usa como dependencia** de este proyecto, solo como referencia del patrón de `hooks.json` + handler único.

---

## 9. Plan de implementación sugerido

1. **Firmware Arduino**
2. **Proceso Python único** (MCP + HTTP + serial)
3. **Hook handler** ✅ implemented in this repo (Phase 1)
4. **Registrar hooks y MCP en Cursor**
5. **Pruebas end-to-end**

---

## 10. Notas / decisiones ya tomadas (no las cambies sin razón)

- Microcontrolador: **Arduino Uno/Nano**, comunicación por **serial USB** (no WiFi, no Bluetooth).
- Display: **OLED I2C SSD1306 128x64**, mostrando **texto**, no gráficos complejos.
- Botón conectado a **D2** con **INPUT_PULLUP** (sin resistencia externa).
- Protocolo serial: **texto plano** con formato `TIPO|campo1|campo2`, 9600 baudios.
- **Reporte de estado (Cursor → Arduino): vía Cursor Hooks nativos**, no vía tool MCP llamada a discreción del modelo. Esto es determinístico.
- **Botón (Arduino → Cursor): vía MCP tool** `get_pending_events`, consultada según regla de proyecto.
- Solo **un proceso** (el servidor Python) abre el puerto serial; el hook-handler le habla por HTTP local, no directo al puerto, para evitar contención.
- No se usa el repo `naoufalelh/cursor-langfuse` como dependencia — solo como referencia de patrón.
