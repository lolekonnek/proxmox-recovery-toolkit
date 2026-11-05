from __future__ import annotations

import json
import logging

from .commands import run_readonly


LOGGER = logging.getLogger(__name__)


def _json_report(command: list[str], report_name: str) -> list[dict[str, object]]:
    result = run_readonly(command)
    if result.returncode != 0:
        raise RuntimeError(
            f"{report_name}: polecenie zakończyło się kodem {result.returncode}: "
            f"{result.stderr or 'brak szczegółów'}"
        )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        LOGGER.exception("Niepoprawny raport JSON z %s", report_name)
        raise RuntimeError(f"{report_name}: polecenie zwróciło niepoprawny JSON.") from error
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{report_name}: nieoczekiwany format raportu.")
    reports = parsed.get("report", [])
    if not isinstance(reports, list):
        raise RuntimeError(f"{report_name}: nieoczekiwany format raportu.")
    rows: list[dict[str, object]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        for key in ("pv", "vg", "lv"):
            values = report.get(key, [])
            if isinstance(values, list):
                rows.extend(row for row in values if isinstance(row, dict))
    return rows


def detect_candidates() -> str:
    """Report likely PVE storage signatures; this does not verify an OS install."""
    devices_result = run_readonly(
        ["lsblk", "--json", "--output", "PATH,FSTYPE,LABEL,TYPE"]
    )
    if devices_result.returncode != 0:
        raise RuntimeError(
            "Skan urządzeń: polecenie zakończyło się kodem "
            f"{devices_result.returncode}: {devices_result.stderr or 'brak szczegółów'}"
        )
    try:
        devices = json.loads(devices_result.stdout)
    except json.JSONDecodeError as error:
        LOGGER.exception("Niepoprawny raport lsblk")
        raise RuntimeError("Skan urządzeń: polecenie zwróciło niepoprawny JSON.") from error
    if not isinstance(devices, dict):
        raise RuntimeError("Skan urządzeń: nieoczekiwany format raportu.")

    candidates: list[str] = []

    def find_ext4(rows: object) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("fstype", "")).lower() == "ext4":
                path = str(row.get("path", "?"))
                label = str(row.get("label") or "brak etykiety")
                candidates.append(
                    f"- System plików ext4 (niezweryfikowany kandydat): {path}, etykieta={label}"
                )
            find_ext4(row.get("children"))

    find_ext4(devices.get("blockdevices"))

    lvs = _json_report(
        ["lvs", "--readonly", "--reportformat", "json", "-o", "vg_name,lv_name,lv_size"],
        "LVM",
    )
    pvs = _json_report(
        ["pvs", "--readonly", "--reportformat", "json", "-o", "pv_name,vg_name,pv_size"],
        "LVM",
    )

    for row in lvs:
        vg = str(row.get("vg_name", "")).strip()
        lv = str(row.get("lv_name", "")).strip()
        size = str(row.get("lv_size", "")).strip()
        if vg == "pve" or lv == "root":
            candidates.append(f"- Kandydat LVM: VG={vg or '?'}, LV={lv or '?'}, rozmiar={size or '?'}")
    for row in pvs:
        vg = str(row.get("vg_name", "")).strip()
        pv = str(row.get("pv_name", "")).strip()
        if vg == "pve":
            candidates.append(f"- Wolumin fizyczny grupy pve: {pv or '?'}")

    try:
        zpool = run_readonly(["zpool", "import", "-d", "/dev"], timeout=60)
    except (OSError, RuntimeError, TimeoutError) as error:
        candidates.append(
            "Błąd sondowania ZFS (nie jest to wynik negatywny):\n" f"{error}"
        )
    else:
        zpool_text = zpool.stdout
        if zpool.returncode == 0 and zpool_text:
            candidates.append(
                "- Wykryto pulę/pule ZFS możliwe do importu (nie zaimportowano):\n"
                + zpool_text
            )
        elif zpool.returncode != 0 and "no pools available" not in (
            zpool.stdout + zpool.stderr
        ).lower():
            candidates.append(
                "Błąd sondowania ZFS (nie jest to wynik negatywny):\n"
                f"{zpool.stderr or zpool.stdout or f'kod {zpool.returncode}'}"
            )

    if not candidates:
        return (
            "Nie znaleziono sygnatur typowych dla magazynu PVE (VG pve, LV root "
            "ani puli ZFS dostępnej do importu).\n\n"
            "To nie wyklucza instalacji Proxmox VE. Sprawdź raporty diagnostyczne."
        )
    return (
        "Wyniki są kandydatami na magazyn instalacji, a nie potwierdzonymi "
        "systemami Proxmox VE. Nie montowano ani nie zmieniano dysków.\n\n"
        + "\n".join(candidates)
    )
