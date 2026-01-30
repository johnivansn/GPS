# Protocolo GPS - Práctica 3
## Redes de Computadoras

---

## Descripción del Proyecto

Sistema de mensajería para dispositivos GPS que permite enviar coordenadas y datos de estado en tiempo real a un servidor central. Diseñado para dispositivos con restricciones de batería y ancho de banda limitado, funcionando sobre redes celulares 2G/3G/4G.

---

## Características del Protocolo

### 1. **Formato del Mensaje** (28 bytes total)

```
CABECERA (8 bytes):
- VER (1 byte):      Versión del protocolo
- TIPO (1 byte):     Tipo de mensaje (DATOS_GPS, ACK, HEARTBEAT)
- ID_DISP (2 bytes): ID único del dispositivo
- SECUENCIA (2 bytes): Número de secuencia
- FLAGS (1 byte):    Flags de estado
- CHECKSUM (2 bytes): CRC-16 para detección de errores

PAYLOAD (20 bytes):
- LATITUD (4 bytes):   Grados × 10^7
- LONGITUD (4 bytes):  Grados × 10^7
- ALTITUD (2 bytes):   Metros
- TIMESTAMP (4 bytes): Unix timestamp
- VELOCIDAD (2 bytes): km/h × 10
- RUMBO (2 bytes):     Grados × 10
- BATERÍA (1 byte):    Porcentaje (0-100)
- ESTADO (1 byte):     Byte de estado
```

### 2. **Método de Transmisión**

- **Protocolo**: UDP (User Datagram Protocol)
- **Puerto por defecto**: 9999
- **Ventajas**:
  - Menor overhead (8 bytes vs 20+ de TCP)
  - No requiere handshake (ahorro de batería)
  - Ideal para datos en tiempo real
  - Tolerante a pérdidas ocasionales

### 3. **Manejo de Errores**

- **CRC-16**: Checksum para detección de errores
- **ACK opcional**: Confirmación de recepción
- **Numeración de secuencia**: Detecta duplicados y pérdidas
- **Timeout y reintentos**: Máximo 3 intentos con timeout de 3s

### 4. **Seguridad Básica**

- Autenticación por ID de dispositivo
- Validación de timestamp (±5 minutos de tolerancia)
- Verificación de checksum en cada mensaje
- Registro de dispositivos conocidos

---

## Estructura del Proyecto

```
proyecto-gps/
├── gps_protocolo.py    # Librería compartida del protocolo
├── gps_cliente.py      # Simulador de dispositivo GPS
├── gps_servidor.py     # Servidor central receptor
├── README.md           # Este archivo
└── gps_log.txt         # Log de mensajes (generado automáticamente)
```

---

## Instalación y Requisitos

### Requisitos
- Python 3.6 o superior
- No requiere librerías externas (usa solo módulos estándar)
- Sistema operativo: Windows, Linux o macOS

### Instalación
```bash
# Clonar o descargar los archivos
# No requiere instalación adicional
```

---

## Uso del Sistema

### 1. Probar la Librería del Protocolo

```bash
python gps_protocolo.py
```

Esto ejecuta pruebas automáticas que verifican:
- ✓ Empaquetado de mensajes
- ✓ Desempaquetado de mensajes
- ✓ Detección de corrupción (checksum)
- ✓ Creación de ACKs

### 2. Iniciar el Servidor

**Opción básica:**
```bash
python gps_servidor.py
```

**Con parámetros personalizados:**
```bash
python gps_servidor.py [puerto] [enviar_ack]

# Ejemplos:
python gps_servidor.py 8888 true     # Puerto 8888, con ACK
python gps_servidor.py 9999 false    # Puerto 9999, sin ACK
```

El servidor mostrará:
```
============================================================
  SERVIDOR GPS CENTRAL
============================================================
  Puerto: 9999
  ACK automático: Sí
============================================================

[✓] Servidor escuchando en puerto 9999
[✓] Esperando dispositivos GPS...
```

### 3. Ejecutar el Cliente (Dispositivo GPS)

**Modo interactivo:**
```bash
python gps_cliente.py
```

El menú te permite elegir:
1. Vehículo estacionado (sin movimiento)
2. Vehículo en movimiento urbano (30 km/h)
3. Vehículo en carretera (80 km/h)
4. Modo personalizado
5. Salir

**Modo directo con parámetros:**
```bash
python gps_cliente.py [servidor_ip] [puerto] [id_dispositivo]

# Ejemplos:
python gps_cliente.py 127.0.0.1 9999 1234
python gps_cliente.py 192.168.1.100 8888 5678
```

---

## Pruebas con Wireshark

### Capturar Tráfico UDP

1. **Abrir Wireshark**
2. **Seleccionar interfaz**: Loopback (lo0 o lo) para pruebas locales
3. **Aplicar filtro**:
   ```
   udp.port == 9999
   ```
