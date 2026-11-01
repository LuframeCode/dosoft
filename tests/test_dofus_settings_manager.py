import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from dofus_settings_manager import DofusSettingsError, DofusSettingsManager


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class DofusDisplayRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.manager = DofusSettingsManager(root / "game", root / "data")
        self.manager.is_dofus_running = lambda: False
        self.game = self.manager.settings_root
        self.shared = self.game / "Shared" / "dofus.json"
        self.normal = {"presetName": "Affichage classique", "uid": 1, "positions": "saved-layout"}
        self.fight = {"presetName": "Combat a 8", "uid": 2, "positions": "saved-fight"}
        write_json(self.shared, {"uiScale": {"value": 1.25}, "unrelatedShared": {"value": "keep"}})
        write_json(self.game / "Shared" / "preset.json", {
            "savedPresets": {"value": [self.normal, self.fight]},
        })
        for name in ("1", "2"):
            account = self.game / "Accounts" / name
            write_json(account / "dofus.json", {
                "autoFocusApp": {"value": True}, "privateHistory": {"value": name},
            })
            write_json(account / "preset.json", {
                "currentPreset": {"value": self.normal},
                "currentFightPreset": {"value": self.fight},
                "fightPresetId": {"value": 2},
                "resetUIPositions": {"value": True},
            })
        (self.game / "version").write_text("3.7.12", encoding="utf-8")

    def test_capture_empty_shared_preserves_previous_global_profile(self):
        self.manager.capture_master_profile()
        previous = self.manager.profile_path.read_bytes()
        self.shared.write_bytes(b"")
        result = self.manager.capture_master_profile()
        profile = json.loads(self.manager.profile_path.read_bytes())
        self.assertEqual(profile["shared_entries"]["uiScale"]["value"], 1.25)
        self.assertTrue(result["warnings"])
        self.assertEqual(self.shared.read_bytes(), b"")
        former = list(self.manager.profile_dir.glob("JEU CLASSIQUE-*.json"))
        self.assertEqual(len(former), 1)
        self.assertEqual(former[0].read_bytes(), previous)

    def test_first_capture_with_empty_shared_keeps_account_layout(self):
        self.shared.write_bytes(b"")
        result = self.manager.capture_master_profile()
        self.assertEqual(result["shared"], 0)
        profile = json.loads(self.manager.profile_path.read_bytes())
        self.assertEqual(profile["normal_preset"]["positions"], "saved-layout")

    def test_backup_quarantines_invalid_original_and_remains_restorable(self):
        self.shared.write_bytes(b"")
        backup = self.manager.create_backup()
        with zipfile.ZipFile(backup) as archive:
            manifest = json.loads(archive.read("DOSOFT-MANIFEST.json"))
            self.assertNotIn("Shared/dofus.json", manifest["files"])
            self.assertIn("Shared/dofus.json", manifest["quarantined_files"])
            self.assertEqual(archive.read("DOSOFT-QUARANTINE/Shared/dofus.json"), b"")
        _, files = self.manager._validated_archive(backup)
        self.assertIn("Accounts/1/preset.json", files)
        self.assertNotIn("Shared/dofus.json", files)
        self.assertTrue(self.manager.backup_warning(backup))

    def test_apply_repairs_empty_shared_and_disables_position_reset(self):
        self.manager.capture_master_profile()
        self.shared.write_bytes(b"")
        character = self.game / "Accounts" / "1" / "Characters" / "99" / "dofus.json"
        write_json(character, {"doNotTouch": 42})
        result = self.manager.apply_master_profile()
        self.assertEqual(result["accounts"], 2)
        self.assertEqual(json.loads(self.shared.read_bytes())["uiScale"]["value"], 1.25)
        for account in ("1", "2"):
            parent = self.game / "Accounts" / account
            self.assertFalse(json.loads((parent / "preset.json").read_bytes())["resetUIPositions"]["value"])
            self.assertEqual(json.loads((parent / "dofus.json").read_bytes())["privateHistory"]["value"], account)
        self.assertEqual(json.loads(character.read_bytes()), {"doNotTouch": 42})
        self.assertTrue(self.manager.backup_warning(result["rollback"]))

    def test_all_accounts_preflight_before_any_live_write(self):
        self.manager.capture_master_profile()
        self.shared.write_bytes(b"")
        broken = self.game / "Accounts" / "2" / "preset.json"
        broken.write_bytes(b"{truncated")
        before = {p: p.read_bytes() for p in self.manager._settings_files()}
        with patch("dofus_settings_manager.time.sleep"), self.assertRaises(DofusSettingsError):
            self.manager.apply_master_profile()
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_failed_write_rolls_back_exact_original_bytes(self):
        self.manager.capture_master_profile()
        self.shared.write_bytes(b"")
        before = {p: p.read_bytes() for p in self.manager._settings_files()}
        original_write = self.manager._write_bytes_atomic
        calls = 0

        def failing_write(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise PermissionError("simulated lock")
            return original_write(path, data)

        with patch.object(self.manager, "_write_bytes_atomic", side_effect=failing_write):
            with self.assertRaises(PermissionError):
                self.manager.apply_master_profile()
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertTrue(self.manager.latest_backup().exists())

    def test_restore_good_backup_when_current_shared_is_empty(self):
        backup = self.manager.create_backup()
        self.shared.write_bytes(b"")
        write_json(self.game / "Accounts" / "1" / "dofus.json", {"autoFocusApp": {"value": False}})
        result = self.manager.restore_latest_backup()
        self.assertEqual(result["archive"], backup)
        self.assertEqual(json.loads(self.shared.read_bytes())["uiScale"]["value"], 1.25)
        account = self.game / "Accounts" / "1"
        self.assertTrue(json.loads((account / "dofus.json").read_bytes())["autoFocusApp"]["value"])
        self.assertFalse(json.loads((account / "preset.json").read_bytes())["resetUIPositions"]["value"])
        self.assertEqual((self.game / "version").read_text(), "3.7.12")

    def test_nonempty_malformed_shared_is_not_treated_as_optional(self):
        self.shared.write_bytes(b"{broken")
        with patch("dofus_settings_manager.time.sleep"), self.assertRaises(DofusSettingsError):
            self.manager.capture_master_profile()
        self.assertFalse(self.manager.profile_path.exists())

    def test_running_client_blocks_operations(self):
        self.manager.is_dofus_running = lambda: True
        with self.assertRaises(DofusSettingsError):
            self.manager.create_backup()
        self.assertFalse(self.manager.backup_dir.exists())


if __name__ == "__main__":
    unittest.main()
