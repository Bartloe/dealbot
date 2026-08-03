"""
===============================================================================
 Dealbot — controle op de aanbiedingen van Lidl

 Versie      : 1.0
 Reden       : Lidl is de vijfde winkel. Twee dingen zijn hier eigen aan deze
               bron en dus het controleren waard: een deel van de prijzen geldt
               alleen met de Lidl Plus-kaart, en de begin- en einddatum komen
               als tijdstempel binnen — in wereldtijd gerekend zou een actie een
               dag te vroeg beginnen.
 Datum       : 03-08-2026 13:20

 Onderdelen:
   test_gewone_prijs()   - prijs, van-prijs, inhoud, groep en link
   test_lidl_plus()      - de kaartprijs telt mee, mét vermelding van de kaart
   test_zonder_prijs()   - een blokje zonder prijs is geen aanbieding
   test_datums()         - middernacht Nederlandse tijd hoort bij de juiste dag
   test_groep()          - de onderste laag, met hoofdletter
   test_blokken()        - onleesbare blokjes worden overgeslagen

 Uitvoeren:
   python scripts/tests/test_lidl.py
===============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.bronnen import lidl  # noqa: E402

# Maandag 3 augustus 2026 00:00 en zondag 9 augustus 2026 23:59, Nederlandse tijd.
START = 1785708000
EINDE = 1786312799


def _blok(**rest):
    """Eén productblokje zoals Lidl het in zijn pagina zet."""
    blok = {
        "productId": 10031466,
        "fullTitle": "Gouda belegen stuk kaas",
        "canonicalPath": "/p/gouda-belegen-stuk-kaas/p10031466",
        "image": "https://plaatjes.lidl.nl/kaas.png",
        "storeStartDate": START,
        "storeEndDate": EINDE,
        "keyfacts": {
            "wonCategoryPrimary": "Werelden/Eten/Kaas, zuivelproducten & eieren/Yoghurt",
        },
        "price": {
            "price": 4.19,
            "oldPrice": 5.99,
            "packaging": {"text": "500 g"},
            "discount": {"discountText": "-30%"},
        },
    }
    blok.update(rest)
    return blok


def test_gewone_prijs():
    """Een gewone aanbieding: prijs, van-prijs, kiloprijs, groep en link."""
    aanbieding = lidl._naar_aanbieding(_blok())

    assert aanbieding is not None
    assert aanbieding.prijs == 4.19, aanbieding.prijs
    assert aanbieding.normale_prijs == 5.99, aanbieding.normale_prijs
    assert aanbieding.actie_tekst == "-30%", aanbieding.actie_tekst
    assert aanbieding.prijs_per_eenheid == 8.38, aanbieding.prijs_per_eenheid
    assert aanbieding.eenheid_norm == "kg"
    assert aanbieding.product_url == "https://www.lidl.nl/p/gouda-belegen-stuk-kaas/p10031466"

    # Een doorgestreepte prijs kan ook in het kortingsblokje staan.
    anders = lidl._naar_aanbieding(_blok(price={
        "price": 1.99, "oldPrice": 0, "discount": {"deletedPrice": 2.99, "discountText": "Actie"},
    }))
    assert anders.normale_prijs == 2.99, anders.normale_prijs
    # "Actie" zegt niets extra's en hoort dus niet in de actietekst.
    assert anders.actie_tekst is None, anders.actie_tekst

    print("  gewone aanbieding: goed")


def test_lidl_plus():
    """Een prijs die alleen met de kaart geldt telt mee, maar dan wel vermeld."""
    kaart = lidl._naar_aanbieding(_blok(
        price={"currencyCode": "EUR"},
        lidlPlus=[{"price": {
            "price": 0.49,
            "oldPrice": 0.79,
            "packaging": {"text": "Per stuk"},
            "discount": {"discountText": "-38%"},
        }}],
    ))

    assert kaart.prijs == 0.49, kaart.prijs
    assert kaart.normale_prijs == 0.79, kaart.normale_prijs
    assert kaart.actie_tekst == "-38%, met Lidl Plus", kaart.actie_tekst
    assert kaart.eenheid_norm == "stuk", kaart.eenheid_norm

    # Een vanafprijs hoort erbij te staan: de rest van de reeks is duurder.
    vanaf = lidl._naar_aanbieding(_blok(price={
        "price": 1.49, "prefix": "VANAF", "discount": {"discountText": "Elders €3.99"},
    }))
    assert vanaf.actie_tekst == "Elders €3.99, vanafprijs", vanaf.actie_tekst

    print("  Lidl Plus en vanafprijs: goed")


def test_zonder_prijs():
    """Een blokje zonder prijs of zonder naam is geen aanbieding."""
    assert lidl._naar_aanbieding(_blok(price={"currencyCode": "EUR"})) is None
    assert lidl._naar_aanbieding(_blok(price={"price": 0})) is None
    assert lidl._naar_aanbieding(_blok(fullTitle="", title="")) is None
    assert lidl._naar_aanbieding(_blok(productId=None)) is None

    print("  blokje zonder prijs of naam: goed")


def test_datums():
    """Middernacht Nederlandse tijd hoort bij de dag die dan begint."""
    aanbieding = lidl._naar_aanbieding(_blok())
    assert aanbieding.geldig_van == "2026-08-03", aanbieding.geldig_van
    assert aanbieding.geldig_tot == "2026-08-09", aanbieding.geldig_tot

    # Onzin in een tijdstempel laat de aanbieding staan, zonder datum.
    kaal = lidl._naar_aanbieding(_blok(storeStartDate=None, storeEndDate="later"))
    assert kaal.geldig_van is None and kaal.geldig_tot is None

    # Zonder einddatum blijft een aanbieding staan; met een datum van gisteren niet.
    assert lidl._loopt_nog(None)
    assert lidl._loopt_nog("2099-01-01")
    assert not lidl._loopt_nog("2020-01-01")

    print("  begin- en einddatum: goed")


def test_groep():
    """De onderste laag van de indeling is de groep, met hoofdletter."""
    assert lidl._naar_aanbieding(_blok()).productgroep == "Yoghurt"

    klein = _blok(keyfacts={"wonCategoryPrimary": "Werelden/Eten/Vlees & gevogelte/rundvlees"})
    assert lidl._naar_aanbieding(klein).productgroep == "Rundvlees"

    # Zonder indeling blijft de groep leeg; de aanbieding zelf blijft staan.
    leeg = lidl._naar_aanbieding(_blok(keyfacts={}))
    assert leeg.productgroep is None and leeg.prijs == 4.19

    print("  productgroep: goed")


def test_blokken():
    """Een onleesbaar blokje wordt overgeslagen, de rest blijft."""
    pagina = (
        '<div data-grid-data="{&quot;productId&quot;:1,&quot;fullTitle&quot;:&quot;Kaas&quot;}">'
        '<div data-grid-data="{kapot">'
        '<div data-grid-data="[1,2]">'
    )
    blokken = lidl._blokken(pagina)
    assert len(blokken) == 1, blokken
    assert blokken[0]["fullTitle"] == "Kaas"

    print("  onleesbare blokjes: goed")


if __name__ == "__main__":
    test_gewone_prijs()
    test_lidl_plus()
    test_zonder_prijs()
    test_datums()
    test_groep()
    test_blokken()
    print("Alle controles op de aanbiedingen van Lidl geslaagd.")
