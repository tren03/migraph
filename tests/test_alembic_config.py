import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from migraph.repositories.alembic.config import resolve_migrations_root


class ResolveMigrationsRootTests(unittest.TestCase):
    def test_resolves_alembic_here_interpolation(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            versions = project / "migrations" / "versions"
            versions.mkdir(parents=True)
            config = project / "alembic.ini"
            config.write_text(
                "[alembic]\nscript_location = %(here)s/migrations\n",
                encoding="utf-8",
            )

            self.assertEqual(
                resolve_migrations_root(str(config)), str(versions.resolve())
            )


if __name__ == "__main__":
    unittest.main()
