"""
Cliente GPS - Simulador de Dispositivo GPS
Redes de Computadoras - Práctica 3

Este programa simula un dispositivo GPS que envía datos de posición
al servidor central usando el protocolo UDP.
"""

import socket
import time
import random
import sys
import argparse
from gps_protocolo import (
    FLAG_BATERIA_BAJA,
    FLAG_EN_MOVIMIENTO,
    FLAG_IGNICION_ON,
    PUERTO_SERVIDOR,
    TIPO_ACK,
    coordenadas_a_raw,
    desempaquetar_mensaje,
    empaquetar_mensaje_gps,
    empaquetar_heartbeat,
    MAX_SEQ,
)


class DispositivoGPS:
    def __init__(
        self, id_dispositivo, servidor_ip="127.0.0.1", servidor_puerto=PUERTO_SERVIDOR
    ):
        self.id_dispositivo = id_dispositivo
        self.servidor = (servidor_ip, servidor_puerto)
        self.secuencia = 0
        self.socket = None

        # Estado del vehículo simulado
        self.latitud = -17.3935  # Cochabamba inicial
        self.longitud = -66.1570
        self.altitud = 2558
        self.velocidad = 0.0  # km/h
        self.rumbo = 0.0  # grados
        self.bateria = 100
        self.en_movimiento = False
        self.ignicion = False

        print(f"\n{'='*60}")
        print(f"  DISPOSITIVO GPS #{self.id_dispositivo}")
        print(f"{'='*60}")
        print(f"  Servidor: {servidor_ip}:{servidor_puerto}")
        print(f"  Posición inicial: {self.latitud:.4f}°, {self.longitud:.4f}°")
        print(f"{'='*60}\n")

    def conectar(self):
        """Crea el socket UDP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(3.0)  # Timeout de 3 segundos para ACK
            print("[✓] Socket UDP creado exitosamente")
            return True
        except socket.error as e:
            print(f"[✗] Error al crear socket: {e}")
            return False

    def simular_movimiento(self):
        """Simula el movimiento del vehículo"""
        if self.en_movimiento:
            # Avanzar en la dirección del rumbo
            # Aproximación simple: 1 km = 0.01 grados
            desplazamiento = (self.velocidad / 3600) * 0.01  # Por segundo

            import math

            rumbo_rad = math.radians(self.rumbo)
            self.latitud += desplazamiento * math.cos(rumbo_rad)
            self.longitud += desplazamiento * math.sin(rumbo_rad)

            # Pequeñas variaciones aleatorias
            self.velocidad += random.uniform(-2, 2)
            self.velocidad = max(0, min(120, self.velocidad))  # Limitar 0-120 km/h

            self.rumbo += random.uniform(-5, 5)
            self.rumbo = self.rumbo % 360

            # Consumo de batería (más rápido si está en movimiento)
            self.bateria -= random.uniform(0.01, 0.05)
        else:
            # Consumo mínimo de batería en reposo
            self.bateria -= random.uniform(0.001, 0.01)

        self.bateria = max(0, self.bateria)

    def obtener_flags(self):
        """Determina los flags del mensaje según el estado"""
        flags = 0

        if self.bateria < 20:
            flags |= FLAG_BATERIA_BAJA

        if self.en_movimiento:
            flags |= FLAG_EN_MOVIMIENTO

        if self.ignicion:
            flags |= FLAG_IGNICION_ON

        return flags

    def enviar_datos(self):
        """Envía datos GPS al servidor"""
        if self.socket is None:
            print("[✗] Error: socket no inicializado")
            return False

        self.secuencia = (self.secuencia + 1) % MAX_SEQ

        # Convertir coordenadas a formato raw
        lat_raw, lon_raw = coordenadas_a_raw(self.latitud, self.longitud)

        # Preparar datos
        vel_raw = int(self.velocidad * 10)
        rumbo_raw = int(self.rumbo * 10)
        flags = self.obtener_flags()

        # Empaquetar mensaje
        mensaje = empaquetar_mensaje_gps(
            id_dispositivo=self.id_dispositivo,
            secuencia=self.secuencia,
            latitud=lat_raw,
            longitud=lon_raw,
            altitud=self.altitud,
            velocidad=vel_raw,
            rumbo=rumbo_raw,
            bateria=int(self.bateria),
            estado=0x00,
            flags=flags,
        )

        # Enviar por UDP
        try:
            self.socket.sendto(mensaje, self.servidor)
            print(f"[→] Mensaje #{self.secuencia} enviado ({len(mensaje)} bytes)")
            print(f"    Pos: {self.latitud:.6f}°, {self.longitud:.6f}°")
            print(
                f"    Vel: {self.velocidad:.1f} km/h, Rumbo: {self.rumbo:.1f}°, Bat: {self.bateria:.0f}%"
            )

            # Esperar ACK opcional
            try:
                respuesta, addr = self.socket.recvfrom(1024)
                datos_ack, error = desempaquetar_mensaje(respuesta)

                if datos_ack and datos_ack["tipo"] == TIPO_ACK:
                    if datos_ack["secuencia"] == self.secuencia:
                        print(f"[←] ACK recibido para mensaje #{self.secuencia}")
                    else:
                        print(
                            f"[!] ACK recibido con secuencia incorrecta: {datos_ack['secuencia']}"
                        )

            except socket.timeout:
                print("[!] No se recibió ACK (timeout)")

            return True

        except socket.error as e:
            print(f"[✗] Error al enviar: {e}")
            return False

    def enviar_heartbeat(self):
        """Envía un heartbeat al servidor"""
        if self.socket is None:
            print("[✗] Error: socket no inicializado")
            return False

        self.secuencia = (self.secuencia + 1) % MAX_SEQ
        flags = self.obtener_flags()

        mensaje = empaquetar_heartbeat(
            id_dispositivo=self.id_dispositivo,
            secuencia=self.secuencia,
            flags=flags,
        )

        try:
            self.socket.sendto(mensaje, self.servidor)
            print(f"[→] HEARTBEAT #{self.secuencia} enviado ({len(mensaje)} bytes)")
            return True
        except socket.error as e:
            print(f"[✗] Error al enviar heartbeat: {e}")
            return False

    def ejecutar(self, intervalo=5, duracion=60):
        """
        Ejecuta el cliente GPS durante un tiempo determinado

        Parámetros:
        - intervalo: segundos entre envíos
        - duracion: duración total en segundos (0 = infinito)
        """
        if not self.conectar():
            return

        print("\n[▶] Iniciando envío de datos GPS...")
        print(f"    Intervalo: {intervalo}s")
        if duracion > 0:
            print(f"    Duración: {duracion}s")
        else:
            print("    Duración: indefinido (Ctrl+C para detener)")
        print()

        tiempo_inicio = time.time()

        try:
            while True:
                # Verificar duración
                if duracion > 0 and (time.time() - tiempo_inicio) >= duracion:
                    print(f"\n[■] Tiempo completado ({duracion}s)")
                    break

                # Simular movimiento
                self.simular_movimiento()

                # Enviar datos
                self.enviar_datos()

                # Esperar antes del siguiente envío
                time.sleep(intervalo)

        except KeyboardInterrupt:
            print("\n\n[■] Detenido por el usuario")
        finally:
            if self.socket is not None:
                self.socket.close()
                print("[✓] Socket cerrado\n")
            else:
                print("[!] Socket no estaba inicializado\n")

    def ejecutar_heartbeat(self, intervalo=10, duracion=60):
        """
        Ejecuta envío periódico de heartbeats
        """
        if not self.conectar():
            return

        print("\n[▶] Iniciando envío de HEARTBEAT...")
        print(f"    Intervalo: {intervalo}s")
        if duracion > 0:
            print(f"    Duración: {duracion}s")
        else:
            print("    Duración: indefinido (Ctrl+C para detener)")
        print()

        tiempo_inicio = time.time()

        try:
            while True:
                if duracion > 0 and (time.time() - tiempo_inicio) >= duracion:
                    print(f"\n[■] Tiempo completado ({duracion}s)")
                    break

                self.enviar_heartbeat()
                time.sleep(intervalo)

        except KeyboardInterrupt:
            print("\n\n[■] Detenido por el usuario")
        finally:
            if self.socket is not None:
                self.socket.close()
                print("[✓] Socket cerrado\n")
            else:
                print("[!] Socket no estaba inicializado\n")


def mostrar_menu():
    """Muestra el menú de opciones"""
    print("\n" + "=" * 60)
    print("  SIMULADOR DE DISPOSITIVO GPS")
    print("=" * 60)
    print("\nOpciones de simulación:")
    print("  1. Vehículo estacionado (sin movimiento)")
    print("  2. Vehículo en movimiento urbano (30 km/h)")
    print("  3. Vehículo en carretera (80 km/h)")
    print("  4. Modo personalizado")
    print("  5. Enviar solo HEARTBEAT")
    print("  6. Salir")
    print("=" * 60)


def main():
    """Función principal"""

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--mode", choices=["static", "urban", "highway", "custom", "heartbeat"])
    parser.add_argument("--interval", type=int, default=None)
    parser.add_argument("--duration", type=int, default=None)
    parser.add_argument("--speed", type=float, default=None)
    parser.add_argument("--heading", type=float, default=None)
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    parser.add_argument("--battery", type=float, default=None)
    parser.add_argument("--id", dest="device_id", type=int, default=None)
    parser.add_argument("--ip", dest="server_ip", type=str, default=None)
    parser.add_argument("--port", dest="server_port", type=int, default=None)
    parser.add_argument("--once", type=str, default="false")

    args, _ = parser.parse_known_args()

    # Configuración por defecto
    servidor_ip = "127.0.0.1"
    servidor_puerto = PUERTO_SERVIDOR
    id_dispositivo = random.randint(1000, 9999)

    # Permitir argumentos de línea de comandos
    usa_flags = any(arg.startswith("--") for arg in sys.argv[1:])
    if not usa_flags:
        if len(sys.argv) >= 2:
            servidor_ip = sys.argv[1]
        if len(sys.argv) >= 3:
            try:
                servidor_puerto = int(sys.argv[2])
            except ValueError:
                print("[✗] Puerto inválido. Uso: python src/gps_cliente.py [ip] [puerto] [id]")
                return
            if not (0 <= servidor_puerto <= 65535):
                print("[✗] Puerto fuera de rango (0-65535).")
                return
        if len(sys.argv) >= 4:
            try:
                id_dispositivo = int(sys.argv[3])
            except ValueError:
                print("[✗] ID inválido. Uso: python src/gps_cliente.py [ip] [puerto] [id]")
                return
            if not (0 <= id_dispositivo <= 65535):
                print("[✗] ID fuera de rango (0-65535).")
                return

    if args.server_ip is not None:
        servidor_ip = args.server_ip
    if args.server_port is not None:
        servidor_puerto = args.server_port

    if args.device_id is not None:
        id_dispositivo = args.device_id

    if args.mode:
        gps = DispositivoGPS(id_dispositivo, servidor_ip, servidor_puerto)
        if args.lat is not None:
            gps.latitud = args.lat
        if args.lon is not None:
            gps.longitud = args.lon
        if args.speed is not None:
            gps.velocidad = args.speed
        if args.heading is not None:
            gps.rumbo = args.heading
        if args.battery is not None:
            gps.bateria = args.battery

        intervalo = args.interval if args.interval is not None else 5
        duracion = args.duration if args.duration is not None else 0
        once = args.once.lower() in ["true", "1", "si", "yes"]

        if args.mode == "static":
            gps.velocidad = 0
            gps.en_movimiento = False
            gps.ignicion = False
        elif args.mode == "urban":
            gps.velocidad = 30 if args.speed is None else gps.velocidad
            gps.rumbo = random.uniform(0, 360) if args.heading is None else gps.rumbo
            gps.en_movimiento = True
            gps.ignicion = True
        elif args.mode == "highway":
            gps.velocidad = 80 if args.speed is None else gps.velocidad
            gps.rumbo = random.uniform(0, 360) if args.heading is None else gps.rumbo
            gps.en_movimiento = True
            gps.ignicion = True
        elif args.mode == "custom":
            gps.en_movimiento = gps.velocidad > 0
            gps.ignicion = gps.velocidad > 0
        elif args.mode == "heartbeat":
            gps.en_movimiento = False
            gps.ignicion = False
            if once:
                gps.conectar()
                gps.enviar_heartbeat()
                if gps.socket is not None:
                    gps.socket.close()
                return
            gps.ejecutar_heartbeat(intervalo=intervalo, duracion=duracion)
            return

        if once:
            gps.conectar()
            gps.enviar_datos()
            if gps.socket is not None:
                gps.socket.close()
            return
        gps.ejecutar(intervalo=intervalo, duracion=duracion)
        return

    while True:
        mostrar_menu()
        opcion = input("\nSeleccione una opción (1-6): ").strip()

        if opcion == "6":
            print("\n[✓] Saliendo...\n")
            break

        # Crear dispositivo GPS
        gps = DispositivoGPS(id_dispositivo, servidor_ip, servidor_puerto)

        if opcion == "1":
            # Vehículo estacionado
            gps.velocidad = 0
            gps.en_movimiento = False
            gps.ignicion = False
            gps.ejecutar(intervalo=10, duracion=60)

        elif opcion == "2":
            # Vehículo urbano
            gps.velocidad = 30
            gps.rumbo = random.uniform(0, 360)
            gps.en_movimiento = True
            gps.ignicion = True
            gps.ejecutar(intervalo=5, duracion=60)

        elif opcion == "3":
            # Vehículo en carretera
            gps.velocidad = 80
            gps.rumbo = random.uniform(0, 360)
            gps.en_movimiento = True
            gps.ignicion = True
            gps.ejecutar(intervalo=3, duracion=60)

        elif opcion == "4":
            # Modo personalizado
            print("\n--- Configuración Personalizada ---")
            try:
                intervalo = int(input("Intervalo de envío (segundos, ej: 5): "))
                duracion = int(input("Duración total (segundos, 0=infinito): "))
                velocidad = float(input("Velocidad inicial (km/h, ej: 50): "))
                rumbo = float(input("Rumbo inicial (grados, 0-360): "))

                gps.velocidad = velocidad
                gps.rumbo = rumbo
                gps.en_movimiento = velocidad > 0
                gps.ignicion = velocidad > 0

                gps.ejecutar(intervalo=intervalo, duracion=duracion)

            except ValueError:
                print("[✗] Valores inválidos, intente nuevamente")
        elif opcion == "5":
            # Solo heartbeat
            gps.en_movimiento = False
            gps.ignicion = False
            gps.ejecutar_heartbeat(intervalo=10, duracion=60)
        else:
            print("[✗] Opción inválida")


if __name__ == "__main__":
    main()
