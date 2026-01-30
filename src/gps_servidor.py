"""
Servidor GPS - Receptor Central de Datos GPS
Redes de Computadoras - Práctica 3

Este programa recibe datos de múltiples dispositivos GPS
y los procesa/almacena usando el protocolo UDP.
"""

import socket
import time
import sys
from datetime import datetime
from gps_protocolo import (
    FLAG_BATERIA_BAJA,
    FLAG_EN_MOVIMIENTO,
    FLAG_IGNICION_ON,
    FLAG_SOS,
    PUERTO_SERVIDOR,
    TIPO_DATOS_GPS,
    convertir_coordenadas,
    desempaquetar_mensaje,
    empaquetar_ack,
)


class ServidorGPS:
    def __init__(self, puerto=PUERTO_SERVIDOR, enviar_ack=True):
        self.puerto = puerto
        self.enviar_ack = enviar_ack
        self.socket = None
        self.dispositivos = (
            {}
        )  # {id_dispositivo: {'ultima_seq': n, 'ultima_pos': (lat,lon), ...}}
        self.mensajes_recibidos = 0
        self.mensajes_perdidos = 0
        self.mensajes_duplicados = 0
        self.errores = 0

        print("\n" + "=" * 60)
        print("  SERVIDOR GPS CENTRAL")
        print("=" * 60)
        print(f"  Puerto: {self.puerto}")
        print(f"  ACK automático: {'Sí' if self.enviar_ack else 'No'}")
        print("=" * 60 + "\n")

    def iniciar(self):
        """Inicia el servidor UDP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(("0.0.0.0", self.puerto))
            # Agregar timeout para que Ctrl+C funcione en Windows
            self.socket.settimeout(1.0)
            print(f"[✓] Servidor escuchando en puerto {self.puerto}")
            print("[✓] Esperando dispositivos GPS...\n")
            return True
        except socket.error as e:
            print(f"[✗] Error al iniciar servidor: {e}")
            return False

    def registrar_dispositivo(self, id_dispositivo):
        """Registra un nuevo dispositivo o actualiza su información"""
        if id_dispositivo not in self.dispositivos:
            self.dispositivos[id_dispositivo] = {
                "primera_conexion": time.time(),
                "ultima_conexion": time.time(),
                "ultima_seq": 0,
                "mensajes_recibidos": 0,
                "ultima_pos": None,
                "ultima_velocidad": 0,
                "ultimo_rumbo": 0,
                "bateria": 100,
                "flags": 0,
            }
            print(f"\n[+] Nuevo dispositivo registrado: GPS #{id_dispositivo}")
        else:
            self.dispositivos[id_dispositivo]["ultima_conexion"] = time.time()

    def procesar_mensaje(self, datos, direccion_cliente):
        """Procesa un mensaje GPS recibido"""
        id_disp = datos["id_dispositivo"]
        seq = datos["secuencia"]

        # Registrar dispositivo
        self.registrar_dispositivo(id_disp)

        # Verificar secuencia
        ultima_seq = self.dispositivos[id_disp]["ultima_seq"]

        if seq <= ultima_seq:
            # Mensaje duplicado o fuera de orden
            self.mensajes_duplicados += 1
            print(
                f"[!] Mensaje duplicado/antiguo: GPS #{id_disp}, SEQ={seq} (esperaba >{ultima_seq})"
            )
            return False

        if seq > ultima_seq + 1:
            # Se perdieron mensajes
            perdidos = seq - ultima_seq - 1
            self.mensajes_perdidos += perdidos
            print(
                f"[!] Se perdieron {perdidos} mensaje(s): GPS #{id_disp}, salto de SEQ {ultima_seq} a {seq}"
            )

        # Actualizar información del dispositivo
        self.dispositivos[id_disp]["ultima_seq"] = seq
        self.dispositivos[id_disp]["mensajes_recibidos"] += 1

        if datos["tipo"] == TIPO_DATOS_GPS:
            lat, lon = convertir_coordenadas(datos["latitud"], datos["longitud"])
            vel = datos["velocidad"] / 10.0
            rumbo = datos["rumbo"] / 10.0

            self.dispositivos[id_disp]["ultima_pos"] = (lat, lon)
            self.dispositivos[id_disp]["ultima_velocidad"] = vel
            self.dispositivos[id_disp]["ultimo_rumbo"] = rumbo
            self.dispositivos[id_disp]["bateria"] = datos["bateria"]
            self.dispositivos[id_disp]["flags"] = datos["flags"]

            # Mostrar datos recibidos
            self.mostrar_datos_gps(datos, direccion_cliente)

            # Guardar en log (opcional)
            self.guardar_log(datos)

        self.mensajes_recibidos += 1
        return True

    def mostrar_datos_gps(self, datos, direccion):
        """Muestra los datos GPS recibidos en formato legible"""
        lat, lon = convertir_coordenadas(datos["latitud"], datos["longitud"])
        vel = datos["velocidad"] / 10.0
        rumbo = datos["rumbo"] / 10.0

        print(f"\n{'─'*60}")
        print("[←] DATOS GPS RECIBIDOS")
        print(f"{'─'*60}")
        print(f"  Origen:       {direccion[0]}:{direccion[1]}")
        print(f"  Dispositivo:  GPS #{datos['id_dispositivo']}")
        print(f"  Secuencia:    #{datos['secuencia']}")
        print(f"  Coordenadas:  {lat:.7f}°, {lon:.7f}°")
        print(f"  Altitud:      {datos['altitud']} m")
        print(f"  Velocidad:    {vel:.1f} km/h")
        print(f"  Rumbo:        {rumbo:.1f}°")
        print(f"  Batería:      {datos['bateria']}%")
        print(
            f"  Timestamp:    {datetime.fromtimestamp(datos['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Mostrar flags activos
        flags_activos = []
        if datos["flags"] & FLAG_BATERIA_BAJA:
            flags_activos.append("⚠ BATERÍA BAJA")
        if datos["flags"] & FLAG_SOS:
            flags_activos.append("🆘 SOS")
        if datos["flags"] & FLAG_EN_MOVIMIENTO:
            flags_activos.append("🚗 EN MOVIMIENTO")
        if datos["flags"] & FLAG_IGNICION_ON:
            flags_activos.append("🔑 IGNICIÓN ON")

        if flags_activos:
            print(f"  Estado:       {', '.join(flags_activos)}")

        print(f"{'─'*60}\n")

    def enviar_ack_mensaje(self, id_dispositivo, secuencia, direccion):
        """Envía un ACK al dispositivo"""
        if not self.enviar_ack:
            return

        if self.socket is None:
            print("[✗] Error: socket no inicializado")
            return

        try:
            ack = empaquetar_ack(id_dispositivo, secuencia)
            self.socket.sendto(ack, direccion)
            print(f"[→] ACK enviado a GPS #{id_dispositivo} (SEQ={secuencia})")
        except socket.error as e:
            print(f"[✗] Error al enviar ACK: {e}")

    def guardar_log(self, datos):
        """Guarda los datos en un archivo de log"""
        try:
            lat, lon = convertir_coordenadas(datos["latitud"], datos["longitud"])
            vel = datos["velocidad"] / 10.0
            rumbo = datos["rumbo"] / 10.0
            timestamp_str = datetime.fromtimestamp(datos["timestamp"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            with open("gps_log.txt", "a") as f:
                f.write(
                    f"{timestamp_str}|GPS{datos['id_dispositivo']}|SEQ{datos['secuencia']}|"
                )
                f.write(f"{lat:.7f}|{lon:.7f}|{datos['altitud']}|")
                f.write(
                    f"{vel:.1f}|{rumbo:.1f}|{datos['bateria']}|0x{datos['flags']:02X}\n"
                )

        except IOError as e:
            print(f"[!] Error al guardar log: {e}")

    def mostrar_estadisticas(self):
        """Muestra estadísticas del servidor"""
        print("\n" + "=" * 60)
        print("  ESTADÍSTICAS DEL SERVIDOR")
        print("=" * 60)
        print(f"  Mensajes recibidos:  {self.mensajes_recibidos}")
        print(f"  Mensajes perdidos:   {self.mensajes_perdidos}")
        print(f"  Mensajes duplicados: {self.mensajes_duplicados}")
        print(f"  Errores detectados:  {self.errores}")
        print(f"  Dispositivos activos: {len(self.dispositivos)}")
        print("=" * 60)

        if self.dispositivos:
            print("\n  DISPOSITIVOS CONECTADOS:")
            print("  " + "-" * 58)
            for id_disp, info in self.dispositivos.items():
                tiempo_desde = int(time.time() - info["ultima_conexion"])
                print(
                    f"  GPS #{id_disp:4d} | Mensajes: {info['mensajes_recibidos']:4d} | "
                    f"Última SEQ: {info['ultima_seq']:4d} | "
                    f"Hace: {tiempo_desde}s"
                )

                if info["ultima_pos"]:
                    lat, lon = info["ultima_pos"]
                    print(
                        f"           | Pos: {lat:.6f}°, {lon:.6f}° | "
                        f"Vel: {info['ultima_velocidad']:.1f} km/h | "
                        f"Bat: {info['bateria']}%"
                    )
            print("  " + "-" * 58)
        print()

    def ejecutar(self):
        """Ejecuta el servidor en modo escucha"""
        if not self.iniciar():
            print("\n[✗] No se pudo iniciar el servidor. Saliendo...\n")
            return

        print("[▶] Servidor en ejecución (Ctrl+C para detener)\n")

        try:
            while True:
                # Recibir mensaje con timeout
                try:
                    mensaje, direccion = self.socket.recvfrom(1024)  # type: ignore

                    # Desempaquetar mensaje
                    datos, error = desempaquetar_mensaje(mensaje)

                    if datos:
                        # Procesar mensaje válido
                        exito = self.procesar_mensaje(datos, direccion)

                        # Enviar ACK si está habilitado y el mensaje fue procesado
                        if exito and datos["tipo"] == TIPO_DATOS_GPS:
                            self.enviar_ack_mensaje(
                                datos["id_dispositivo"], datos["secuencia"], direccion
                            )
                    else:
                        # Error en el mensaje
                        self.errores += 1
                        print(f"[✗] Error al procesar mensaje de {direccion}: {error}")

                except socket.timeout:
                    # Timeout normal, continuar esperando
                    continue
                except socket.error as e:
                    print(f"[✗] Error de socket: {e}")

        except KeyboardInterrupt:
            print("\n\n[■] Servidor detenido por el usuario")
        finally:
            self.mostrar_estadisticas()
            if self.socket is not None:
                self.socket.close()
                print("[✓] Socket cerrado\n")
            else:
                print("[!] Socket ya estaba cerrado\n")


def main():
    """Función principal"""

    # Configuración por defecto
    puerto = PUERTO_SERVIDOR
    enviar_ack = True

    # Argumentos de línea de comandos
    if len(sys.argv) >= 2:
        puerto = int(sys.argv[1])
    if len(sys.argv) >= 3:
        enviar_ack = sys.argv[2].lower() in ["true", "1", "si", "yes"]

    # Crear y ejecutar servidor
    servidor = ServidorGPS(puerto=puerto, enviar_ack=enviar_ack)
    servidor.ejecutar()


if __name__ == "__main__":
    main()
