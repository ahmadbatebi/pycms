"""
ChelCheleh - Auto-Update Module
Handles checking and applying updates from GitHub repository.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable

import httpx

# GitHub repository configuration
REPO_OWNER = "ahmadbatebi"
REPO_NAME = "pycms"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GITHUB_ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/main.zip"

# Directories/files to preserve during update (user data)
PRESERVE_PATHS = [
    "data",
    "uploads",
    ".env",
    "backups",
]

# Request timeout in seconds
REQUEST_TIMEOUT = 30.0


class UpdateError(Exception):
    """Custom exception for update-related errors."""
    pass


async def check_for_updates(current_commit: str | None) -> dict:
    """
    Check GitHub for available updates.

    Args:
        current_commit: The currently installed commit hash, or None if unknown.

    Returns:
        Dictionary with update information:
        {
            "update_available": bool,
            "latest_commit": str,
            "commit_date": str,
            "commit_message": str,
            "current_commit": str | None,
            "error": str | None
        }
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Get the latest commit from main branch
            response = await client.get(
                f"{GITHUB_API_URL}/commits/main",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ChelCheleh-CMS-Updater",
                },
            )

            if response.status_code == 404:
                return {
                    "update_available": False,
                    "latest_commit": None,
                    "commit_date": None,
                    "commit_message": None,
                    "current_commit": current_commit,
                    "error": "Repository not found",
                }

            if response.status_code == 403:
                # Rate limit exceeded
                return {
                    "update_available": False,
                    "latest_commit": None,
                    "commit_date": None,
                    "commit_message": None,
                    "current_commit": current_commit,
                    "error": "GitHub API rate limit exceeded. Please try again later.",
                }

            response.raise_for_status()
            data = response.json()

            latest_commit = data["sha"]
            commit_date = data["commit"]["committer"]["date"]
            commit_message = data["commit"]["message"].split("\n")[0]  # First line only

            # Check if update is available
            update_available = current_commit is None or current_commit != latest_commit

            return {
                "update_available": update_available,
                "latest_commit": latest_commit,
                "commit_date": commit_date,
                "commit_message": commit_message,
                "current_commit": current_commit,
                "error": None,
            }

    except httpx.TimeoutException:
        return {
            "update_available": False,
            "latest_commit": None,
            "commit_date": None,
            "commit_message": None,
            "current_commit": current_commit,
            "error": "Connection timeout. Please check your internet connection.",
        }
    except httpx.HTTPError as e:
        return {
            "update_available": False,
            "latest_commit": None,
            "commit_date": None,
            "commit_message": None,
            "current_commit": current_commit,
            "error": f"HTTP error: {str(e)}",
        }
    except Exception as e:
        return {
            "update_available": False,
            "latest_commit": None,
            "commit_date": None,
            "commit_message": None,
            "current_commit": current_commit,
            "error": f"Unexpected error: {str(e)}",
        }


async def download_and_apply_update(
    base_path: Path,
    backup_callback: Callable[[], str] | None = None,
) -> dict:
    """
    Download and apply the latest update from GitHub.

    Args:
        base_path: The base installation path of the CMS.
        backup_callback: Optional callback function to create a backup before update.
                        Should return the backup file path.

    Returns:
        Dictionary with update result:
        {
            "success": bool,
            "new_commit": str | None,
            "backup_path": str | None,
            "error": str | None
        }
    """
    backup_path = None
    temp_dir = None

    try:
        # Step 1: Create backup if callback provided
        if backup_callback:
            try:
                backup_path = backup_callback()
            except Exception as e:
                return {
                    "success": False,
                    "new_commit": None,
                    "backup_path": None,
                    "error": f"Backup failed: {str(e)}",
                }

        # Step 2: Get latest commit hash
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            commit_response = await client.get(
                f"{GITHUB_API_URL}/commits/main",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ChelCheleh-CMS-Updater",
                },
            )
            commit_response.raise_for_status()
            new_commit = commit_response.json()["sha"]

        # Step 3: Download ZIP file
        temp_dir = Path(tempfile.mkdtemp(prefix="chelcheleh_update_"))
        zip_path = temp_dir / "update.zip"

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(
                GITHUB_ZIP_URL,
                headers={"User-Agent": "ChelCheleh-CMS-Updater"},
            )
            response.raise_for_status()

            zip_path.write_bytes(response.content)

        # Step 4: Extract ZIP file
        extract_dir = temp_dir / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find the extracted directory (usually named {repo}-{branch})
        extracted_contents = list(extract_dir.iterdir())
        if not extracted_contents:
            raise UpdateError("Empty update archive")

        source_dir = extracted_contents[0]
        if not source_dir.is_dir():
            raise UpdateError("Invalid update archive structure")

        # Step 5: Apply update (copy files, preserving user data)
        await _apply_update_files(source_dir, base_path)

        return {
            "success": True,
            "new_commit": new_commit,
            "backup_path": backup_path,
            "error": None,
        }

    except httpx.TimeoutException:
        return {
            "success": False,
            "new_commit": None,
            "backup_path": backup_path,
            "error": "Download timeout. Please check your internet connection.",
        }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "new_commit": None,
            "backup_path": backup_path,
            "error": f"Download failed: {str(e)}",
        }
    except UpdateError as e:
        return {
            "success": False,
            "new_commit": None,
            "backup_path": backup_path,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "new_commit": None,
            "backup_path": backup_path,
            "error": f"Update failed: {str(e)}",
        }
    finally:
        # Cleanup temp directory
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


async def _apply_update_files(source_dir: Path, target_dir: Path) -> None:
    """
    Copy update files from source to target, preserving user data directories.

    Args:
        source_dir: The directory containing new files.
        target_dir: The installation directory to update.
    """
    # Run file operations in executor to not block event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_apply_update_files, source_dir, target_dir)


def _sync_apply_update_files(source_dir: Path, target_dir: Path) -> None:
    """
    Synchronous implementation of file update logic.
    """
    for item in source_dir.iterdir():
        target_item = target_dir / item.name

        # Skip preserved paths
        if item.name in PRESERVE_PATHS:
            continue

        if item.is_dir():
            # Remove existing directory and copy new one
            if target_item.exists():
                shutil.rmtree(target_item)
            shutil.copytree(item, target_item)
        else:
            # Copy file
            shutil.copy2(item, target_item)


def get_cms_version() -> str:
    """Get the current CMS version string."""
    return "0.1.0"


def format_commit_date(iso_date: str) -> str:
    """
    Format ISO date string to a more readable format.

    Args:
        iso_date: ISO 8601 format date string (e.g., "2026-01-05T10:30:00Z")

    Returns:
        Formatted date string (e.g., "2026-01-05 10:30")
    """
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_date
