"""Alembic configuration functions."""

import os
from configparser import ConfigParser
from pathlib import Path
from typing import Optional, Tuple


def find_alembic_ini(start_path: str | None = None) -> str | None:
    """Find alembic.ini by searching upward from start_path or cwd."""
    if start_path is None:
        start_path = os.getcwd()
    current = Path(start_path).resolve()
    while current != current.parent:
        alembic_ini = current / "alembic.ini"
        if alembic_ini.exists():
            return str(alembic_ini)
        current = current.parent
    return None


def parse_alembic_ini(ini_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse alembic.ini to extract script_location and version_locations."""
    config = ConfigParser()
    config.read(ini_path)
    if "alembic" not in config:
        return None, None
    alembic_section = config["alembic"]
    script_location = alembic_section.get("script_location", "alembic")
    version_locations = alembic_section.get("version_locations")
    return script_location, version_locations


def resolve_migrations_root(config_path: str | None = None) -> str:
    """Resolve the Alembic migrations directory path.

    Resolution order:
    1. Parse config_path if provided
    2. Find alembic.ini and extract version_locations
    3. Fall back to script_location/versions

    Args:
        config_path: Path to alembic.ini. If None, will search for it.

    Returns:
        Absolute path to migrations directory.

    Raises:
        FileNotFoundError: If no migrations directory can be found.
    """
    ini_path = config_path or find_alembic_ini()

    if ini_path:
        script_location, version_locations = parse_alembic_ini(ini_path)
        ini_dir = Path(ini_path).parent

        # Check version_locations first
        if version_locations:
            first_location = version_locations.split(os.pathsep)[0].strip()
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
        "Could not find Alembic migrations directory. "
        "Provide explicit path or ensure alembic.ini is discoverable."
    )
