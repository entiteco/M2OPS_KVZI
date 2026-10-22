"""Contrôles de dates. Les dates sont en UTC (normalisées au TD 3)."""

from datetime import datetime, timedelta

# Tolérance entre l'heure de publication annoncée par l'éditeur et l'heure
# de collecte : les horloges ne sont pas toujours à l'heure.
TOLERANCE_FUTUR = timedelta(hours=1)


def est_dans_le_futur(publie_le: str | None, recupere_le: str) -> bool:
    """Vrai si la date de publication dépasse l'heure de collecte, tolérance comprise."""
    if publie_le is None:
        return False
    publication = datetime.fromisoformat(publie_le)
    collecte = datetime.fromisoformat(recupere_le)
    return publication - collecte > TOLERANCE_FUTUR
