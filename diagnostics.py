from __future__ import annotations

from .commands import render_result, run_readonly


def disk_report() -> str:
    sections = (
        ("Urządzenia blokowe i partycje (lsblk)", ["lsblk", "--json", "--bytes", "--output", "NAME,KNAME,PATH,TYPE,SIZE,FSTYPE,FSVER,LABEL,UUID,PARTUUID,RO,MOUNTPOINTS,MODEL,SERIAL"]),
        ("Sygnatury systemów plików (blkid)", ["blkid", "-o", "full"]),
    )
    output: list[str] = []
    for title, command in sections:
        result = run_readonly(command, timeout=60)
        output.append(f"=== {title} ===\n{render_result(result)}")
    return "\n\n".join(output)


def lvm_report() -> str:
    commands = (
        ("Woluminy fizyczne (tryb tylko do odczytu)", ["pvs", "--readonly", "--reportformat", "json"]),
        ("Grupy woluminów (tryb tylko do odczytu)", ["vgs", "--readonly", "--reportformat", "json"]),
        ("Woluminy logiczne (tryb tylko do odczytu)", ["lvs", "--readonly", "--reportformat", "json"]),
    )
    output = []
    for title, command in commands:
        result = run_readonly(command, timeout=60)
        output.append(f"=== {title} ===\n{render_result(result)}")
    return "\n\n".join(output)


def zfs_report() -> str:
    result = run_readonly(["zpool", "import", "-d", "/dev"], timeout=60)
    if result.returncode == 1 and "no pools available" in (
        result.stdout + result.stderr
    ).lower():
        return "Nie znaleziono pul ZFS dostępnych do importu. Żadna pula nie została zaimportowana."
    return (
        "Skan wykrywania pul ZFS (polecenie nie importuje puli):\n\n"
        + render_result(result)
    )
