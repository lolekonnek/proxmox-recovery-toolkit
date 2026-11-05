import json
import unittest
from unittest.mock import patch

from proxmox_recovery.commands import CommandResult
from proxmox_recovery.discovery import detect_candidates


class DiscoveryTests(unittest.TestCase):
    @patch("proxmox_recovery.discovery.run_readonly")
    def test_detects_pve_lvm_without_claiming_system_verification(self, run):
        lvs = {"report": [{"lv": [{"vg_name": "pve", "lv_name": "root", "lv_size": "96g"}]}]}
        pvs = {"report": [{"pv": [{"pv_name": "/dev/sda3", "vg_name": "pve", "pv_size": "120g"}]}]}
        run.side_effect = [
            CommandResult(("lsblk",), 0, json.dumps({"blockdevices": []}), ""),
            CommandResult(("lvs",), 0, json.dumps(lvs), ""),
            CommandResult(("pvs",), 0, json.dumps(pvs), ""),
            CommandResult(("zpool",), 1, "", "no pools available"),
        ]

        report = detect_candidates()

        self.assertIn("VG=pve, LV=root", report)
        self.assertIn("nie potwierdzonymi", report)
        self.assertEqual(run.call_args_list[1].args[0][1], "--readonly")
        self.assertEqual(run.call_args_list[2].args[0][1], "--readonly")

    @patch("proxmox_recovery.discovery.run_readonly")
    def test_reports_zfs_candidates_without_importing_them(self, run):
        empty = json.dumps({"report": []})
        run.side_effect = [
            CommandResult(("lsblk",), 0, json.dumps({"blockdevices": []}), ""),
            CommandResult(("lvs",), 0, empty, ""),
            CommandResult(("pvs",), 0, empty, ""),
            CommandResult(("zpool",), 0, "pool: rpool\n state: ONLINE", ""),
        ]

        report = detect_candidates()

        self.assertIn("pule ZFS", report)
        self.assertIn("nie zaimportowano", report)
        self.assertEqual(run.call_args_list[3].args[0], ["zpool", "import", "-d", "/dev"])

    @patch("proxmox_recovery.discovery.run_readonly")
    def test_lists_ext4_as_unverified_candidate(self, run):
        empty = json.dumps({"report": []})
        devices = {
            "blockdevices": [
                {"path": "/dev/sda", "fstype": None, "children": [
                    {"path": "/dev/sda2", "fstype": "ext4", "label": "rootfs"}
                ]}
            ]
        }
        run.side_effect = [
            CommandResult(("lsblk",), 0, json.dumps(devices), ""),
            CommandResult(("lvs",), 0, empty, ""),
            CommandResult(("pvs",), 0, empty, ""),
            CommandResult(("zpool",), 1, "", "no pools available"),
        ]

        report = detect_candidates()

        self.assertIn("/dev/sda2", report)
        self.assertIn("niezweryfikowany kandydat", report)


if __name__ == "__main__":
    unittest.main()
