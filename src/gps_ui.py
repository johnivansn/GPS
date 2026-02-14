"""
UI de control (PyQt5) para cliente/servidor GPS.
Requiere: pip install PyQt5
"""

import subprocess
import sys
import os
from PyQt5 import QtWidgets, QtCore


class GPSUI(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Control GPS")
        self.resize(1000, 650)

        self.server_proc = None
        self.client_proc = None

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main = QtWidgets.QVBoxLayout(central)

        header = QtWidgets.QLabel("Visualizador Interactivo del Protocolo GPS")
        header.setObjectName("Header")
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main.addWidget(header)

        tabs = QtWidgets.QTabBar()
        tabs.addTab("Red y Comunicación")
        tabs.addTab("Estructura del Paquete")
        tabs.addTab("Mapa GPS")
        tabs.setObjectName("TopTabs")
        main.addWidget(tabs)

        content = QtWidgets.QHBoxLayout()
        main.addLayout(content, 1)

        right = QtWidgets.QVBoxLayout()
        left = QtWidgets.QVBoxLayout()
        content.addLayout(right, 2)
        content.addLayout(left, 1)

        # Configuración del dispositivo
        cfg = QtWidgets.QGroupBox("Configuración del Dispositivo")
        cfg_layout = QtWidgets.QFormLayout(cfg)
        self.device_id = QtWidgets.QSpinBox()
        self.device_id.setRange(0, 65535)
        self.device_id.setValue(1234)
        self.server_port = QtWidgets.QSpinBox()
        self.server_port.setRange(1, 65535)
        self.server_port.setValue(9999)
        self.lat = QtWidgets.QDoubleSpinBox()
        self.lat.setDecimals(6)
        self.lat.setRange(-90, 90)
        self.lat.setValue(-17.3935)
        self.lon = QtWidgets.QDoubleSpinBox()
        self.lon.setDecimals(6)
        self.lon.setRange(-180, 180)
        self.lon.setValue(-66.1570)
        self.speed = QtWidgets.QDoubleSpinBox()
        self.speed.setRange(0, 300)
        self.heading = QtWidgets.QDoubleSpinBox()
        self.heading.setRange(0, 359)
        self.battery = QtWidgets.QDoubleSpinBox()
        self.battery.setRange(0, 100)
        self.battery.setValue(100)

        cfg_layout.addRow("ID", self.device_id)
        cfg_layout.addRow("Puerto Servidor", self.server_port)
        cfg_layout.addRow("Latitud", self.lat)
        cfg_layout.addRow("Longitud", self.lon)
        cfg_layout.addRow("Velocidad (km/h)", self.speed)
        cfg_layout.addRow("Rumbo (grados)", self.heading)
        cfg_layout.addRow("Batería (%)", self.battery)
        left.addWidget(cfg)

        # Simulación
        sim = QtWidgets.QGroupBox("Simulación")
        sim_layout = QtWidgets.QFormLayout(sim)
        self.scenario = QtWidgets.QComboBox()
        self.scenario.addItems(["static", "urban", "highway", "custom", "heartbeat"])
        self.interval = QtWidgets.QSpinBox()
        self.interval.setRange(1, 60)
        self.interval.setValue(5)
        self.duration = QtWidgets.QSpinBox()
        self.duration.setRange(0, 3600)
        self.duration.setValue(0)
        sim_layout.addRow("Escenario", self.scenario)
        sim_layout.addRow("Intervalo (s)", self.interval)
        sim_layout.addRow("Duración (s, 0=inf)", self.duration)
        left.addWidget(sim)

        # Control
        ctl = QtWidgets.QGroupBox("Controles")
        ctl_layout = QtWidgets.QGridLayout(ctl)
        self.btn_start_server = QtWidgets.QPushButton("Iniciar Servidor")
        self.btn_stop_server = QtWidgets.QPushButton("Detener Servidor")
        self.btn_start_client = QtWidgets.QPushButton("Iniciar Cliente")
        self.btn_stop_client = QtWidgets.QPushButton("Detener Cliente")
        self.btn_send_once = QtWidgets.QPushButton("Enviar 1 Mensaje")

        ctl_layout.addWidget(self.btn_start_server, 0, 0)
        ctl_layout.addWidget(self.btn_stop_server, 0, 1)
        ctl_layout.addWidget(self.btn_start_client, 1, 0)
        ctl_layout.addWidget(self.btn_stop_client, 1, 1)
        ctl_layout.addWidget(self.btn_send_once, 2, 0, 1, 2)
        left.addWidget(ctl)
        left.addStretch(1)

        # Stats
        stats = QtWidgets.QGroupBox("Estadísticas")
        stats_layout = QtWidgets.QGridLayout(stats)
        self.stat_sent = QtWidgets.QLabel("0")
        self.stat_ack = QtWidgets.QLabel("0")
        self.stat_lost = QtWidgets.QLabel("0")
        self.stat_success = QtWidgets.QLabel("100%")
        stats_layout.addWidget(QtWidgets.QLabel("Mensajes Enviados"), 0, 0)
        stats_layout.addWidget(self.stat_sent, 1, 0)
        stats_layout.addWidget(QtWidgets.QLabel("ACKs Recibidos"), 0, 1)
        stats_layout.addWidget(self.stat_ack, 1, 1)
        stats_layout.addWidget(QtWidgets.QLabel("Paquetes Perdidos"), 0, 2)
        stats_layout.addWidget(self.stat_lost, 1, 2)
        stats_layout.addWidget(QtWidgets.QLabel("Tasa de Éxito"), 0, 3)
        stats_layout.addWidget(self.stat_success, 1, 3)
        right.addWidget(stats)

        # Visual placeholder
        viz = QtWidgets.QFrame()
        viz.setObjectName("Viz")
        viz_layout = QtWidgets.QVBoxLayout(viz)
        viz_label = QtWidgets.QLabel("Área de visualización")
        viz_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        viz_layout.addWidget(viz_label, 1)
        right.addWidget(viz, 2)

        # Log
        log_box = QtWidgets.QGroupBox("Registro")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        log_layout.addWidget(self.log)
        right.addWidget(log_box, 1)

        # Signals
        self.btn_start_server.clicked.connect(self.start_server)
        self.btn_stop_server.clicked.connect(self.stop_server)
        self.btn_start_client.clicked.connect(self.start_client)
        self.btn_stop_client.clicked.connect(self.stop_client)
        self.btn_send_once.clicked.connect(self.send_once)

        self._log("UI lista. Inicia el servidor y el cliente.")

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { font-family: 'Segoe UI'; font-size: 12px; }
            #Header {
                background: #0b3c49;
                color: white;
                padding: 10px;
                font-size: 18px;
                font-weight: 600;
            }
            QGroupBox {
                border: 1px solid #d0d4da;
                border-radius: 8px;
                margin-top: 10px;
                padding: 8px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px 0 4px;
            }
            #Viz {
                border: 1px solid #d0d4da;
                border-radius: 8px;
                background: #f8fafc;
            }
            #TopTabs {
                background: #eef2f7;
            }
            """
        )

    def _log(self, msg: str) -> None:
        self.log.append(msg)

    def _client_args(self, once: bool) -> list:
        args = [sys.executable, os.path.join("src", "gps_cliente.py")]
        args += ["--mode", self.scenario.currentText()]
        args += ["--interval", str(self.interval.value())]
        args += ["--duration", str(self.duration.value())]
        args += ["--speed", str(self.speed.value())]
        args += ["--heading", str(self.heading.value())]
        args += ["--lat", str(self.lat.value())]
        args += ["--lon", str(self.lon.value())]
        args += ["--battery", str(self.battery.value())]
        args += ["--id", str(self.device_id.value())]
        args += ["--port", str(self.server_port.value())]
        if once:
            args += ["--once", "true"]
        return args

    def start_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            self._log("Servidor ya está en ejecución.")
            return
        try:
            self.server_proc = subprocess.Popen(
                [
                    sys.executable,
                    os.path.join("src", "gps_servidor.py"),
                    str(self.server_port.value()),
                ]
            )
            self._log("Servidor iniciado.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo iniciar servidor: {e}")

    def stop_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            self.server_proc.terminate()
            self._log("Servidor detenido.")
        else:
            self._log("Servidor no está en ejecución.")

    def start_client(self) -> None:
        if self.client_proc and self.client_proc.poll() is None:
            self._log("Cliente ya está en ejecución.")
            return
        try:
            self.client_proc = subprocess.Popen(self._client_args(once=False))
            self._log("Cliente iniciado.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo iniciar cliente: {e}")

    def stop_client(self) -> None:
        if self.client_proc and self.client_proc.poll() is None:
            self.client_proc.terminate()
            self._log("Cliente detenido.")
        else:
            self._log("Cliente no está en ejecución.")

    def send_once(self) -> None:
        try:
            subprocess.Popen(self._client_args(once=True))
            self._log("Mensaje único enviado.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo enviar mensaje: {e}")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    ui = GPSUI()
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
