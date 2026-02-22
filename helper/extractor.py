"""
Archive extraction helper.
Supports: ZIP, RAR, 7Z, TAR, TAR.GZ, TAR.BZ2, TAR.XZ
"""
import os
import zipfile
import tarfile
import shutil
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def _rar_available() -> bool:
    try:
        import rarfile  # noqa: F401
        return (
            shutil.which("unrar") is not None
            or shutil.which("bsdtar") is not None
        )
    except ImportError:
        return False


def _7z_available() -> bool:
    return shutil.which("7z") is not None


def _safe_zip_extract(zf: zipfile.ZipFile, dest_dir: str) -> None:
    """Extract ZIP while blocking path traversal (zip slip)."""
    dest_dir = os.path.realpath(dest_dir)
    for member in zf.infolist():
        target = os.path.realpath(os.path.join(dest_dir, member.filename))
        if not target.startswith(dest_dir + os.sep):
            raise RuntimeError(
                f"Path traversal attempt blocked: {member.filename}"
            )
        zf.extract(member, dest_dir)


def _run_7z(archive_path: str, dest_dir: str) -> None:
    """Run 7z extraction, raising RuntimeError on failure."""
    try:
        subprocess.run(
            ["7z", "x", archive_path, f"-o{dest_dir}", "-y"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"7z extraction failed: {e.stderr.strip()}") from e


def extract_archive(archive_path: str, dest_dir: str) -> list:
    """
    Extract archive_path into dest_dir.
    Returns sorted list of extracted absolute file paths.

    Raises:
        FileNotFoundError: If archive_path does not exist.
        RuntimeError: If the format is unsupported or extraction fails.
    """
    archive_path = os.path.abspath(archive_path)
    dest_dir = os.path.abspath(dest_dir)

    # Fail early with a clear message instead of a cryptic OS error.
    if not os.path.isfile(archive_path):
        raise FileNotFoundError(
            f"Archive not found: {archive_path}"
        )

    os.makedirs(dest_dir, exist_ok=True)

    # Derive extension from the filename only, not the full path.
    name = Path(archive_path).name.lower()

    try:
        if name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                _safe_zip_extract(zf, dest_dir)

        elif any(name.endswith(e) for e in
                 (".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar")):
            with tarfile.open(archive_path) as tf:
                tf.extractall(dest_dir, filter="data")

        elif name.endswith(".rar"):
            if _rar_available():
                import rarfile
                with rarfile.RarFile(archive_path) as rf:
                    rf.extractall(dest_dir)
            elif _7z_available():
                _run_7z(archive_path, dest_dir)
            else:
                raise RuntimeError(
                    "RAR support unavailable. "
                    "Install 'rarfile' + unrar/bsdtar, or p7zip-full."
                )

        elif name.endswith(".7z"):
            if _7z_available():
                _run_7z(archive_path, dest_dir)
            else:
                raise RuntimeError(
                    "7z binary not found. Install p7zip-full."
                )

        elif any(name.endswith(e) for e in (".gz", ".bz2", ".xz")):
            # Bare compressed files (not tar). Decompress with 7z if available.
            if _7z_available():
                _run_7z(archive_path, dest_dir)
            else:
                raise RuntimeError(
                    f"Unsupported compressed format '{name}'. "
                    "Install p7zip-full for .gz/.bz2/.xz support."
                )

        else:
            # Unknown extension — attempt 7z as a last resort.
            if _7z_available():
                log.warning(
                    "Unrecognised extension for '%s', attempting 7z fallback.",
                    name,
                )
                _run_7z(archive_path, dest_dir)
            else:
                raise RuntimeError(
                    f"Unsupported archive format: {archive_path}"
                )

    except (FileNotFoundError, RuntimeError):
        raise
    except Exception as e:
        log.exception("Extraction failed for '%s': %s", archive_path, e)
        raise RuntimeError(f"Extraction failed: {e}") from e

    extracted = [
        str(p)
        for p in sorted(Path(dest_dir).rglob("*"))
        if p.is_file()
    ]
    return extracted


def is_archive(filename: str) -> bool:
    """Return True if filename has a recognised archive extension."""
    exts = (
        ".zip", ".rar", ".7z",
        ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz",
        ".gz", ".bz2", ".xz",
    )
    name = Path(filename).name.lower()
    return any(name.endswith(e) for e in exts)
