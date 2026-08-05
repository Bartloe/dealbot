"""
===============================================================================
 Dealbot — controle op de aanbiedingen van Picnic

 Versie      : 1.0
 Reden       : Picnic is de zesde winkel en de lastigste bron tot nu toe: hij
               antwoordt met een beschrijving van zijn app-scherm in plaats van
               met kale productgegevens. Wat een tekst betékent, blijkt alleen
               uit de opmaak. Juist die afspraken moeten vastliggen, want als
               Picnic zijn scherm verandert hoort dat hier op te vallen en niet
               pas als de aanbiedingen stilletjes wegblijven.
 Datum       : 05-08-2026 12:45

 Onderdelen:
   test_gewone_prijs()      - een tegel zonder vlaggetje is geen aanbieding
   test_verlaagde_prijs()   - rode prijs plus doorgestreepte prijs
   test_voorwaardelijk()    - "1+1 gratis": de prijs op de tegel is de gewone
   test_prijskampioen()     - een rode prijs zonder vlaggetje is geen actie
   test_merk()              - herkomst ("Uit Nederland") telt niet als merk
   test_inhoud()            - de bereidingstijd is geen verpakking
   test_sleutelfout()       - een rem onderscheiden van een verlopen sleutel
   test_week()              - een actie loopt van maandag tot en met zondag

 Uitvoeren:
   python scripts/tests/test_picnic.py
===============================================================================
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.bronnen import picnic  # noqa: E402

GROEP = "Koffiebonen"
AFDELING = "Koffie & thee"


def _tekst(inhoud, kleur=None, maat=12):
    """Eén stukje tekst op een tegel, zoals Picnic het opmaakt."""
    return {"type": "RICH_TEXT", "markdown": inhoud,
            "textAttributes": {"color": kleur or "#333333", "size": maat}}


def _vlaggetje(inhoud):
    """Het gele blokje waarmee Picnic een aanbieding aanwijst."""
    return {"type": "CONTAINER", "backgroundColor": picnic._VLAG,
            "child": _tekst(inhoud)}


def _kaart(naam="Intens koffiebonen", merk="Douwe Egberts", nummer="s1018049"):
    """Het blokje voor de schermlezer; daar staat het merk in."""
    label = f"{naam}, van {merk}" if merk else naam
    return {"contentType": "SELLING_UNIT", "sellingUnitId": nummer, "productName": naam,
            "unavailableAccessibility": {"accessibilityLabel": label}}


def _tegel(kaart, *teksten):
    """Een producttegel: het blokje voor de schermlezer plus wat er te zien is."""
    return {"type": "STACK", "children": [kaart, *teksten]}


def _lees(kaart, *teksten):
    return picnic._uit_tegel(kaart, _tegel(kaart, *teksten), AFDELING, GROEP)


def test_gewone_prijs():
    """Zonder vlaggetje is het gewoon de schapprijs, geen aanbieding."""
    product = _lees(_kaart(),
                    _tekst("Intens koffiebonen", maat=14),
                    _tekst("10.79", maat=14),
                    _tekst("Douwe Egberts"),
                    _tekst("500 gram", picnic._INHOUD))

    assert product is not None
    assert product.prijs == 10.79
    assert product.oude_prijs is None
    assert product.actie_tekst is None
    assert product.is_aanbieding is False
    assert product.productgroep == GROEP
    assert product.afdeling == AFDELING
    assert product.inhoud_tekst == "500 gram"
    print("  gewone prijs: geen aanbieding, wel een schapprijs")


def test_verlaagde_prijs():
    """Rode prijs met doorgestreepte prijs: de tegelprijs ís de actieprijs."""
    product = _lees(_kaart("Hollandse aardbeien", merk=None),
                    _vlaggetje("20% korting"),
                    _tekst("Hollandse aardbeien", maat=14),
                    _tekst("3.99", "#b40117", maat=14),
                    _tekst("4.99", picnic._OUDE_PRIJS),
                    _tekst("400 gram", picnic._INHOUD))

    assert product.is_aanbieding
    assert product.prijs == 3.99
    assert product.oude_prijs == 4.99

    aanbieding = picnic._naar_aanbieding(product, "2026-08-03", "2026-08-09")
    assert aanbieding.prijs == 3.99, "de verlaagde prijs telt zoals hij er staat"
    assert aanbieding.normale_prijs == 4.99
    assert aanbieding.prijs_per_eenheid == 9.975, "€ 3,99 voor 400 gram"
    print("  verlaagde prijs: 3,99 (was 4,99), € 9,98 per kilo")


def test_voorwaardelijk():
    """
    Bij "1+1 gratis" staat de gewone prijs op de tegel.

    Wie die klakkeloos overneemt, zet de aanbieding twee keer zo duur in de
    lijst als hij is. Dealbot rekent daarom zelf uit wat je per stuk betaalt.
    """
    product = _lees(_kaart("Proteïneshake chocolade", "Melkunie"),
                    _vlaggetje("1+1 gratis"),
                    _tekst("Proteïneshake chocolade", maat=14),
                    _tekst("1.69", maat=14),
                    _tekst("Melkunie"),
                    _tekst("250 ml", picnic._INHOUD))

    assert product.is_aanbieding
    assert product.oude_prijs is None

    aanbieding = picnic._naar_aanbieding(product, "2026-08-03", "2026-08-09")
    assert aanbieding.normale_prijs == 1.69
    assert aanbieding.prijs == 0.845, "twee halen, één betalen"
    print("  1+1 gratis: gewone prijs 1,69 wordt 0,845 per stuk")


def test_prijskampioen():
    """
    Een rode prijs zonder vlaggetje is geen aanbieding.

    Picnic zet het label "Prijskampioen" — een blijvend lage prijs — in dezelfde
    rode kleur als een actieprijs. Alleen het gele vlaggetje telt.
    """
    product = _lees(_kaart("Aromatico pads", "Picnic"),
                    _tekst("Aromatico", maat=14),
                    _tekst("4.59", maat=14),
                    _tekst("Prijskampioen", "#b40117"),
                    _tekst("Picnic"),
                    _tekst("36 pads", picnic._INHOUD))

    assert product.is_aanbieding is False, "Prijskampioen is geen weekaanbieding"
    assert product.prijs == 4.59
    print("  Prijskampioen: rode prijs, maar geen aanbieding")


def test_merk():
    """Herkomst is geen merk; anders vindt het product zijn tegenhanger niet."""
    zonder = _lees(_kaart("Hollandse pruimen", "Uit Nederland"),
                   _tekst("Hollandse pruimen", maat=14),
                   _tekst("6.29", maat=14))
    assert zonder.merk is None, '"Uit Nederland" hoort niet in het merkveld'

    met = _lees(_kaart(),
                _tekst("Intens koffiebonen", maat=14),
                _tekst("10.79", maat=14))
    assert met.merk == "Douwe Egberts"
    print("  merk: Douwe Egberts wel, 'Uit Nederland' niet")


def test_inhoud():
    """
    De verpakking staat tussen andere grijze kreten; we nemen de eerste die als
    hoeveelheid te lezen is. Een bereidingstijd hoort daar niet bij: "30 min"
    zou anders een kiloprijs opleveren die nergens op slaat.
    """
    product = _lees(_kaart("Verse lasagne", "Picnic"),
                    _tekst("Verse lasagne", maat=14),
                    _tekst("6.49", maat=14),
                    _tekst("30 min", picnic._INHOUD),
                    _tekst("2-3 porties", picnic._INHOUD),
                    _tekst("800 gram", picnic._INHOUD))

    assert product.inhoud_tekst == "800 gram"
    print("  inhoud: 800 gram, niet '30 min' en niet '2-3 porties'")


class _Antwoord:
    """Een antwoord van Picnic, genoeg om het soort fout te herkennen."""

    def __init__(self, soort, inhoud):
        self.headers = {"content-type": soort}
        self._inhoud = inhoud

    def json(self):
        if self._inhoud is None:
            raise ValueError("geen json")
        return self._inhoud


def test_sleutelfout():
    """
    Een snelheidsrem is iets anders dan een verlopen sleutel.

    De rem komt als kale webpagina van de portier ervoor en gaat vanzelf over;
    een sleutelprobleem komt netjes verpakt van de ingang zelf en lost zichzelf
    nooit op. Wie die twee door elkaar haalt, stuurt bij elke drukke ochtend
    een loos alarm de beheerpagina op.
    """
    rem = _Antwoord("text/html", None)
    assert picnic._is_sleutelfout(rem) is False

    sleutel = _Antwoord("application/json", {"error": {"code": "AUTH_INVALID_CRED"}})
    assert picnic._is_sleutelfout(sleutel) is True

    tweestaps = _Antwoord("application/json",
                          {"error": {"code": "TWO_FACTOR_AUTHENTICATION_REQUIRED"}})
    assert picnic._is_sleutelfout(tweestaps) is True

    anders = _Antwoord("application/json", {"error": {"code": "NOT_FOUND"}})
    assert picnic._is_sleutelfout(anders) is False
    print("  fouten: rem en sleutelprobleem blijven uit elkaar")


def test_week():
    """Een actie bij Picnic loopt van maandag tot en met zondag."""
    van, tot = picnic._week()
    assert date.fromisoformat(van).weekday() == 0, "begint op maandag"
    assert date.fromisoformat(tot).weekday() == 6, "eindigt op zondag"
    assert (date.fromisoformat(tot) - date.fromisoformat(van)).days == 6
    assert van <= date.today().isoformat() <= tot
    print(f"  looptijd: {van} t/m {tot}")


def main():
    print("Controle op de aanbiedingen van Picnic\n")
    for controle in (test_gewone_prijs, test_verlaagde_prijs, test_voorwaardelijk,
                     test_prijskampioen, test_merk, test_inhoud,
                     test_sleutelfout, test_week):
        controle()
    print("\nAlles goed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
