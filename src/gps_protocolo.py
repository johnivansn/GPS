"""
Protocolo GPS - Librería Compartida
Redes de Computadoras - Práctica 3

Formato del mensaje GPS (30 bytes total):
- Cabecera: 10 bytes (VER, TIPO, ID, SEQ, CHECKSUM, FLAGS)
- Payload: 20 bytes (LAT, LON, ALT, TIME, VEL, RUMBO, BAT, ESTADO)

FORMATO STRUCT: !BBHHHHiiHIHHBB
- B = 1 byte unsigned
- H = 2 bytes unsigned short
- I = 4 bytes unsigned int
- i = 4 bytes signed int
"""

import struct
import time

# ============== CONSTANTES DEL PROTOCOLO ==============
VERSION = 0x01
PUERTO_SERVIDOR = 9999
MAX_SEQ = 0x10000  # 65536, rango de 16 bits

# Tipos de mensaje
TIPO_DATOS_GPS = 0x01
TIPO_ACK = 0x02
TIPO_HEARTBEAT = 0x03

# Flags de estado
FLAG_BATERIA_BAJA = 0x01
FLAG_SOS = 0x02
FLAG_EN_MOVIMIENTO = 0x04
FLAG_IGNICION_ON = 0x08

# Clave secreta compartida
CLAVE_SECRETA = "MiClaveSecretaGPS2024"


# ============== FUNCIONES DE CHECKSUM (CRC-16) ==============
def calcular_checksum(datos):
    """Calcula CRC-16 para detección de errores"""
    crc = 0xFFFF
    for byte in datos:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def verificar_checksum(mensaje):
    """Verifica si el checksum del mensaje es correcto"""
    if len(mensaje) < 10:
        return False

    # Extraer checksum del mensaje (bytes 6-8)
    checksum_recibido = struct.unpack("!H", mensaje[6:8])[0]

    # Calcular checksum sin incluir el campo checksum
    datos_sin_checksum = mensaje[:6] + b"\x00\x00" + mensaje[8:]
    checksum_calculado = calcular_checksum(datos_sin_checksum)

    return checksum_recibido == checksum_calculado


# ============== EMPAQUETADO DE MENSAJES ==============
def empaquetar_mensaje_gps(
    id_dispositivo,
    secuencia,
    latitud,
    longitud,
    altitud,
    velocidad,
    rumbo,
    bateria,
    estado,
    flags=0,
):
    """
    Empaqueta un mensaje GPS completo (30 bytes)

    Formato: !BBHHHHiiHIHHBB = 30 bytes
    - VERSION(1) TIPO(1) ID(2) SEQ(2) CHECKSUM(2) FLAGS(2) = 10 bytes cabecera
    - LAT(4) LON(4) ALT(2) TIME(4) VEL(2) RUM(2) BAT(1) EST(1) = 20 bytes payload

    Parámetros:
    - latitud/longitud: Grados × 10^7 (ej: -17.3935 × 10^7 = -173935000)
    - altitud: Metros sobre el nivel del mar
    - velocidad: km/h × 10
    - rumbo: Grados × 10 (0-3600)
    - bateria: Porcentaje (0-100)
    """
    timestamp = int(time.time())

    # Construir mensaje sin checksum
    mensaje_sin_checksum = struct.pack(
        "!BBHHHHiiHIHHBB",
        VERSION,  # B: 1 byte
        TIPO_DATOS_GPS,  # B: 1 byte
        id_dispositivo,  # H: 2 bytes
        secuencia,  # H: 2 bytes
        0,  # H: 2 bytes (checksum placeholder)
        flags,  # H: 2 bytes
        latitud,  # i: 4 bytes (signed int)
        longitud,  # i: 4 bytes (signed int)
        altitud,  # H: 2 bytes
        timestamp,  # I: 4 bytes (unsigned int)
        velocidad,  # H: 2 bytes
        rumbo,  # H: 2 bytes
        bateria,  # B: 1 byte
        estado,  # B: 1 byte
    )

    # Calcular checksum
    checksum = calcular_checksum(mensaje_sin_checksum)

    # Construir mensaje final con checksum
    mensaje_final = struct.pack(
        "!BBHHHHiiHIHHBB",
        VERSION,
        TIPO_DATOS_GPS,
        id_dispositivo,
        secuencia,
        checksum,  # Checksum real
        flags,
        latitud,
        longitud,
        altitud,
        timestamp,
        velocidad,
        rumbo,
        bateria,
        estado,
    )

    return mensaje_final


