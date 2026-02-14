"""
Servidor GPS - Receptor Central de Datos GPS
Redes de Computadoras - Práctica 3

Este programa recibe datos de múltiples dispositivos GPS
y los procesa/almacena usando el protocolo UDP.
"""

import socket
import os
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
    TIPO_HEARTBEAT,
    convertir_coordenadas,
    desempaquetar_mensaje,
    empaquetar_ack,
    MAX_SEQ,
)


class ServidorGPS:
    def __init__(
        self,
        puerto=PUERTO_SERVIDOR,
        enviar_ack=True,
        log_path="gps_log.txt",
        max_log_bytes=1_000_000,
        ventana_tiempo_seg=300,
    ):
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
        self.ventana_tiempo_seg = ventana_tiempo_seg
        self.log_path = log_path
        self.max_log_bytes = max_log_bytes
        self._client_proc = None

        print("\n" + "=" * 60)
        print("  SERVIDOR GPS CENTRAL")
        print("=" * 60)
        print(f"  Puerto: {self.puerto}")
        print(f"  ACK automático: {'Sí' if self.enviar_ack else 'No'}")
        print(f"  Ventana tiempo: {self.ventana_tiempo_seg}s")
        if self.log_path:
            print(f"  Log: {self.log_path} (max {self.max_log_bytes} bytes)")
        else:
            print("  Log: deshabilitado")
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


    def _es_seq_mas_reciente(self, seq_nueva, seq_ultima):
        """
        Compara secuencias con wrap-around (16 bits).
        Retorna True si seq_nueva es mas reciente que seq_ultima.
        """
        if seq_nueva == seq_ultima:
            return False
        # Distancia hacia adelante en modulo 65536
        adelante = (seq_nueva - seq_ultima) % MAX_SEQ
        # Considerar "reciente" si esta en la mitad superior del anillo
        return 0 < adelante < (MAX_SEQ // 2)

    def procesar_mensaje(self, datos, direccion_cliente):
        """Procesa un mensaje GPS recibido"""
        id_disp = datos["id_dispositivo"]
        seq = datos["secuencia"]

        # Registrar dispositivo
        self.registrar_dispositivo(id_disp)

        # Verificar secuencia
        ultima_seq = self.dispositivos[id_disp]["ultima_seq"]

        if not self._es_seq_mas_reciente(seq, ultima_seq):
            # Mensaje duplicado o fuera de orden (incluye wrap-around)
            self.mensajes_duplicados += 1
            print(
                f"[!] Mensaje duplicado/antiguo: GPS #{id_disp}, SEQ={seq} (esperaba >{ultima_seq})"
            )
            return False

        # Calcular perdidas considerando wrap-around
        salto = (seq - ultima_seq) % MAX_SEQ
        if salto > 1:
            # Se perdieron mensajes
            perdidos = salto - 1
            self.mensajes_perdidos += perdidos
            print(
                f"[!] Se perdieron {perdidos} mensaje(s): GPS #{id_disp}, salto de SEQ {ultima_seq} a {seq}"
            )

        # Actualizar información del dispositivo
        self.dispositivos[id_disp]["ultima_seq"] = seq
        self.dispositivos[id_disp]["mensajes_recibidos"] += 1

        if datos["tipo"] == TIPO_DATOS_GPS:
            # Validar ventana temporal (anti-replay básico)
            ahora = time.time()
            if abs(datos["timestamp"] - ahora) > self.ventana_tiempo_seg:
                self.errores += 1
                print(
                    f"[!] Timestamp fuera de ventana: GPS #{id_disp}, TS={datos['timestamp']}"
                )
                return False

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
        elif datos["tipo"] == TIPO_HEARTBEAT:
            self.dispositivos[id_disp]["flags"] = datos["flags"]
            self.mostrar_heartbeat(datos, direccion_cliente)

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

    def _rotar_log_si_es_necesario(self):
        """Rotación simple: renombra log a .1 si supera el tamaño máximo"""
        if not self.log_path:
            return
        try:
            log_dir = os.path.dirname(self.log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            if os.path.exists(self.log_path):
                tam = os.path.getsize(self.log_path)
                if tam >= self.max_log_bytes:
                    destino = f"{self.log_path}.1"
                    if os.path.exists(destino):
                        os.remove(destino)
                    os.rename(self.log_path, destino)
        except OSError as e:
            print(f"[!] Error al rotar log: {e}")

    def mostrar_heartbeat(self, datos, direccion):
        """Muestra un heartbeat recibido"""
        print(f"\n{'─'*60}")
        print("[←] HEARTBEAT RECIBIDO")
        print(f"{'─'*60}")
        print(f"  Origen:       {direccion[0]}:{direccion[1]}")
        print(f"  Dispositivo:  GPS #{datos['id_dispositivo']}")
        print(f"  Secuencia:    #{datos['secuencia']}")
        print(
            f"  Timestamp:    {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"  Flags:        0x{datos['flags']:02X}")
        print(f"{'─'*60}\n")

    def guardar_log(self, datos):
        """Guarda los datos en un archivo de log"""
        if not self.log_path:
            return
        try:
            self._rotar_log_si_es_necesario()
            lat, lon = convertir_coordenadas(datos["latitud"], datos["longitud"])
            vel = datos["velocidad"] / 10.0
            rumbo = datos["rumbo"] / 10.0
            timestamp_str = datetime.fromtimestamp(datos["timestamp"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            with open(self.log_path, "a") as f:
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
                        if exito and datos["tipo"] in (TIPO_DATOS_GPS, TIPO_HEARTBEAT):
                            self.enviar_ack_mensaje(
                                datos["id_dispositivo"], datos["secuencia"], direccion
                            )
                    else:
                        # Error en el mensaje
                        self.errores += 1
                        print(
                            f"[✗] Error al procesar mensaje de {direccion}: {error}"
                        )

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
        try:
            puerto = int(sys.argv[1])
        except ValueError:
            print(
                "[✗] Puerto inválido. Uso: python src/gps_servidor.py [puerto] [ack=true|false] [log_path] [max_kb] [ventana_seg]"
            )
            return
        if not (0 <= puerto <= 65535):
            print("[✗] Puerto fuera de rango (0-65535).")
            return
    if len(sys.argv) >= 3:
        enviar_ack = sys.argv[2].lower() in ["true", "1", "si", "yes"]
    log_path = "gps_log.txt"
    max_log_bytes = 1_000_000
    if len(sys.argv) >= 4:
        log_path = sys.argv[3]
    if len(sys.argv) >= 5:
        try:
            max_log_bytes = int(sys.argv[4]) * 1024
        except ValueError:
            print(
                "[✗] max_kb inválido. Uso: python src/gps_servidor.py [puerto] [ack=true|false] [log_path] [max_kb] [ventana_seg]"
            )
            return
        if max_log_bytes <= 0:
            print("[✗] max_kb debe ser mayor que 0.")
            return
    ventana_tiempo_seg = 300
    if len(sys.argv) >= 6:
        try:
            ventana_tiempo_seg = int(sys.argv[5])
        except ValueError:
            print(
                "[✗] ventana_seg inválido. Uso: python src/gps_servidor.py [puerto] [ack=true|false] [log_path] [max_kb] [ventana_seg]"
            )
            return
        if ventana_tiempo_seg <= 0:
            print("[✗] ventana_seg debe ser mayor que 0.")
            return

    # Crear y ejecutar servidor
    servidor = ServidorGPS(
        puerto=puerto,
        enviar_ack=enviar_ack,
        log_path=log_path,
        max_log_bytes=max_log_bytes,
        ventana_tiempo_seg=ventana_tiempo_seg,
    )

    servidor.ejecutar()


if __name__ == "__main__":
    main()
