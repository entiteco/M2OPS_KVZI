"""Applique les migrations Alembic de la base gazette.

Usage : python -m src.stockage.migrer   (utilise GAZETTE_DB_URL)
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

DOSSIER_MIGRATIONS = Path(__file__).parent / "migrations"


def migrer(url: str | None = None) -> None:
    config = Config()
    config.set_main_option("script_location", str(DOSSIER_MIGRATIONS))
    config.set_main_option("sqlalchemy.url", url or os.environ["GAZETTE_DB_URL"])
    command.upgrade(config, "head")


if __name__ == "__main__":
    migrer()
    print("Base gazette à jour")
