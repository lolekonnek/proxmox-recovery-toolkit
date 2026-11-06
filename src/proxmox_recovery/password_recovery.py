from __future__ import annotations

import logging
from pathlib import Path

from .commands import run_readonly

LOGGER = logging.getLogger(__name__)


def password_recovery_report() -> str:
    """
    Diagnostyka możliwości odzyskania dostępu
    do wykrytej instalacji Proxmox VE.
    Nie zmienia haseł ani nie modyfikuje dysków.
    """

    output = [
        "PROXMOX PASSWORD RECOVERY",
        "=" * 40,
        "",
        "Tryb diagnostyczny – bez modyfikacji systemu.",
        "",
    ]

    # Sprawdzenie dostępności narzędzi
    commands = {
        "LVM": ["lvs", "--readonly", "--reportformat", "json"],
        "Dyski": ["lsblk", "--json", "--output", "NAME,PATH,FSTYPE,TYPE"],
    }

    for name, command in commands.items():
        try:
            result = run_readonly(command)
            if result.returncode == 0:
                output.append(f"[OK] {name}: dostępne")
            else:
                output.append(f"[BŁĄD] {name}: kod {result.returncode}")
        except (OSError, RuntimeError, TimeoutError) as error:
            LOGGER.exception("Błąd diagnostyki %s", name)
            output.append(f"[BŁĄD] {name}: {error}")

    # Sprawdzenie charakterystycznych plików lokalnego systemu
    output.extend([
        "",
        "INFORMACJE O ŚRODOWISKU:",
        f"Root systemu Live: {Path('/').resolve()}",
        "",
        "UWAGA:",
        "Ta wersja nie montuje systemów plików,",
        "nie wykonuje chroot i nie zmienia haseł.",
        "",
        "W przypadku własnej instalacji Proxmox VE",
        "skorzystaj z autoryzowanej procedury odzyskiwania",
        "dostępu administratora.",
        "",
        "Dokumentacja: https://pve.proxmox.com/pve-docs/",
    ])

    return "\n".join(output)