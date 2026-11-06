from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Sequence


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run_readonly(command: Sequence[str], timeout: int = 30) -> CommandResult:
    """Run a diagnostic command without a shell and preserve failures."""
    args = tuple(command)
    if not args:
        raise ValueError("Nie można uruchomić pustego polecenia.")
    if shutil.which(args[0]) is None:
        raise FileNotFoundError(f"Brak wymaganego polecenia: {args[0]}")

    LOGGER.info("Uruchamiam polecenie diagnostyczne: %s", " ".join(args))
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        LOGGER.error("Przekroczono limit czasu polecenia: %s", " ".join(args))
        raise TimeoutError(
            f"Przekroczono limit {timeout} s dla: {' '.join(args)}"
        ) from error
    except OSError as error:
        LOGGER.exception("Nie udało się uruchomić: %s", " ".join(args))
        raise RuntimeError(f"Nie udało się uruchomić {args[0]}: {error}") from error

    result = CommandResult(
        command=args,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )
    if result.returncode == 0:
        LOGGER.info("Polecenie zakończone powodzeniem: %s", args[0])
    else:
        LOGGER.warning(
            "Polecenie %s zakończone kodem %d: %s",
            args[0],
            result.returncode,
            result.stderr,
        )
    return result

def run_system_command(
    command: Sequence[str],
    timeout: int = 30,
) -> CommandResult:
    """
    Uruchamia kontrolowane polecenie systemowe.

    Nie korzysta z powłoki systemowej.
    Nie zapewnia automatycznej autoryzacji operacji.
    """

    args = tuple(command)

    if not args:
        raise ValueError("Nie można uruchomić pustego polecenia.")

    if any(not isinstance(arg, str) or "\x00" in arg for arg in args):
        raise ValueError("Nieprawidłowy argument polecenia.")

    if timeout <= 0:
        raise ValueError("Limit czasu musi być większy od zera.")

    if shutil.which(args[0]) is None:
        raise FileNotFoundError(
            f"Brak wymaganego polecenia: {args[0]}"
        )

    LOGGER.info(
        "Uruchamiam kontrolowane polecenie systemowe: %s",
        args[0],
    )

    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

    except subprocess.TimeoutExpired as error:
        LOGGER.error(
            "Przekroczono limit czasu polecenia: %s",
            args[0],
        )
        raise TimeoutError(
            f"Przekroczono limit {timeout} s dla: {args[0]}"
        ) from error

    except OSError as error:
        LOGGER.exception(
            "Nie udało się uruchomić polecenia: %s",
            args[0],
        )
        raise RuntimeError(
            f"Nie udało się uruchomić {args[0]}: {error}"
        ) from error

    result = CommandResult(
        command=args,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )

    if result.returncode == 0:
        LOGGER.info(
            "Polecenie systemowe zakończone powodzeniem: %s",
            args[0],
        )
    else:
        LOGGER.warning(
            "Polecenie %s zakończone kodem %d: %s",
            args[0],
            result.returncode,
            result.stderr,
        )

    return result

def render_result(result: CommandResult) -> str:
    output = result.stdout or "(brak danych na standardowym wyjściu)"
    if result.returncode != 0:
        detail = result.stderr or "(brak szczegółów błędu)"
        return f"{output}\n\nBŁĄD (kod {result.returncode}):\n{detail}"
    if result.stderr:
        return f"{output}\n\nKomunikaty:\n{result.stderr}"
    return output
