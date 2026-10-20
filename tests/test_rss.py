import json
from pathlib import Path

from src.collecte.rss import ecrire_json, parser

FIXTURE = Path(__file__).parent / "fixtures" / "humanite.xml"


def items_humanite():
    return parser(FIXTURE.read_bytes(), "humanite")


def test_parser_lit_tous_les_items():
    assert len(items_humanite()) == 9999


def test_parser_extrait_les_champs_attendus():
    premier = items_humanite()[0]
    assert premier["source"] == "humanite"
    assert premier["titre"].startswith("“Pillages”, “casse”")
    assert premier["lien"].startswith("https://www.humanite.fr/")
    assert premier["date_publication"] == "2026-10-20T12:01:36+00:00"
    assert premier["extrait"].startswith("Chaque journée de mobilisation")


def test_parser_ne_garde_ni_auteur_ni_contenu_integral():
    for item in items_humanite():
        assert set(item) == {
            "source",
            "guid",
            "titre",
            "extrait",
            "lien",
            "date_publication",
        }


def test_parser_retire_le_html_de_l_extrait():
    flux = b"""<rss version="2.0"><channel><item>
        <title>Titre</title><link>https://exemple.fr/a</link>
        <description>&lt;p&gt;Un &lt;b&gt;extrait&lt;/b&gt;&lt;/p&gt;</description>
    </item></channel></rss>"""
    assert parser(flux, "test")[0]["extrait"] == "Un extrait"


def test_parser_ignore_un_flux_invalide():
    assert parser(b"pas du xml", "test") == []


def test_ecrire_json(tmp_path):
    items = items_humanite()
    chemin = ecrire_json(items, "humanite", "https://www.humanite.fr/feed", tmp_path)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    assert document["source"] == "humanite"
    assert document["nb_items"] == 20
    assert document["items"] == items