def empaquetar_ack(id_dispositivo, secuencia_ack):
    """Empaqueta un mensaje ACK (10 bytes - cabecera completa)"""
    mensaje_sin_checksum = struct.pack(
        "!BBHHHH",
        VERSION,
        TIPO_ACK,
        id_dispositivo,
        secuencia_ack,
        0,  # checksum placeholder
        0,  # flags = 0
    )

    checksum = calcular_checksum(mensaje_sin_checksum)

    mensaje_final = struct.pack(
        "!BBHHHH",
        VERSION,
        TIPO_ACK,
        id_dispositivo,
        secuencia_ack,
        checksum,
        0,  # flags = 0
    )

    return mensaje_final


def empaquetar_heartbeat(id_dispositivo, secuencia, flags=0):
    """Empaqueta un mensaje HEARTBEAT (10 bytes - cabecera completa)"""
    mensaje_sin_checksum = struct.pack(
        "!BBHHHH",
        VERSION,
        TIPO_HEARTBEAT,
        id_dispositivo,
        secuencia,
        0,  # checksum placeholder
        flags,
    )

    checksum = calcular_checksum(mensaje_sin_checksum)

    mensaje_final = struct.pack(
        "!BBHHHH",
        VERSION,
        TIPO_HEARTBEAT,
        id_dispositivo,
        secuencia,
        checksum,
        flags,
    )

    return mensaje_final


# ============== DESEMPAQUETADO DE MENSAJES ==============
def desempaquetar_mensaje(mensaje):
    """
    Desempaqueta un mensaje recibido
    Retorna un diccionario con los campos o None si hay error
    """
    if len(mensaje) < 10:
        return None, "Mensaje demasiado corto"

    # Verificar checksum
    if not verificar_checksum(mensaje):
        return None, "Checksum inválido"

    # Desempaquetar cabecera (10 bytes)
    try:
        campos = struct.unpack("!BBHHHH", mensaje[:10])
        version, tipo, id_disp, secuencia, checksum, flags = campos

        if version != VERSION:
            return None, f"Versión incorrecta: {version}"

        resultado = {
            "version": version,
            "tipo": tipo,
            "id_dispositivo": id_disp,
            "secuencia": secuencia,
            "flags": flags,
            "checksum": checksum,
        }

        # Si es mensaje de datos GPS, desempaquetar payload
        # Payload empieza en byte 10, ocupa 20 bytes
        if tipo == TIPO_DATOS_GPS and len(mensaje) >= 30:
            payload = struct.unpack("!iiHIHHBB", mensaje[10:30])
            latitud, longitud, altitud, timestamp, velocidad, rumbo, bateria, estado = (
                payload
            )

            resultado.update(
                {
                    "latitud": latitud,
                    "longitud": longitud,
                    "altitud": altitud,
                    "timestamp": timestamp,
                    "velocidad": velocidad,
                    "rumbo": rumbo,
                    "bateria": bateria,
                    "estado": estado,
                }
            )

        return resultado, "OK"

    except struct.error as e:
        return None, f"Error al desempaquetar: {e}"


# ============== FUNCIONES DE UTILIDAD ==============
def convertir_coordenadas(lat_raw, lon_raw):
    """Convierte coordenadas de formato int a float (grados)"""
    latitud = lat_raw / 10000000.0
    longitud = lon_raw / 10000000.0
    return latitud, longitud


def coordenadas_a_raw(lat_float, lon_float):
    """Convierte coordenadas de float (grados) a formato int"""
    latitud = int(lat_float * 10000000)
    longitud = int(lon_float * 10000000)
    return latitud, longitud


