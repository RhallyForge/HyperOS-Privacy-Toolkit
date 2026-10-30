import unittest

from hyperos_privacy_toolkit.adb import (
    AdbError,
    enabled_state_name,
    parse_devices,
    parse_enabled_code,
    select_device,
)


class AdbParsingTests(unittest.TestCase):
    def test_parse_usb_and_wireless(self):
        output = """List of devices attached
ABC123 device product:marble_global model:23049PCD8G device:marble transport_id:1
192.0.2.10:5555 device product:marble_global model:23049PCD8G device:marble transport_id:2
"""
        devices = parse_devices(output)
        self.assertEqual(2, len(devices))
        self.assertEqual("usb", devices[0].transport)
        self.assertEqual("wireless", devices[1].transport)

    def test_same_phone_multiple_transports_prefers_usb(self):
        devices = parse_devices(
            """List of devices attached
ABC123 device product:marble_global model:23049PCD8G device:marble transport_id:1
adb-example._adb-tls-connect._tcp device product:marble_global model:23049PCD8G device:marble transport_id:2
"""
        )
        self.assertEqual("ABC123", select_device(devices).serial)

    def test_distinct_devices_require_explicit_serial(self):
        devices = parse_devices(
            """List of devices attached
A device product:one model:One device:one
B device product:two model:Two device:two
"""
        )
        with self.assertRaises(AdbError):
            select_device(devices)

    def test_package_enabled_codes(self):
        dump = "User 0: installed=true enabled=0 stopped=false"
        self.assertEqual(0, parse_enabled_code(dump))
        self.assertEqual("DEFAULT", enabled_state_name(0))
        self.assertEqual("DISABLED_USER", enabled_state_name(3))


if __name__ == "__main__":
    unittest.main()
