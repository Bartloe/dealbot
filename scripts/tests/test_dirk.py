"""
===============================================================================
 Dealbot — controle op de indeling van Dirk van den Broek

 Versie      : 1.0
 Reden       : Dirk wordt voortaan ingedeeld in zijn 146 groepen ("Koffie &
               cacao") in plaats van in de zeventien grove afdelingen ("Dranken,
               sap, koffie & thee"). Daar hoort een controle bij, inclusief de
               terugvallen voor het geval Dirk die groep niet meelevert.
 Datum       : 02-08-2026 01:05

 Onderdelen:
   test_productgroep()     - de groep wint van de afdeling, met terugval
   test_webgroepen()       - de keuzelijst: ontdubbeld, opgeschoond, op volgorde
   test_webgroepen_stuk()  - gaat de vraag mis, dan een lege lijst en geen crash

 Uitvoeren:
   python scripts/tests/test_dirk.py
===============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.bronnen import dirk  # noqa: E402

AFDELINGEN = [{"id": 1, "naam": "Dranken, sap, koffie & thee"}, {"id": 2, "naam": "Diepvries"}]


def _actie(**rest):
    """Eén aanbieding zoals Dirk hem aanlevert, met alleen wat wij gebruiken."""
    actie = {
        "headerText": "Koffie",
        "packaging": "Pak 500 gram",
        "textPriceSign1": "ACTIE",
        "startDate": "2026-08-01T00:00:00.000Z",
        "endDate": "2026-08-07T00:00:00.000Z",
    }
    actie.update(rest)
    return actie


def _product(product_id, naam, **info):
    inhoud = {"headerText": naam, "brand": None, "packaging": "500 g",
              "department": "Dranken, sap, koffie & thee", "webgroup": "Koffie & cacao"}
    inhoud.update(info)
    return {"productId": product_id, "normalPrice": 8.0, "offerPrice": 5.0,
            "productInformation": inhoud}


class _NepSessie:
    """Staat in voor de verbinding; er mag in deze controles niets de deur uit."""

    def post(self, *_, **__):
        raise AssertionError("deze test hoort niet echt bij Dirk aan te kloppen")


def test_productgroep():
    """De groep onder de afdeling is de productgroep, niet de afdeling zelf."""
    koffie = dirk._naar_aanbieding(_product(1, "Douwe Egberts Koffiebonen espresso"), _actie())
    assert koffie.productgroep == "Koffie & cacao", koffie.productgroep

    # Levert Dirk geen groep mee, dan blijft de afdeling over.
    zonder = dirk._naar_aanbieding(_product(2, "Losse thee", webgroup=None), _actie())
    assert zonder.productgroep == "Dranken, sap, koffie & thee", zonder.productgroep

    # Een spatie aan het eind ("Afbakbrood ") mag niet als eigen groep tellen.
    slordig = dirk._naar_aanbieding(_product(3, "Stokbrood", webgroup="Afbakbrood "), _actie())
    assert slordig.productgroep == "Afbakbrood", repr(slordig.productgroep)

    # Ontbreekt allebei, dan blijft de groep leeg — dat mag, en de aanbieding blijft.
    kaal = dirk._naar_aanbieding(
        _product(4, "Onbekend", webgroup=None, department=None), _actie())
    assert kaal.productgroep is None
    assert kaal.product_naam == "Onbekend"

    print("  productgroep: goed")


def test_webgroepen():
    """De keuzelijst krijgt de groepen: ontdubbeld, opgeschoond en op volgorde."""
    antwoord = {"webGroups": [
        {"webGroups": [{"description": "Koffie & cacao"}, {"description": "Thee"}]},
        {"webGroups": [{"description": "Diepvries snacks"}, {"description": "Thee"},
                       {"description": "  "}, {"description": None}]},
        {"webGroups": None},
    ]}

    origineel = dirk._vraag
    dirk._vraag = lambda *_, **__: antwoord
    try:
        groepen = dirk._webgroepen(_NepSessie(), AFDELINGEN)
    finally:
        dirk._vraag = origineel

    assert groepen == ["Diepvries snacks", "Koffie & cacao", "Thee"], groepen

    print("  groepenlijst: goed")


def test_webgroepen_stuk():
    """Gaat het ophalen mis, dan een lege lijst — haal_op() valt dan terug."""
    origineel = dirk._vraag

    def stuk(*_, **__):
        raise dirk.DirkFout("Dirk gaf een foutmelding terug: kapot")

    dirk._vraag = stuk
    try:
        assert dirk._webgroepen(_NepSessie(), AFDELINGEN) == []
        # Zonder afdelingen wordt er niet eens gevraagd.
        assert dirk._webgroepen(_NepSessie(), []) == []
    finally:
        dirk._vraag = origineel

    print("  terugval bij een storing: goed")


if __name__ == "__main__":
    test_productgroep()
    test_webgroepen()
    test_webgroepen_stuk()
    print("Alle controles op de indeling van Dirk geslaagd.")