def mostrar_mensaje(datos):
    """Muestra un mensaje de forma legible"""
    if datos["tipo"] == TIPO_DATOS_GPS:
        lat, lon = convertir_coordenadas(datos["latitud"], datos["longitud"])
        vel_real = datos["velocidad"] / 10.0
        rumbo_real = datos["rumbo"] / 10.0

        print(f"\n{'='*60}")
        print(f"MENSAJE GPS - Dispositivo {datos['id_dispositivo']}")
        print(f"{'='*60}")
        print(f"  Secuencia:    {datos['secuencia']}")
        print(f"  Posición:     {lat:.7f}°, {lon:.7f}°")
        print(f"  Altitud:      {datos['altitud']} m")
        print(f"  Velocidad:    {vel_real:.1f} km/h")
        print(f"  Rumbo:        {rumbo_real:.1f}°")
        print(f"  Batería:      {datos['bateria']}%")
        print(f"  Timestamp:    {time.ctime(datos['timestamp'])}")
        print(f"  Flags:        0x{datos['flags']:02X}")

        # Decodificar flags
        if datos["flags"] & FLAG_BATERIA_BAJA:
            print("  ⚠ BATERÍA BAJA")
        if datos["flags"] & FLAG_SOS:
            print("    B SEÑAL SOS")
        if datos["flags"] & FLAG_EN_MOVIMIENTO:
            print("    EN MOVIMIENTO")
        if datos["flags"] & FLAG_IGNICION_ON:
            print("    IGNICIÓN ENCENDIDA")

        print(f"{'='*60}\n")

    elif datos["tipo"] == TIPO_ACK:
        print(f"[ACK] Dispositivo {datos['id_dispositivo']}, SEQ={datos['secuencia']}")

    elif datos["tipo"] == TIPO_HEARTBEAT:
        print(f"[HEARTBEAT] Dispositivo {datos['id_dispositivo']}")


# ============== FUNCIÓN DE PRUEBA ==============
if __name__ == "__main__":
    print("=== Prueba del Protocolo GPS ===\n")

    # Crear un mensaje de ejemplo
    print("1. Creando mensaje GPS...")

    # Coordenadas de Cochabamba, Bolivia
    lat, lon = coordenadas_a_raw(-17.3935, -66.1570)

    mensaje = empaquetar_mensaje_gps(
        id_dispositivo=1234,
        secuencia=1,
        latitud=lat,
        longitud=lon,
        altitud=2558,
        velocidad=450,  # 45.0 km/h
        rumbo=1350,  # 135.0 grados
        bateria=85,
        estado=0x00,
        flags=FLAG_EN_MOVIMIENTO | FLAG_IGNICION_ON,
    )

    print(f"   Tamaño del mensaje: {len(mensaje)} bytes")
    print(f"   Bytes (hex): {mensaje.hex()}")

    # Desempaquetar el mensaje
    print("\n2. Desempaquetando mensaje...")
    datos, error = desempaquetar_mensaje(mensaje)

    if datos:
        print("   ✓ Mensaje válido")
        mostrar_mensaje(datos)
    else:
        print(f"   ✗ Error: {error}")

    # Probar checksum inválido
    print("\n3. Probando mensaje corrupto...")
    mensaje_corrupto = bytearray(mensaje)
    mensaje_corrupto[10] ^= 0xFF  # Corromper un byte

    datos, error = desempaquetar_mensaje(bytes(mensaje_corrupto))
    if datos:
        print("   ✗ No se detectó la corrupción")
    else:
        print(f"   ✓ Error detectado: {error}")

    # Crear ACK
    print("\n4. Creando mensaje ACK...")
    ack = empaquetar_ack(1234, 1)
    print(f"   Tamaño del ACK: {len(ack)} bytes")
    print(f"   Bytes (hex): {ack.hex()}")

    datos_ack, _ = desempaquetar_mensaje(ack)
    if datos_ack:
        mostrar_mensaje(datos_ack)
