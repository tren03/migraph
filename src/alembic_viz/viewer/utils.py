"""Utility functions for the viewer."""

from pathlib import Path


def get_template_path(filename: str) -> Path:
    """Get the path to a template file.

    Args:
        filename: Name of the template file (e.g., 'index.html')

    Returns:
        Absolute path to the template file
    """
    return Path(__file__).parent / "templates" / filename


def load_template(filename: str) -> bytes:
    """Load a template file as bytes.

    Args:
        filename: Name of the template file (e.g., 'index.html')

    Returns:
        File contents as bytes

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = get_template_path(filename)
    return template_path.read_bytes()


def load_template_text(filename: str) -> str:
    """Load a template file as text.

    Args:
        filename: Name of the template file (e.g., 'index.html')

    Returns:
        File contents as string (UTF-8)

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = get_template_path(filename)
    return template_path.read_text(encoding="utf-8")
