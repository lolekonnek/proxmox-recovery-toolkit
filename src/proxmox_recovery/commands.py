from __future__ import annotations

import json
import os
import pty
import fcntl
import termios
import struct
import select
import subprocess
import logging
import sys
import tty
import termios as _termios

from pathlib import Path

from .commands import run_readonly, run_system_command
from .discovery import detect_candidates

LOGGER = logging.getLogger(__name__)

MOUNT_POINT = Path("/mnt")
ROOT_DEVICE = "/dev/pve/root"
VOLUME_GROUP = "pve"


# ==========================================
# DIAGNOSTYKA ODZYSKIWANIA
# ==========================================

def password_recovery_report() -> str:
    """Diagnostyka możliwości odzyskania dostępu."""

    output = [
        "PROXMOX PASSWORD RECOVERY",
        "=" * 40,
        "",
        "Tryb diagnostyczny – bez modyfikacji systemu.",
        "",
    ]

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

    output.extend([
        "",
        "INFORMACJE O ŚRODOWISKU:",
        f"Root systemu Live: {Path('/').resolve()}",
        "",
        "Dokumentacja: https://pve.proxmox.com/pve-docs/",
    ])

    return "\n".join(output)


# ==========================================
# PRZYGOTOWANIE MAGAZYNU
# ==========================================

def prepare_storage() -> str:
    """Sprawdza, czy wykryto potencjalne instalacje Proxmox."""

    LOGGER.info("Rozpoczęto diagnostykę pamięci masowej.")

    try:
        report = detect_candidates()
    except Exception:
        LOGGER.exception("Nie udało się wykryć instalacji.")
        return "Błąd podczas wykrywania instalacji."

    if not report.strip():
        return "Nie wykryto żadnych potencjalnych instalacji."

    return report


def activate_volume_group() -> str:
    """Aktywuje woluminy LVM (vgchange -ay)."""

    LOGGER.info("Aktywacja woluminów LVM grupy %s.", VOLUME_GROUP)

    try:
        result = run_system_command(["vgchange", "-ay", VOLUME_GROUP])

        if result.returncode != 0:
            return f"vgchange -ay {VOLUME_GROUP} zwróciło kod {result.returncode}: {result.stderr}"

        return f"vgchange -ay {VOLUME_GROUP}: OK"

    except (RuntimeError, TimeoutError, FileNotFoundError) as error:
        return f"Nie udało się aktywować LVM: {error}"


# ==========================================
# MONTOWANIE SYSTEMU
# ==========================================

def mount_system() -> str:
    """Montuje system Proxmox oraz wymagane systemy specjalne."""

    LOGGER.info("Rozpoczęto montowanie systemu Proxmox.")

    if not Path(ROOT_DEVICE).exists():
        return f"Nie znaleziono urządzenia: {ROOT_DEVICE}"

    try:
        MOUNT_POINT.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return f"Nie udało się utworzyć katalogu: {error}"

    # 1) montowanie głównego systemu
    try:
        result = run_system_command([
            "mount", "-o", "rw", ROOT_DEVICE, str(MOUNT_POINT)
        ])

        if result.returncode != 0:
            return f"Błąd montowania systemu: {result.stderr}"

    except (RuntimeError, TimeoutError, FileNotFoundError) as error:
        return f"Nie udało się zamontować systemu: {error}"

    # 2) bind-mount systemów specjalnych
    bind_mounts = ["/dev", "/proc", "/sys", "/run"]
    mounted = []

    for directory in bind_mounts:
        target = MOUNT_POINT / directory.lstrip("/")

        try:
            target.mkdir(parents=True, exist_ok=True)

            result = run_system_command([
                "mount", "--bind", directory, str(target)
            ])

            if result.returncode != 0:
                return (
                    f"System główny został zamontowany, "
                    f"ale nie udało się zamontować {directory}.\n"
                    f"Błąd: {result.stderr}\n"
                    f"Zamontowane wcześniej: {', '.join(mounted)}"
                )

            mounted.append(directory)

        except (RuntimeError, TimeoutError, FileNotFoundError, OSError) as error:
            return f"Błąd montowania {directory}: {error}"

    LOGGER.info("Zakończono montowanie systemu Proxmox.")

    return (
        "Montowanie zakończone.\n"
        f"System: {ROOT_DEVICE}\n"
        f"Punkt montowania: {MOUNT_POINT}\n"
        "Tryb: RW\n"
        "Zamontowane systemy specjalne:\n"
        + "\n".join(f"  - {directory}" for directory in mounted)
    )


