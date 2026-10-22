import json
from pathlib import Path

import pytest

from src.collecte.rss import parser

FIXTURE = Path(__file__).parent / "fixtures" / "humanite.xml"
RECUPERE_LE = "2026-10-20T12:10:00+00:00"


def items_humanite():
    return parser(FIXTURE.read_bytes(), "L'Humanité", RECUPERE_LE)


def test_parser_lit_tous_les_items():
    assert len(items_humanite()) == 20


def test_parser_produit_le_format_articles_bruts():
    premier = items_humanite()[0]
    assert set(premier) == {
        "id",
        "source",
        "lien",
        "titre",
        "resume",
        "publie_le",
        "recupere_le",
        "rubrique",
        "payload",
    }
    assert len(premier["id"]) == 16
    assert premier["source"] == "L'Humanité"
    assert premier["titre"].startswith("“Pillages”, “casse”")
    assert premier["lien"].startswith("https://www.humanite.fr/")
    assert premier["publie_le"] == "2026-10-20T12:01:36+00:00"
    assert premier["recupere_le"] == RECUPERE_LE
    assert premier["resume"].startswith("Chaque journée de mobilisation")
    assert premier["rubrique"] == "Société"


def test_payload_sans_texte_integral_images_ni_auteur():
    for item in items_humanite():
        payload = item["payload"]
        assert "content" not in payload
        assert "author" not in payload and "authors" not in payload
        assert not any(cle.startswith("media_") for cle in payload)
        assert all(lien.get("rel") != "enclosure" for lien in payload.get("links", []))
        json.dumps(payload)  # sérialisable tel quel


def test_parser_retire_le_html_de_l_extrait():
    flux = b"""<rss version="2.0"><channel><item>
        <title>Titre</title><link>https://exemple.fr/a</link>
        <description>&lt;p&gt;Un &lt;b&gt;extrait&lt;/b&gt;&lt;/p&gt;</description>
    </item></channel></rss>"""
    assert parser(flux, "test")[0]["resume"] == "Un extrait"


def test_parser_lit_aussi_atom():
    flux = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <title>Titre Atom</title><link href="https://exemple.fr/atom"/>
        <id>tag:exemple.fr,2026:1</id><updated>2026-10-20T08:00:00+02:00</updated>
        <summary>Extrait Atom</summary>
    </entry></feed>"""
    (item,) = parser(flux, "test")
    assert item["lien"] == "https://exemple.fr/atom"
    assert item["resume"] == "Extrait Atom"
    assert item["publie_le"] == "2026-10-20T06:00:00+00:00"


def test_parser_refuse_un_flux_illisible():
    with pytest.raises(ValueError):
        parser(b"<html>pas un flux</html", "test")
