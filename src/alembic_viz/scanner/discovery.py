"""Discovery utilities for finding Alembic configuration and versions directory."""

import os
from configparser import ConfigParser
from pathlib import Path
from typing import Optional, Tuple


def find_alembic_ini(start_path: Optional[str] = None) -> Optional[str]:
    """Find alembic.ini by searching upward from start_path or cwd.

    Args:
        start_path: Path to start searching from. Defaults to cwd.

    Returns:
        Absolute path to alembic.ini if found, None otherwise.
    """
    if start_path is None:
        start_path = os.getcwd()

    current = Path(start_path).resolve()

    # Search upward until we find alembic.ini or hit root
    while current != current.parent:
        alembic_ini = current / "alembic.ini"
        if alembic_ini.exists():
            return str(alembic_ini)
        current = current.parent

    return None


def parse_alembic_ini(ini_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse alembic.ini to extract script_location and version_locations.

    Args:
        ini_path: Path to alembic.ini file.

    Returns:
        Tuple of (script_location, version_locations).
        version_locations may be a colon-separated string for multiple locations.
    """
    config = ConfigParser()
    config.read(ini_path)

    if "alembic" not in config:
        return None, None

    alembic_section = config["alembic"]
    script_location = alembic_section.get("script_location", "alembic")
    version_locations = alembic_section.get("version_locations")

    return script_location, version_locations


def find_versions_directory(
    explicit_path: Optional[str] = None,
    alembic_ini_path: Optional[str] = None,
) -> str:
    """Find the Alembic versions directory.

    Resolution order:
    1. explicit_path if provided and exists
    2. Parse alembic_ini_path or find alembic.ini, extract version_locations
    3. Look for alembic/versions relative to alembic.ini location

    Args:
        explicit_path: Direct path to versions directory.
        alembic_ini_path: Path to alembic.ini file.

    Returns:
        Absolute path to versions directory.

    Raises:
        FileNotFoundError: If no versions directory can be found.
    """
    # 1. Explicit path takes priority
    if explicit_path:
        path = Path(explicit_path).resolve()
        if path.exists() and path.is_dir():
            return str(path)
        raise FileNotFoundError(
            f"Explicit versions directory not found: {explicit_path}"
        )

    # 2. Try to find alembic.ini
    ini_path = alembic_ini_path or find_alembic_ini()

    if ini_path:
        script_location, version_locations = parse_alembic_ini(ini_path)
        ini_dir = Path(ini_path).parent

        # Check version_locations first (may have multiple paths)
        if version_locations:
            # Take the first location if multiple
            first_location = version_locations.split(os.pathsep)[0].strip()
            # Handle relative paths
            if not first_location.startswith("/"):
                first_location = str(ini_dir / first_location)

            path = Path(first_location).resolve()
            if path.exists() and path.is_dir():
                return str(path)

        # Fall back to script_location/versions
        if script_location:
            if not script_location.startswith("/"):
                script_location = str(ini_dir / script_location)

            versions_path = Path(script_location) / "versions"
            if versions_path.exists() and versions_path.is_dir():
                return str(versions_path.resolve())

    raise FileNotFoundError(
        "Could not find Alembic versions directory. "
        "Provide explicit --directory or ensure alembic.ini is in current or parent directory."
    )
