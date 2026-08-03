"""
===============================================================================
 Dealbot — controle op het lezen van digitale folders

 Versie      : 1.0
 Reden       : De folderlezer laat een AI naar drukwerk kijken. Wat de AI
               teruggeeft is nooit helemaal voorspelbaar, dus het rekenwerk en
               de controles eromheen moeten waterdicht zijn: een verkeerd
               gedeelde prijs zet een aanbieding twee keer zo duur in de lijst.
 Datum       : 03-08-2026 00:45

 Onderdelen:
   test_stuksprijs()     - "1+1 gratis" wordt de prijs voor één stuk
   test_bedragen()       - nul, niets en onzin leveren geen prijs op
   test_artikel()        - wat er van één afgelezen artikel overblijft
   test_periode()        - de datums: alleen echte, en de meerderheid wint
   test_vomar_week()     - de folderweek van Vomar loopt zondag t/m zaterdag
   test_folder_zoeken()  - geen folder of geen PDF is een nette melding
   test_soort_fout()     - 503 is drukte, "per day" is de dagvoorraad
   test_sleutels()       - de sleutels worden op volgorde uit .env gehaald

 Uitvoeren:
   python scripts/tests/test_folderlezer.py
===============================================================================
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot import ai, folderlezer  # noqa: E402
from dealbot.bronnen import vomar_folder  # noqa: E402


def _artikel(**rest):
    """Eén artikel zoals de AI het aanlevert."""
    artikel = {
        "product_naam": "Pirulo Waterijs",
        "merk": "Pirulo",
        "inhoud": "pak 5 stuks",
        "normale_prijs": 7.58,
        "actie_bedrag": 3.79,
        "bedrag_geldt_voor_aantal": 2,
        "actie_tekst": "1+1 gratis",
        "alleen_met_app": False,
    }
    artikel.update(rest)
    return artikel


def test_stuksprijs():
    """Bij "1+1 gratis" geldt het bedrag voor twee stuks; dat moet gedeeld worden."""
    assert folderlezer._stuksprijs(3.79, 2) == 1.895
    assert folderlezer._stuksprijs(5.00, 2) == 2.50
    assert folderlezer._stuksprijs(3.99, 1) == 3.99

    # Geen of onbruikbaar aantal: dan is één stuks de veilige aanname.
    assert folderlezer._stuksprijs(3.99, None) == 3.99
    assert folderlezer._stuksprijs(3.99, "twee") == 3.99
    assert folderlezer._stuksprijs(3.99, 0) == 3.99

    # Een absurd aantal is een leesfout en mag de prijs niet wegdelen.
    assert folderlezer._stuksprijs(3.99, 500) == 3.99

    assert folderlezer._stuksprijs(None, 2) is None

    print("  stuksprijs bij meerstuks-acties: goed")


def test_bedragen():
    """Nul is geen prijs, en onzin ook niet."""
    assert folderlezer._bedrag(0) is None
    assert folderlezer._bedrag(-1) is None
    assert folderlezer._bedrag(None) is None
    assert folderlezer._bedrag("gratis") is None
    assert folderlezer._bedrag("2.49") == 2.49
    assert folderlezer._bedrag(2.4949999) == 2.495

    print("  bedragen: goed")


def test_artikel():
    """Van één afgelezen artikel naar een aanbieding met een kloppende kiloprijs."""
    def maak(**rest):
        return folderlezer._naar_aanbieding(
            _artikel(**rest), winkel_id=5, pagina=1, folder_url=None, voorvoegsel="folder-32"
        )

    ijs = maak()
    assert ijs.prijs == 1.895, ijs.prijs          # 3,79 voor twee pakken
    assert ijs.normale_prijs == 7.58
    assert ijs.eenheid_norm == "stuk"
    assert ijs.bron_id.startswith("folder-32-p1-"), ijs.bron_id

    # Hetzelfde artikel levert dezelfde sleutel op; twee keer ophalen mag geen
    # dubbele lijst geven.
    assert maak().bron_id == ijs.bron_id

    # Zonder naam of zonder enig bedrag valt er niets te vergelijken.
    assert maak(product_naam="") is None
    assert maak(product_naam="   ") is None
    assert maak(actie_bedrag=0, normale_prijs=0) is None

    # Alleen een normale prijs is genoeg om mee te doen; de actietekst wordt dan
    # over die prijs uitgerekend ("1+1 gratis" is de helft).
    kaal = maak(actie_bedrag=0)
    assert kaal is not None and kaal.prijs == 3.79, kaal.prijs
    gewoon = maak(actie_bedrag=0, actie_tekst="per pak")
    assert gewoon.prijs == 7.58, gewoon.prijs

    # Dat een korting alleen via de app geldt, hoort de gebruiker te zien.
    app = maak(alleen_met_app=True)
    assert "alleen met de app" in app.actie_tekst, app.actie_tekst
    zonder_tekst = maak(alleen_met_app=True, actie_tekst="")
    assert zonder_tekst.actie_tekst == "alleen met de app"

    # De kiloprijs komt uit de inhoud zoals die in de folder stond.
    koek = maak(inhoud="pak 500 gram", actie_bedrag=2.0, bedrag_geldt_voor_aantal=1)
    assert koek.prijs_per_eenheid == 4.0, koek.prijs_per_eenheid
    assert koek.eenheid_norm == "kg"

    # Staat er geen leesbare inhoud, dan geen verzonnen kiloprijs.
    vaag = maak(inhoud="alle soorten")
    assert vaag.prijs_per_eenheid is None

    print("  artikel naar aanbieding: goed")


def test_periode():
    """Alleen echte datums tellen, en de periode van de meeste pagina's wint."""
    assert folderlezer._datum("2026-08-02") == "2026-08-02"
    assert folderlezer._datum("2026-08-02T00:00:00") == "2026-08-02"
    assert folderlezer._datum("zondag 2 augustus") is None
    assert folderlezer._datum("2026-13-45") is None
    assert folderlezer._datum("") is None
    assert folderlezer._datum(None) is None

    stemmen = Counter({("2026-08-02", "2026-08-08"): 9, ("2026-09-02", "2026-09-08"): 1})
    assert folderlezer._periode(stemmen) == ("2026-08-02", "2026-08-08")
    assert folderlezer._periode(Counter()) == (None, None)

    print("  geldigheidsperiode: goed")


