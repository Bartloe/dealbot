"""
===============================================================================
 Dealbot — controle op het assortiment van Vomar

 Versie      : 1.0
 Reden       : Vomar is er als nieuwe bron bij gekomen, niet voor aanbiedingen
               maar voor de gewone winkelprijzen. Zijn gegevens zien er anders
               uit dan die van de andere ketens: de inhoud komt in twee losse
               velden en de productgroep zit verstopt achter drie nummers.
 Datum       : 02-08-2026 11:45

 Onderdelen:
   test_productgroep()   - de onderste laag wint, met de hoofdgroep als terugval
   test_inhoud()         - "1000" plus "gram" wordt een kiloprijs
   test_prijs()          - een prijs van nul telt niet als gratis
   test_dubbel()         - hetzelfde artikelnummer twee keer: laagste prijs wint
   test_webadres()       - de link naar vomar.nl, ook bij rare tekens
   test_indeling_leeg()  - geen indeling is een storing, geen stille lege lijst

 Uitvoeren:
   python scripts/tests/test_vomar.py
===============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.bronnen import vomar  # noqa: E402

# De drie lagen zoals Vomar ze aanlevert: afdeling, hoofdgroep, groep.
PADEN = {
    (30, 303, 15): ("Frisdrank, sappen, koffie & thee", "Koffie, Cacao en Thee", "Koffiebonen"),
    (30, 303, 99): ("Frisdrank, sappen, koffie & thee", "Koffie, Cacao en Thee", ""),
}


def _product(**rest):
    """Eén product zoals Vomar het aanlevert, met alleen wat wij gebruiken."""
    product = {
        "articleNumber": 109627,
        "description": "Douwe Egberts Espresso Bonen",
        "contents": "500",
        "unit": "gram",
        "price": 10.55,
        "brand": "Douwe Egberts",
        "primaryEan": "8711000324318",
        "departmentWebShopNumber": 30,
        "mainGroupWebShopNumber": 303,
        "subGroupWebShopNumber": 15,
        "images": [{"fileName": "product-images/abc.png", "imageType": "PackShot"}],
    }
    product.update(rest)
    return product


class _NepSessie:
    """Staat in voor de verbinding; er mag in deze controles niets de deur uit."""

    def get(self, *_, **__):
        raise AssertionError("deze test hoort niet echt bij Vomar aan te kloppen")


def test_productgroep():
    """De onderste laag is de productgroep; ontbreekt die, dan de hoofdgroep."""
    koffie = vomar._naar_standaardprijs(_product(), PADEN)
    assert koffie.productgroep == "Koffiebonen", koffie.productgroep
    assert koffie.afdeling == "Frisdrank, sappen, koffie & thee", koffie.afdeling

    # Kent Vomar de onderste laag niet, dan valt hij terug op de hoofdgroep.
    grof = vomar._naar_standaardprijs(_product(subGroupWebShopNumber=99), PADEN)
    assert grof.productgroep == "Koffie, Cacao en Thee", grof.productgroep

    # Staat het nummer helemaal niet in de indeling, dan blijft de groep leeg —
    # het product verdwijnt daarmee niet.
    onbekend = vomar._naar_standaardprijs(_product(departmentWebShopNumber=77), PADEN)
    assert onbekend.productgroep is None, onbekend.productgroep
    assert onbekend.product_naam == "Douwe Egberts Espresso Bonen"

    print("  productgroep: goed")


def test_inhoud():
    """Vomar levert hoeveelheid en eenheid apart; samen geven ze de kiloprijs."""
    bonen = vomar._naar_standaardprijs(_product(contents="500", unit="gram", price=10.0), PADEN)
    assert bonen.prijs_per_eenheid == 20.0, bonen.prijs_per_eenheid
    assert bonen.eenheid_norm == "kg", bonen.eenheid_norm

    fles = vomar._naar_standaardprijs(_product(contents="1500", unit="ml", price=3.0), PADEN)
    assert fles.prijs_per_eenheid == 2.0, fles.prijs_per_eenheid
    assert fles.eenheid_norm == "l", fles.eenheid_norm

    stuks = vomar._naar_standaardprijs(_product(contents="6", unit="stuks", price=2.4), PADEN)
    assert stuks.eenheid_norm == "stuk", stuks.eenheid_norm

    # Ontbreekt de eenheid, dan geen verzonnen kiloprijs.
    kaal = vomar._naar_standaardprijs(_product(contents="500", unit=""), PADEN)
    assert kaal.prijs_per_eenheid is None
    assert kaal.prijs == 10.55

    print("  inhoud en kiloprijs: goed")


def test_prijs():
    """Een prijs van nul betekent "niet bekend" en levert geen gratis product op."""
    assert vomar._bedrag(0) is None
    assert vomar._bedrag(None) is None
    assert vomar._bedrag("onzin") is None
    assert vomar._bedrag(1.25) == 1.25

    gratis = vomar._naar_standaardprijs(_product(price=0), PADEN)
    assert gratis.prijs is None
    assert gratis.prijs_per_eenheid is None

    print("  prijzen: goed")


def test_dubbel():
    """Hetzelfde artikelnummer twee keer: de laagste prijs blijft staan."""
    duur = vomar._naar_standaardprijs(_product(price=2.69), PADEN)
    goedkoop = vomar._naar_standaardprijs(_product(price=2.49), PADEN)

    assert vomar._goedkoopste(goedkoop, duur).prijs == 2.49
    assert vomar._goedkoopste(duur, goedkoop).prijs == 2.49
    assert vomar._goedkoopste(duur, None).prijs == 2.69

    # Een product zonder prijs mag er nooit eentje mét verdringen.
    zonder = vomar._naar_standaardprijs(_product(price=0), PADEN)
    assert vomar._goedkoopste(zonder, duur).prijs == 2.69
    assert vomar._goedkoopste(duur, zonder).prijs == 2.69

    print("  dubbele artikelnummers: goed")


def test_webadres():
    """De link naar vomar.nl, ook als er komma's en ampersands in de namen staan."""
    product = vomar._naar_standaardprijs(_product(), PADEN)
    assert product.product_url == (
        "https://www.vomar.nl/producten/frisdrank-sappen-koffie-thee/"
        "koffie-cacao-en-thee/douwe-egberts-espresso-bonen/109627"
    ), product.product_url

    assert product.afbeelding_url.startswith("https://d3vricquk1sjgf.cloudfront.net/")

    # Geen foto meegeleverd is geen reden om het product te laten vallen.
    zonder = vomar._naar_standaardprijs(_product(images=[]), PADEN)
    assert zonder.afbeelding_url is None
    assert zonder.prijs == 10.55

    print("  links en foto's: goed")


def test_indeling_leeg():
    """Zonder winkelindeling stoppen we; stil doorgaan zou groeploze producten geven."""
    origineel = vomar._vraag
    vomar._vraag = lambda *_, **__: {"departments": []}
    try:
        vomar._indeling(_NepSessie())
    except vomar.VomarFout:
        pass
    else:
        raise AssertionError("een lege indeling hoort een storing te zijn")
    finally:
        vomar._vraag = origineel

    print("  lege indeling: goed")


if __name__ == "__main__":
    test_productgroep()
    test_inhoud()
    test_prijs()
    test_dubbel()
    test_webadres()
    test_indeling_leeg()
    print("Alle controles op het assortiment van Vomar geslaagd.")
