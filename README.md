# Proxmox Recovery Toolkit

Polskojęzyczne, uruchamiane z nośnika USB środowisko Debian Live do
diagnostyki dysków i wykrywania kandydatów na instalacje Proxmox VE.
Narzędzie nie montuje znalezionych systemów, nie importuje pul ZFS i nie
zmienia danych na dyskach użytkownika.

## Zakres i bezpieczeństwo

- Skanuje urządzenia blokowe, sygnatury systemów plików, metadane LVM oraz
  pule ZFS, których nie trzeba importować.
- Kandydatów opisuje jako **potencjalne** instalacje. Same sygnatury nie
  potwierdzają, że system jest instalacją Proxmox VE.
- Wszystkie polecenia diagnostyczne są uruchamiane bez opcji zapisujących.
  `pvs`, `vgs` i `lvs` dostają `--readonly`; `zpool import` służy wyłącznie
  do wyświetlenia pul dostępnych do importu i nie importuje żadnej z nich.
- Nie uruchamia `mount`, `chroot`, `vgchange`, `zpool import <nazwa>`,
  `passwd`, narzędzi formatowania ani narzędzi naprawczych.
- Dziennik działań jest zapisywany w pamięci środowiska Live pod
  `/var/log/proxmox-recovery-toolkit.log`, a nie na skanowanych dyskach.

Opcja „Odzyskiwanie dostępu” nie resetuje hasła. Przypomina o użyciu
autoryzowanej konsoli administracyjnej i oficjalnej dokumentacji Proxmox VE.
Operacje zmieniające uwierzytelnianie są celowo poza zakresem tego narzędzia.

## Budowanie obrazu ISO

Obraz jest systemem Debian Live, a jego konfiguracja korzysta z narzędzia
`live-build`, które jest pakietem Debiana. Bezpośrednie budowanie jest
przewidziane na Debianie lub Ubuntu z dostępem do repozytoriów Debiana.
Instrukcje poniżej nie zakładają, że można zainstalować `live-build` z
repozytoriów innych dystrybucji.

```sh
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso
sudo ./build.sh
```

### Budowanie z Arch Linux, CachyOS, Fedory i innych dystrybucji

Nie trzeba zmieniać systemu na komputerze. Uruchom Debiana w maszynie
wirtualnej (zalecane) albo na innym komputerze, skopiuj do niego cały katalog
projektu i wykonaj powyższe polecenia w Debianie. W Arch Linux/CachyOS pakiet
`live-build` może nie być dostępny w skonfigurowanych repozytoriach pacmana;
`squashfs-tools` i `libisoburn` (dostawca `xorriso`) nie zastępują
`live-build` ani `debootstrap`.

Możesz użyć dowolnego oprogramowania do wirtualizacji dostępnego dla swojej
dystrybucji. W maszynie wirtualnej z Debianem:

1. Zainstaluj Debiana z dostępem do Internetu i przydziel mu odpowiednią
   ilość miejsca na pobrane pakiety oraz obraz.
2. Skopiuj projekt do maszyny (np. przez współdzielony katalog lub SSH).
3. Zainstaluj zależności i uruchom `sudo ./build.sh` zgodnie z instrukcjami
   powyżej.
4. Skopiuj utworzony plik ISO z maszyny wirtualnej na host.

Budowanie bezpośrednio na innych dystrybucjach ani w kontenerze nie jest
obecnie przetestowane i nie jest wspierane przez ten projekt. Samo
zainstalowanie pakietów o podobnych nazwach z repozytorium danej dystrybucji
nie gwarantuje, że `live-build` będzie dostępny lub że obraz poprawnie się
zbuduje.

Wynikiem jest hybrydowy obraz `proxmox-recovery-toolkit-amd64.iso` w katalogu
głównym projektu. Konfiguracja obrazu obejmuje start BIOS/ISOLINUX oraz UEFI
przez GRUB EFI. Budowanie wymaga połączenia z Internetem, miejsca na pobrane
pakiety i uprawnień administratora.

## Tworzenie nośnika USB

Obraz należy zapisać na **właściwym urządzeniu USB**. Poniższe polecenie
bezpowrotnie nadpisuje wskazane urządzenie — sprawdź jego nazwę i rozmiar
przed użyciem:

```sh
lsblk
sudo dd if=proxmox-recovery-toolkit-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Zastąp `/dev/sdX` całym urządzeniem USB, nie partycją. Można też użyć
Rufus/Etcher; wybierz tryb obrazu DD, jeśli program o to zapyta.

## Użycie

Uruchom komputer z USB, wybierz Debian Live, a po załadowaniu środowiska
uruchom:

```sh
sudo proxmox-recovery-toolkit
```

Menu oferuje:

1. Wykrywanie kandydatów (systemy plików ext4, LVM, ZFS).
2. Diagnostykę dysków i partycji przez `lsblk` oraz `blkid`.
3. Raporty LVM w trybie `--readonly`.
4. Listę pul ZFS możliwych do wykrycia bez ich importowania.
5. Informacje o bezpiecznych, autoryzowanych ścieżkach odzyskiwania.
6. Dziennik działań bieżącej sesji.
7. Potwierdzone wyłączenie komputera.

Skanowanie nie wybiera ani nie modyfikuje dysku. Ponieważ narzędzie nie
montuje systemów plików, nie potwierdza zawartości `/etc/pve` ani nie może
gwarantować, że znalezione sygnatury należą do działającej instalacji PVE.

## Rozwój i testy

Kod aplikacji znajduje się w `src/proxmox_recovery/`. Do testów nie są
wymagane uprawnienia roota:

```sh
python3 -m unittest discover -s tests -v
```

ZFS jest dostarczany przez pakiety Debiana z sekcji `contrib`; moduł kernela
jest zależny od kernela obrazu Live i może być niedostępny w niektórych
konfiguracjach sprzętowych. Brak polecenia lub błąd sondowania jest
wyświetlany w raporcie i rejestrowany, nie zastępuje się go fikcyjnym wynikiem.