def test_vomar_week():
    """De folderweek van Vomar begint op zondag, een dag vóór de kalenderweek."""
    # Week 32 van 2026: kalenderweek begint maandag 3 augustus, de folder liep
    # van zondag 2 tot en met zaterdag 8 augustus (afgelezen van de omslag).
    assert vomar_folder._periode(32, 2026) == ("2026-08-02", "2026-08-08")
    assert vomar_folder._periode(1, 2026) == ("2025-12-28", "2026-01-03")

    # Een onmogelijk weeknummer mag geen fout geven maar een bruikbare week.
    van, tot = vomar_folder._periode(99, 2026)
    assert van < tot

    print("  folderweek van Vomar: goed")


def test_folder_zoeken():
    """Geen folder of een veranderde folderdienst is een melding, geen crash."""
    class _Antwoord:
        def __init__(self, code, tekst=""):
            self.status_code = code
            self.ok = code < 400
            self.text = tekst
            self.url = "https://view.publitas.com/folder-deze-week/week-32/"

    origineel = vomar_folder.requests.get
    try:
        # Vomar heeft nog geen folder voor volgende week klaarstaan.
        vomar_folder.requests.get = lambda *_, **__: _Antwoord(404)
        try:
            vomar_folder.zoek_folder("volgende-week")
        except vomar_folder.FolderFout as fout:
            assert "geen folder" in str(fout), fout
        else:
            raise AssertionError("een ontbrekende folder hoort gemeld te worden")

        # De pagina is er wel, maar er staat geen PDF meer op.
        vomar_folder.requests.get = lambda *_, **__: _Antwoord(200, "<html>niets</html>")
        try:
            vomar_folder.zoek_folder()
        except vomar_folder.FolderFout as fout:
            assert "PDF" in str(fout), fout
        else:
            raise AssertionError("een pagina zonder PDF hoort gemeld te worden")

        # En zo hoort het wél: titel, weeknummer en de link naar het bestand.
        pagina = ('<title>Folder deze week Extern - Online weekfolder week 32 - Pagina 1</title>'
                  '{"downloadPdfUrl":"https://view.publitas.com/1/2/pdfs/abc.pdf?x=1"}')
        vomar_folder.requests.get = lambda *_, **__: _Antwoord(200, pagina)
        folder = vomar_folder.zoek_folder()
        assert folder.week == 32, folder.week
        assert folder.pdf_url.endswith("abc.pdf?x=1"), folder.pdf_url
        assert "Pagina 1" not in folder.titel, folder.titel
    finally:
        vomar_folder.requests.get = origineel

    # Een folder die we niet kennen vragen levert meteen een duidelijke melding.
    try:
        vomar_folder.zoek_folder("vorige-week")
    except vomar_folder.FolderFout as fout:
        assert "Onbekende folder" in str(fout), fout
    else:
        raise AssertionError("een onbekende folder hoort gemeld te worden")

    print("  folder zoeken: goed")


