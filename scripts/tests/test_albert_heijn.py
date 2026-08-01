"""
===============================================================================
 Dealbot — controle op het aanvullen van de Albert Heijn-folder

 Versie      : 1.0
 Reden       : De folder noemt geen meerpakken. De aanvulling die dat repareert
               moet twee dingen goed doen: échte meerpakaanbiedingen meenemen en
               blijvende staffelkortingen weren. Dat is met de hand niet meer na
               te lopen, dus leggen we het hier vast.
 Datum       : 01-08-2026 17:20

 Onderdelen:
   test_meerpak_inhoud()  - de inhoud van een meerpak komt van het losse pak
   test_aanvulling()      - wie wel en niet in de lijst hoort
   test_loopt_vandaag()   - de folder van volgende week telt nog niet mee

 Uitvoeren:
   python scripts/tests/test_albert_heijn.py
===============================================================================
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.bronnen import albert_heijn  # noqa: E402

VANDAAG = date.today().isoformat()
GISTEREN = (date.today() - timedelta(days=1)).isoformat()
MORGEN = (date.today() + timedelta(days=1)).isoformat()
VOLGENDE_WEEK = (date.today() + timedelta(days=8)).isoformat()


def _product(webshop_id, titel, **rest):
    """Een product zoals Albert Heijn het aanlevert, met alleen wat wij gebruiken."""
    product = {
        "webshopId": webshop_id,
        "title": titel,
        "isBonus": True,
        "isInfiniteBonus": False,
        "promotionType": "NATIONAL",
        "bonusStartDate": GISTEREN,
        "bonusEndDate": MORGEN,
        "priceBeforeBonus": 10.0,
        "salesUnitSize": "500 g",
    }
    product.update(rest)
    return product


def _meerpak(webshop_id, titel, los_id, aantal, **rest):
    return _product(
        webshop_id, titel,
        isVirtualBundle=True,
        virtualBundleItems=[{"productId": los_id, "quantity": aantal}],
        salesUnitSize=f"{aantal} stuks",
        **rest,
    )


def test_meerpak_inhoud():
    los = _product(100, "Koffiebonen", salesUnitSize="500 g")
    bonus = {"100": los}

    drie_pack = _meerpak(101, "Koffiebonen 3-pack", 100, 3)
    assert albert_heijn._meerpak_inhoud(drie_pack, bonus) == "1500 g"

    # Een los pak dat zelf al uit meerdere stuks bestaat, telt goed door.
    bonus["200"] = _product(200, "Toetjes", salesUnitSize="2 x 125 g")
    assert albert_heijn._meerpak_inhoud(_meerpak(201, "Toetjes 3-pack", 200, 3), bonus) == "750 g"

    # Onbekend los product of een gemengd pakket: geen verzonnen inhoud.
    assert albert_heijn._meerpak_inhoud(_meerpak(102, "Onbekend 2-pack", 999, 2), bonus) is None
    gemengd = _product(103, "Pakket", isVirtualBundle=True, virtualBundleItems=[
        {"productId": 100, "quantity": 1}, {"productId": 200, "quantity": 1}])
    assert albert_heijn._meerpak_inhoud(gemengd, bonus) is None

    print("  meerpak-inhoud: goed")


def test_loopt_vandaag():
    assert albert_heijn._loopt_vandaag(_product(1, "Nu"))
    assert not albert_heijn._loopt_vandaag(
        _product(2, "Volgende week", bonusStartDate=MORGEN, bonusEndDate=VOLGENDE_WEEK))
    assert not albert_heijn._loopt_vandaag(
        _product(3, "Afgelopen", bonusStartDate=GISTEREN, bonusEndDate=GISTEREN))
    print("  geldigheid: goed")


def test_aanvulling():
    bonus = {
        # staat al in de folder, mag niet dubbel
        "100": _product(100, "Koffiebonen", salesUnitSize="500 g"),
        # meerpak van een product dat in de bonus is: hoort erbij
        "101": _meerpak(101, "Koffiebonen 3-pack", 100, 3, currentPrice=27.0),
        # los product dat de folder simpelweg niet noemde
        "110": _product(110, "Snoepgroente", bonusMechanism="3 voor 5.00"),
        # meerpak van een product dat niet in de bonus is: staffelkorting
        "120": _meerpak(120, "Wokgroente 3-pack", 121, 3,
                        bonusMechanism="10% volume voordeel", currentPrice=6.45),
        # loopt door tot ver na deze bonusweek: blijvende webshopkorting
        "130": _product(130, "Parfumset", bonusEndDate="2026-12-31", bonusMechanism="BONUS"),
        # Gall & Gall hoort niet in de supermarktlijst
        "140": _product(140, "Wijn", promotionType="GALL"),
        # de folder van volgende week telt nog niet mee
        "150": _product(150, "Volgende week", bonusStartDate=MORGEN, bonusEndDate=VOLGENDE_WEEK),
    }

    extra = albert_heijn._aanvulling(bonus, {"100"}, MORGEN)
    gevonden = {a.bron_id: a for a in extra}

    assert set(gevonden) == {"101", "110"}, f"onverwacht: {sorted(gevonden)}"

    # Het meerpak krijgt de kiloprijs van drie losse pakken: 27 euro voor 1,5 kg.
    meerpak = gevonden["101"]
    assert meerpak.inhoud_waarde == 1500.0 and meerpak.inhoud_eenheid == "g"
    assert meerpak.prijs_per_eenheid == 18.0, meerpak.prijs_per_eenheid
    assert meerpak.eenheid_norm == "kg"

    print("  aanvulling: goed")


if __name__ == "__main__":
    test_meerpak_inhoud()
    test_loopt_vandaag()
    test_aanvulling()
    print("Alle controles op de Albert Heijn-aanvulling geslaagd.")
