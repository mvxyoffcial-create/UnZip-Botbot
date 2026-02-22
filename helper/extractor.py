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
        import rarfile
        return True
    except ImportError:
        return False


def _7z_available() -> bool:
    return shutil.which("7z") is not None


def extract_archive(archive_path: str, dest_dir: str) -> list:
    """
    Extract archive_path into dest_dir.
    Returns sorted list of extracted absolute file paths.
    """
    os.makedirs(dest_dir, exist_ok=True)
    archive_path = os.path.abspath(archive_path)
    dest_dir = os.path.abspath(dest_dir)
    ext = archive_path.lower()

    try:
        if ext.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest_dir)

        elif ext.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar")):
            with tarfile.open(archive_path) as tf:
                tf.extractall(dest_dir, filter='data')

        elif ext.endswith(".rar"):
            if _rar_available():
                import rarfile
                with rarfile.RarFile(archive_path) as rf:
                    rf.extractall(dest_dir)
            elif _7z_available():
                result = subprocess.run(
                    ["7z", "x", archive_path, f"-o{dest_dir}", "-y"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                raise RuntimeError("RAR support unavailable. Install rarfile or 7z.")

        elif ext.endswith(".7z"):
            if _7z_available():
                result = subprocess.run(
                    ["7z", "x", archive_path, f"-o{dest_dir}", "-y"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                raise RuntimeError("7z binary not found. Install p7zip-full.")

        else:
            # Try 7z as fallback
            if _7z_available():
                result = subprocess.run(
                    ["7z", "x", archive_path, f"-o{dest_dir}", "-y"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                raise RuntimeError(f"Unsupported archive format: {archive_path}")

    except subprocess.CalledProcessError as e:
        log.exception(f"7z extraction failed: {e.stderr}")
        raise RuntimeError(f"Extraction failed: {e.stderr}")
    except Exception as e:
        log.exception(f"Extraction failed: {e}")
        raise

    # Fast file collection using Path.rglob()
    extracted = [str(p) for p in sorted(Path(dest_dir).rglob("*")) if p.is_file()]
    return extracted


def is_archive(filename: str) -> bool:
    exts = (".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tgz",
            ".tar.bz2", ".tar.xz", ".gz", ".bz2", ".xz")
    name = filename.lower()
    return any(name.endswith(e) for e in exts)
