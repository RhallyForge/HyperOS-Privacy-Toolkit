import unittest

from hyperos_privacy_toolkit.models import DeviceInfo
from hyperos_privacy_toolkit.profiles import (
    action_by_id,
    default_profiles_dir,
    load_profiles,
    select_profile,
)


def device(**overrides):
    values = {
        "model": "23049PCD8G",
        "device": "marble",
        "android": "15",
        "miui": "V816",
        "hyperos": "OS3.0.4.0.VMRMIXM",
        "build": "example",
        "region": "IT",
        "locale": "it-IT",
        "current_user": "0",
        "transport": "wireless",
    }
    values.update(overrides)
    return DeviceInfo(**values)


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_profiles(default_profiles_dir())

    def test_verified_profile_selected_only_for_exact_tested_target(self):
        profile = select_profile(self.profiles, device())
        self.assertEqual("poco-f5-marble-hyperos3-global-it", profile["id"])

    def test_unsupported_device_falls_back_to_read_only(self):
        profile = select_profile(
            self.profiles,
            device(model="other", device="other", locale="en-US", region="US"),
        )
        self.assertEqual("generic-xiaomi-read-only", profile["id"])
        self.assertEqual([], profile["actions"])

    def test_msa_requires_server_data_deletion_acknowledgement(self):
        profile = select_profile(self.profiles, device())
        action = action_by_id(profile, "msa-authorization-revocation")
        self.assertEqual("server-data-deletion", action["risk"])
        self.assertEqual("manual", action["restore_mode"])

    def test_action_ids_are_unique(self):
        for profile in self.profiles:
            ids = [action["id"] for action in profile.get("actions", [])]
            self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
