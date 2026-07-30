"""
===============================================================================
 Dealbot — controle op de prijsnormalisatie

 Versie      : 1.1
 Reden       : Controles toegevoegd voor de aanbiedingsvormen en verpakkingen
               die Jumbo gebruikt: een bedrag korting in euro's, en inhoud die
               als "570 ml" of "6 stuks" wordt aangeleverd.
 Datum       : 31-07-2026 00:12

 Uitvoeren met: python scripts/tests/test_normalisatie.py
===============================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.normalisatie import (  # noqa: E402
    effectieve_prijs,
    lees_inhoud,
    prijs_per_eenheid,
    product_sleutel,
)

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen != verwacht:
        fouten.append(f"{omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")


# --- Inhoud herkennen -------------------------------------------------------
controleer("400 g", lees_inhoud("400 g").norm_waarde, 0.4)
controleer("1,5 l", lees_inhoud("1,5 l").norm_waarde, 1.5)
controleer("125 ml", lees_inhoud("125 ml").norm_waarde, 0.125)
controleer("1 kg", lees_inhoud("1 kg").norm_waarde, 1.0)
controleer("2 x 125 g", lees_inhoud("2 x 125 g").norm_waarde, 0.25)
controleer("6 x 90 ml", lees_inhoud("6 x 90 ml").norm_waarde, 0.54)
controleer("0,52 l", lees_inhoud("0,52 l").norm_waarde, 0.52)
controleer("eenheid van 400 g", lees_inhoud("400 g").norm_eenheid, "kg")
controleer("5 stuks", lees_inhoud("5 stuks").norm_eenheid, "stuk")
controleer("aantal bij 5 stuks", lees_inhoud("5 stuks").norm_waarde, 5.0)
controleer("2-pack", lees_inhoud("2-pack").norm_waarde, 2.0)
controleer("per stuk", lees_inhoud("per stuk").norm_eenheid, "stuk")
controleer("570 ml (zoals Jumbo aanlevert)",
           round(lees_inhoud("570 ml").norm_waarde, 5), 0.57)
controleer("6 stuks (zoals Jumbo aanlevert)", lees_inhoud("6 stuks").norm_eenheid, "stuk")

# Grensgevallen: hier hoort niets uit te komen in plaats van een gok.
controleer("lege tekst", lees_inhoud(""), None)
controleer("niets", lees_inhoud(None), None)
controleer("onbekende maat", lees_inhoud("17 wasbeurten"), None)
controleer("alleen tekst", lees_inhoud("per bosje"), None)

# --- Aanbiedingsvormen omrekenen -------------------------------------------
controleer("kant-en-klare actieprijs", effectieve_prijs("30% korting", 3.42, 4.89), 3.42)
controleer("2 voor 3.50", effectieve_prijs("2 voor 3.50", None, 2.19), 1.75)
controleer("2 VOOR 1.99", effectieve_prijs("2 VOOR 1.99", None, 1.29), 0.995)
controleer("VOOR 3.49", effectieve_prijs("VOOR 3.49", None, 3.99), 3.49)
controleer("1 + 1 gratis", effectieve_prijs("1 + 1 GRATIS", None, 3.00), 1.5)
controleer("2 + 1 gratis", effectieve_prijs("2 + 1 gratis", None, 3.00), 2.0)
controleer("2e halve prijs", effectieve_prijs("2e halve prijs", None, 2.00), 1.5)
controleer("2e gratis", effectieve_prijs("2e gratis", None, 2.00), 1.0)
controleer("25% korting", effectieve_prijs("25% korting", None, 4.00), 3.0)
controleer("1,00 korting", effectieve_prijs("1,00 korting", None, 3.49), 2.49)
controleer("5,00 korting", effectieve_prijs("5,00 korting", None, 21.99), 16.99)
controleer("korting groter dan de prijs",
           effectieve_prijs("5,00 korting", None, 3.00), 0.0)
controleer("geen actietekst", effectieve_prijs(None, None, 2.50), 2.5)
controleer("niets bekend", effectieve_prijs(None, None, None), None)
controleer("onbekende vorm", effectieve_prijs("gratis kruiden erbij", None, 2.00), 2.0)

# --- Kiloprijs --------------------------------------------------------------
controleer("kiloprijs 400 g voor 3.49",
           prijs_per_eenheid(3.49, lees_inhoud("400 g")), 8.725)
controleer("literprijs 1,5 l voor 2.19",
           prijs_per_eenheid(2.19, lees_inhoud("1,5 l")), 1.46)
controleer("kiloprijs zonder inhoud", prijs_per_eenheid(3.49, None), None)
controleer("kiloprijs zonder prijs", prijs_per_eenheid(None, lees_inhoud("400 g")), None)

# --- Groeperen van hetzelfde product ---------------------------------------
controleer("sleutel gelijk ondanks inhoud",
           product_sleutel("AH", "AH Blauwe bessen 300 g"),
           product_sleutel("AH", "AH blauwe bessen"))
controleer("sleutel negeert hoofdletters",
           product_sleutel(None, "Grand'Italia Pesto"),
           "grand italia pesto")
controleer("sleutel negeert accenten",
           product_sleutel(None, "Café crème"), "cafe creme")

# --- Uitkomst ---------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:\n")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op de prijsnormalisatie geslaagd.")
