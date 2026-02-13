import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import gps_protocolo  # noqa: E402


class TestProtocolo(unittest.TestCase):
    def test_checksum_valido(self):
        msg = gps_protocolo.empaquetar_mensaje_gps(
            id_dispositivo=1234,
            secuencia=1,
            latitud=100,
            longitud=200,
            altitud=10,
            velocidad=50,
            rumbo=100,
            bateria=90,
            estado=0,
            flags=0,
        )
        self.assertTrue(gps_protocolo.verificar_checksum(msg))

    def test_checksum_invalido(self):
        msg = gps_protocolo.empaquetar_mensaje_gps(
            id_dispositivo=1234,
            secuencia=1,
            latitud=100,
            longitud=200,
            altitud=10,
            velocidad=50,
            rumbo=100,
            bateria=90,
            estado=0,
            flags=0,
        )
        corrupto = bytearray(msg)
        corrupto[10] ^= 0xFF
        self.assertFalse(gps_protocolo.verificar_checksum(bytes(corrupto)))

    def test_empaquetar_desempaquetar_gps(self):
        msg = gps_protocolo.empaquetar_mensaje_gps(
            id_dispositivo=4321,
            secuencia=42,
            latitud=-173935000,
            longitud=-661570000,
            altitud=2558,
            velocidad=450,
            rumbo=1350,
            bateria=85,
            estado=0,
            flags=gps_protocolo.FLAG_EN_MOVIMIENTO,
        )
        datos, error = gps_protocolo.desempaquetar_mensaje(msg)
        self.assertIsNotNone(datos, msg=error)
        assert datos is not None
        self.assertEqual(datos["id_dispositivo"], 4321)
        self.assertEqual(datos["secuencia"], 42)
        self.assertEqual(datos["latitud"], -173935000)
        self.assertEqual(datos["longitud"], -661570000)
        self.assertEqual(datos["altitud"], 2558)

    def test_empaquetar_ack(self):
        ack = gps_protocolo.empaquetar_ack(1234, 99)
        datos, error = gps_protocolo.desempaquetar_mensaje(ack)
        self.assertIsNotNone(datos, msg=error)
        assert datos is not None
        self.assertEqual(datos["tipo"], gps_protocolo.TIPO_ACK)
        self.assertEqual(datos["secuencia"], 99)

    def test_empaquetar_heartbeat(self):
        hb = gps_protocolo.empaquetar_heartbeat(1234, 7, flags=0x01)
        datos, error = gps_protocolo.desempaquetar_mensaje(hb)
        self.assertIsNotNone(datos, msg=error)
        assert datos is not None
        self.assertEqual(datos["tipo"], gps_protocolo.TIPO_HEARTBEAT)
        self.assertEqual(datos["secuencia"], 7)
        self.assertEqual(datos["flags"], 0x01)


if __name__ == "__main__":
    unittest.main()
