import unittest

from hyperos_privacy_toolkit.safety import (
    SafetyError,
    assert_no_obvious_secret,
    opaque_device_reference,
    require_confirmation,
    require_data_deletion_acknowledgement,
)


class SafetyTests(unittest.TestCase):
    def test_exact_confirmation_is_required(self):
        with self.assertRaises(SafetyError):
            require_confirmation("security-recommendations", None)
        with self.assertRaises(SafetyError):
            require_confirmation("security-recommendations", "downloads-recommended-content")
        require_confirmation("security-recommendations", "security-recommendations")

    def test_msa_acknowledgement_is_required(self):
        with self.assertRaises(SafetyError):
            require_data_deletion_acknowledgement(False)
        require_data_deletion_acknowledgement(True)

    def test_device_reference_does_not_leak_serial(self):
        serial = "192.0.2.10:5555"
        reference = opaque_device_reference(serial)
        self.assertNotIn(serial, reference)
        self.assertTrue(reference.startswith("wireless-"))

    def test_publishable_content_scan(self):
        assert_no_obvious_secret("No device identifiers here")
        with self.assertRaises(SafetyError):
            assert_no_obvious_secret("endpoint 192.0.2.10:5555")


if __name__ == "__main__":
    unittest.main()
