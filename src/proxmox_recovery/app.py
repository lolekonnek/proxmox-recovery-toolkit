from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from . import diagnostics, discovery


LOGGER = logging.getLogger("proxmox_recovery")
LOG_PATH = Path("/var/log/proxmox-recovery-toolkit.log")
RECOVERY_GUIDANCE = """Ta wersja narzędzia nie resetuje haseł i nie modyfikuje
systemów na dyskach.

Dla własnego serwera użyj autoryzowanej konsoli fizycznej lub zdalnej,
procedury odzyskiwania zatwierdzonej przez administratora oraz oficjalnej
dokumentacji Proxmox VE:
https://pve.proxmox.com/pve-docs/

Przed działaniami zmieniającymi uwierzytelnianie potwierdź właściciela
systemu, tożsamość instalacji, dostępność kopii zapasowej oraz wpływ na
klaster i usługi. Zmiany wykonuj ręcznie zgodnie z polityką administratora."""


def configure_logging() -> None:
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    LOGGER.info("Uruchomiono Proxmox Recovery Toolkit")


def _whiptail(
    arguments: list[str], title: str = "Proxmox Recovery Toolkit"
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["whiptail", "--title", title, *arguments],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Brak programu whiptail w środowisku Live.") from error


def show_text(title: str, text: str) -> None:
    LOGGER.info("Wyświetlam raport: %s", title)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as report:
        report.write(text)
        report_path = report.name
    try:
        result = _whiptail(
            ["--textbox", report_path, "22", "78", "--scrolltext"], title
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(f"whiptail nie wyświetlił raportu (kod {result.returncode}).")
    finally:
        Path(report_path).unlink(missing_ok=True)


def _menu() -> str | None:
    options = [
        ("1", "Wykryj instalacje Proxmox"),
        ("2", "Diagnostyka dysków i partycji"),
        ("3", "Informacje o konfiguracji LVM"),
        ("4", "Diagnostyka ZFS (bez importu pul)"),
        ("5", "Odzyskiwanie dostępu - procedura administratora"),
        ("6", "Wyświetl logi"),
        ("7", "Wyłącz komputer"),
    ]
    arguments = ["--menu", "Wybierz działanie diagnostyczne:", "20", "82", "8"]
    for tag, label in options:
        arguments.extend((tag, label))
    arguments.extend(("--default-item", "1", "--output-fd", "1"))
    result = _whiptail(arguments)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise RuntimeError(f"Nie udało się wyświetlić menu (kod {result.returncode}).")
    return result.stdout.strip()


def _poweroff() -> None:
    result = _whiptail(
        ["--yesno", "Czy na pewno wyłączyć komputer?", "8", "56"]
    )
    if result.returncode != 0:
        return
    LOGGER.warning("Użytkownik potwierdził wyłączenie komputera")
    try:
        completed = subprocess.run(["systemctl", "poweroff"], check=False)
    except OSError as error:
        LOGGER.exception("Nie udało się wyłączyć komputera")
        show_text("Błąd", f"Nie udało się wyłączyć komputera: {error}")
        return
    if completed.returncode != 0:
        LOGGER.error("systemctl poweroff zakończył się kodem %d", completed.returncode)
        show_text("Błąd", f"Polecenie wyłączenia zakończyło się kodem {completed.returncode}.")


def main() -> None:
    if os.geteuid() != 0:
        print("Uruchom program z uprawnieniami administratora: sudo proxmox-recovery-toolkit")
        raise SystemExit(1)
    configure_logging()
    actions = {
        "1": ("Wykrywanie instalacji", discovery.detect_candidates),
        "2": ("Diagnostyka dysków i partycji", diagnostics.disk_report),
        "3": ("Diagnostyka LVM", diagnostics.lvm_report),
        "4": ("Diagnostyka ZFS", diagnostics.zfs_report),
        "5": ("Odzyskiwanie dostępu", lambda: RECOVERY_GUIDANCE),
        "6": ("Dziennik działań", lambda: LOG_PATH.read_text(encoding="utf-8")),
    }

    while True:
        selected = _menu()
        if selected is None:
            LOGGER.info("Użytkownik zakończył pracę z menu")
            return
        if selected == "7":
            _poweroff()
            return
        action = actions.get(selected)
        if action is None:
            LOGGER.error("Nieznana opcja menu: %s", selected)
            show_text("Błąd", f"Nieznana opcja menu: {selected}")
            continue
        title, callback = action
        try:
            show_text(title, callback())
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            LOGGER.exception("Niepowodzenie podczas: %s", title)
            show_text("Błąd diagnostyki", str(error))