def test_soort_fout():
    """Dezelfde foutcode, twee betekenissen: wachten of van sleutel wisselen."""
    druk = ("ServerError: 503 UNAVAILABLE. {'error': {'message': 'This model is currently "
            "experiencing high demand.', 'status': 'UNAVAILABLE'}}")
    assert ai._soort_fout(druk) == "hapering", ai._soort_fout(druk)

    per_minuut = ("429 RESOURCE_EXHAUSTED: quotaId: "
                  "GenerateRequestsPerMinutePerProjectPerModel-FreeTier, retryDelay: '23s'")
    per_dag = "429 RESOURCE_EXHAUSTED: quotaId: GenerateRequestsPerDayPerProjectPerModel"
    assert ai._soort_fout(per_minuut) == "tempo"
    assert ai._soort_fout(per_dag) == "quotum"
    assert ai._soort_fout("429 RESOURCE_EXHAUSTED") == "tempo"      # bij twijfel wachten

    leeg = "429 RESOURCE_EXHAUSTED. Your prepayment credits are depleted."
    assert ai._soort_fout(leeg) == "geen tegoed"

    oud = ("ClientError: 404 NOT_FOUND. 'This model models/gemini-2.5-flash is no longer "
           "available to new users'")
    assert ai._soort_fout(oud) == "geen toegang"

    assert ai._soort_fout("400 INVALID_ARGUMENT: de opdracht deugt niet") == "overig"

    # De rusttijd die Google zelf voorstelt wordt gevolgd, maar wel begrensd.
    assert ai._voorgestelde_rust(per_minuut) == 23.0
    assert ai._voorgestelde_rust("geen voorstel") == 0.0
    assert ai._voorgestelde_rust("retryDelay: '9999s'") == ai.MAX_WACHTEN

    print("  soorten storing: goed")


def test_sleutels():
    """De sleutels komen op volgorde uit .env, en stoppen bij het eerste gat."""
    bewaard = {naam: os.environ.pop(naam) for naam in list(os.environ)
               if naam.startswith("GEMINI_API_KEY")}
    try:
        assert ai.sleutels() == []

        # Zonder sleutel is er niets te vragen, en dat moet zo gezegd worden.
        leeg = ai.Vraagbaak()
        kan, reden = leeg.beschikbaar()
        assert not kan and ".env" in reden, reden

        os.environ["GEMINI_API_KEY"] = "een"
        os.environ["GEMINI_API_KEY_2"] = "twee"
        os.environ["GEMINI_API_KEY_4"] = "vier"          # gat: nummer 3 ontbreekt
        assert [naam for naam, _ in ai.sleutels()] == ["GEMINI_API_KEY", "GEMINI_API_KEY_2"]

        vraagbaak = ai.Vraagbaak()
        assert vraagbaak.beschikbaar()[0]

        # Raakt alles op, dan hoort de melding te zeggen wat eraan schort.
        vraagbaak._op = {0, 1}
        vraagbaak._zonder_tegoed = {0, 1}
        kan, reden = vraagbaak.beschikbaar()
        assert not kan and "tegoed" in reden, reden
    finally:
        for naam in list(os.environ):
            if naam.startswith("GEMINI_API_KEY"):
                del os.environ[naam]
        os.environ.update(bewaard)

    print("  sleutels uit .env: goed")


if __name__ == "__main__":
    test_stuksprijs()
    test_bedragen()
    test_artikel()
    test_periode()
    test_vomar_week()
    test_folder_zoeken()
    test_soort_fout()
    test_sleutels()
    print("Alle controles op het lezen van folders geslaagd.")