4. **Iniciar captura**
5. **Ejecutar servidor y cliente**
6. **Analizar paquetes capturados**

### Verificar el Protocolo

En Wireshark podrás ver:
- Tamaño de paquetes: 28 bytes (datos GPS) u 8 bytes (ACK)
- Dirección origen y destino
- Puerto UDP: 9999
- Contenido hexadecimal del mensaje

**Ejemplo de análisis:**
```
Frame: 28 bytes
Ethernet II
Internet Protocol Version 4
User Datagram Protocol
Data (28 bytes):
  01 01 04 d2 00 01 0c 3f f5 15 7e 50 fc 0e 74 7a
  00 00 09 fe 67 fd b3 08 01 c2 05 46 55 00
```

Desglose:
- `01`: VERSION = 0x01
- `01`: TIPO = DATOS_GPS
- `04 d2`: ID_DISPOSITIVO = 1234
- `00 01`: SECUENCIA = 1
- `0c`: FLAGS = 0x0C (movimiento + ignición)
- `3f f5`: CHECKSUM
- Resto: Payload con coordenadas, velocidad, etc.

---

## Ejemplos de Salida

### Servidor recibiendo datos:

```
────────────────────────────────────────────────────────────
[←] DATOS GPS RECIBIDOS
────────────────────────────────────────────────────────────
  Origen:       127.0.0.1:54321
  Dispositivo:  GPS #1234
  Secuencia:    #5
  Coordenadas:  -17.3935000°, -66.1570000°
  Altitud:      2558 m
  Velocidad:    45.3 km/h
  Rumbo:        135.0°
  Batería:      85%
  Timestamp:    2026-01-29 14:30:15
  Estado:       EN MOVIMIENTO, IGNICIÓN ON
────────────────────────────────────────────────────────────

[→] ACK enviado a GPS #1234 (SEQ=5)
```

### Cliente enviando datos:

```
[→] Mensaje #5 enviado (28 bytes)
    Pos: -17.393500°, -66.157000°
    Vel: 45.3 km/h, Rumbo: 135.0°, Bat: 85%
[←] ACK recibido para mensaje #5
```

---

## Análisis del Protocolo

### Eficiencia del Protocolo

**Overhead por mensaje:**
- Cabecera: 8 bytes
- Payload: 20 bytes
- **Total: 28 bytes**

**Comparación con otros formatos:**
- JSON equivalente: ~150-200 bytes
- XML equivalente: ~250-300 bytes
- **Ahorro**: ~82-91% de ancho de banda

**Consumo de batería estimado:**
- Envío cada 5s: ~17,280 mensajes/día
- Datos transmitidos: ~483 KB/día
- Consumo red 3G: ~0.1-0.5% batería/día

### Tolerancia a Errores

- **CRC-16** detecta:
  - 100% errores de 1 bit
  - 100% errores de 2 bits
  - 99.998% errores de burst ≤16 bits

- **Numeración de secuencia**:
  - Detecta pérdidas
  - Detecta duplicados
  - Rango: 0-65535 (se reinicia automáticamente)

---

## Características Implementadas

✅ **Requeridas:**
- [x] Formato de mensaje compacto (28 bytes)
- [x] Transmisión UDP eficiente
- [x] Detección de errores (CRC-16)
- [x] Manejo de errores (ACK, secuencia, reintentos)
- [x] Seguridad básica (validación de dispositivos)
- [x] Aplicaciones cliente-servidor funcionales

✅ **Extra:**
- [x] Simulación de movimiento realista
- [x] Múltiples modos de operación
- [x] Log persistente de mensajes
- [x] Estadísticas del servidor
- [x] Detección de mensajes perdidos/duplicados
- [x] Flags de estado (batería baja, SOS, movimiento)
- [x] Optimización de envío según contexto

---

## Troubleshooting

### Problema: "Address already in use"
**Solución:**
- Espera 30-60 segundos antes de reiniciar el servidor
- O usa otro puerto: `python gps_servidor.py 8888`

### Problema: Cliente no recibe ACK
**Causas posibles:**
- Firewall bloqueando UDP
- Servidor con ACK deshabilitado
- Timeout muy corto (normal en UDP)

### Problema: Mensajes perdidos
**Es normal en UDP:**
- El protocolo tolera pérdidas ocasionales
- Se registran en las estadísticas del servidor
- Para mayor confiabilidad: habilitar ACK y reintentos

---

## Referencias

Basado en conceptos de:
- **PDF 4 - Capa de Transporte**: UDP, checksum, manejo de errores
- **PDF 5 - Capa de Aplicaciones**: Sockets, cliente-servidor
- **PDF 3 - Capa de Red**: Direccionamiento, enrutamiento

---

## 📄 Licencia

Proyecto educativo - Uso libre para fines académicos