def unmount_system() -> str:
    """Odmontowuje bind-mounty i system główny."""

    LOGGER.info("Odmontowywanie systemu Proxmox.")

    errors = []

    for directory in ["/run", "/sys", "/proc", "/dev"]:
        target = MOUNT_POINT / directory.lstrip("/")
        try:
            result = run_system_command(["umount", str(target)])
            if result.returncode != 0:
                errors.append(f"{target}: {result.stderr}")
        except Exception as error:
            errors.append(f"{target}: {error}")

    try:
        result = run_system_command(["umount", str(MOUNT_POINT)])
        if result.returncode != 0:
            errors.append(f"{MOUNT_POINT}: {result.stderr}")
    except Exception as error:
        errors.append(f"{MOUNT_POINT}: {error}")

    if errors:
        return "Odmontowanie zakończone z błędami:\n" + "\n".join(errors)

    return "System odmomontowany poprawnie."


# ==========================================
# CHROOT + passwd root
# ==========================================

def chroot_passwd_root() -> int:
    """
    Uruchamia chroot /mnt i interaktywnie wywołuje passwd root.
    Użytkownik wpisuje nowe hasło bezpośrednio w konsoli.
    """

    LOGGER.info("Uruchamianie chroot + passwd root.")

    master_fd, slave_fd = pty.openpty()

    try:
        process = subprocess.Popen(
            ["chroot", str(MOUNT_POINT), "/usr/bin/passwd", "root"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
        )
    finally:
        os.close(slave_fd)

    # Przekierowanie stdin/stdout użytkownika do PTY
    old_tty = None
    try:
        old_tty = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())
    except termios.error:
        old_tty = None

    try:
        while True:
            rlist, _, _ = select.select([master_fd, sys.stdin.fileno()], [], [], 0.1)

            if master_fd in rlist:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    data = b""
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)

            if sys.stdin.fileno() in rlist:
                try:
                    data = os.read(sys.stdin.fileno(), 1024)
                except OSError:
                    data = b""
                if data:
                    os.write(master_fd, data)

            if process.poll() is not None:
                # dokończ odczyt z PTY
                try:
                    while True:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        os.write(sys.stdout.fileno(), data)
                except OSError:
                    pass
                break
    finally:
        if old_tty is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_tty)
        try:
            os.close(master_fd)
        except OSError:
            pass

    return process.wait()


# ==========================================
# GŁÓWNY PROCES
# ==========================================

def recover_password() -> str:
    """Koordynuje cały proces zmiany hasła root w Proxmox."""

    lines = ["PROXMOX ROOT PASSWORD CHANGE", "=" * 40, ""]

    step = activate_volume_group()
    lines.append(f"[1] {step}")
    if "OK" not in step:
        return "\n".join(lines)

    step = mount_system()
    lines.append(f"[2] {step}")
    if "Montowanie zakończone" not in step:
        unmount_system()
        return "\n".join(lines)

    lines.append("[3] Uruchamiam chroot /mnt i passwd root — wpisz nowe hasło.")
    print("\n".join(lines))

    rc = chroot_passwd_root()

    if rc == 0:
        lines.append("[3] passwd root: OK")
    else:
        lines.append(f"[3] passwd root: kod {rc}")

    step = unmount_system()
    lines.append(f"[4] {step}")

    return "\n".join(lines)


# ==========================================
# SPRZĄTANIE
# ==========================================

def cleanup():
    """Kończy pracę programu i restartuje komputer."""

    LOGGER.info("Przygotowanie do restartu systemu.")

    input("Naciśnij Enter, aby ponownie uruchomić komputer...")

    try:
        result = subprocess.run(
            ["sudo", "systemctl", "reboot"],
            check=False
        )

        if result.returncode != 0:
            return f"Nie udało się zrestartować systemu: {result.returncode}"

        return "Wysłano żądanie restartu."

    except OSError as error:
        LOGGER.exception("Błąd restartowania systemu.")
        return f"Błąd: {error}"
