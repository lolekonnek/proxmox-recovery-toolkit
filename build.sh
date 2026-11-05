#!/bin/sh
set -eu

cd "$(dirname "$0")"

if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' "Uruchom skrypt jako root: sudo $0" >&2
    exit 1
fi

for command in lb; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Brak wymaganego polecenia: %s\n' "$command" >&2
        exit 1
    fi
done

mkdir -p config/includes.chroot/usr/local/lib/python3/dist-packages/proxmox_recovery
cp -a src/proxmox_recovery/. config/includes.chroot/usr/local/lib/python3/dist-packages/proxmox_recovery/

sh ./auto/config
lb build

image="live-image-amd64.hybrid.iso"
if [ ! -f "$image" ]; then
    printf 'Nie znaleziono oczekiwanego obrazu: %s\n' "$image" >&2
    exit 1
fi
install -m 0644 "$image" proxmox-recovery-toolkit-amd64.iso
printf 'Utworzono: %s/proxmox-recovery-toolkit-amd64.iso\n' "$PWD"
