"""
===============================================================================
 Dealbot — kenmerken: de derde laag onder de lade

 Versie      : 1.0
 Reden       : Onze indeling heeft één lade Huishouden / Toiletpapier, met het
               droge en het vochtige door elkaar. Wie alleen het vochtige wil
               volgen kon dat nergens kiezen — en datzelfde speelt bij koffie
               (bonen, pads, capsules), melk (vol, halfvol) en tientallen andere
               laden.

               De laden fijner maken is geen oplossing: dan groeit de indeling
               eindeloos en moet iemand hem met de hand bijhouden. De winkels
               hebben die fijne indeling echter al gemaakt. "Toiletpapier
               Vochtig" bij Vomar, "Toiletpapier - vochtig" bij Albert Heijn:
               het woord staat er, wij gooiden het alleen weg bij het vertalen.

               Deze module bewaart het als kenmerk. Eén woord in onze taal, bij
               elke winkel hetzelfde, en volledig afgeleid uit wat er al is —
               er staat nergens een lijstje dat met de hand wordt bijgehouden.

 Datum       : 05-08-2026 14:45

 Onderdelen:
   MAXIMUM_WOORDEN   - hoe lang een kenmerk hoogstens mag zijn
   GEEN_KENMERK      - woorden die nooit iets verbijzonderen
   stam()            - "vochtige" en "vochtig" over één kam
   opschonen()       - maakt van een ruw antwoord een bruikbaar kenmerk
   Woordenlijst      - wat we per lade aan kenmerken kennen
     .van_koppelingen() - de lijst uit het vertaalboekje opbouwen
     .bekend()          - welke kenmerken kent deze lade al
     .pas_in()          - een nieuw kenmerk opschonen en op bestaande laten vallen
     .uit_naam()        - het kenmerk uit de productnaam vissen
     .leer()            - een kenmerk aan de lijst toevoegen
     .als_tekst()       - de lijst in de vorm die de AI-opdracht nodig heeft

 De lijst groeit per lade en loopt daarna vanzelf vol: bij de eerste winkel is
 "vochtig" nieuw, bij de tweede en derde valt hun woord erop terug. Zo krijg je
 geen drie knopjes voor hetzelfde.
===============================================================================
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from .indeling import schoon

log = logging.getLogger(__name__)

# Een kenmerk is een verbijzondering, geen omschrijving. Meer dan twee woorden
# betekent dat de AI de groepsnaam heeft overgeschreven in plaats van er iets
# uit te halen; dat levert een knopje op waar niemand op klikt.
MAXIMUM_WOORDEN = 2
MAXIMUM_TEKENS = 24

# Woorden die op zichzelf niets verbijzonderen. "Overige koffie" is geen soort
# koffie, en een kenmerk "diversen" splitst een lade niet maar verdubbelt hem.
GEEN_KENMERK: frozenset[str] = frozenset({
    "overig", "overige", "divers", "diversen", "algemeen", "algemene", "rest",
    "restant", "ander", "andere", "gewoon", "gewone", "standaard", "normaal",
    "normale", "assortiment", "producten", "product", "artikelen", "soorten",
    "en", "of", "van", "voor", "met", "de", "het", "een", "bij", "in", "op",
})

# Deze uitgangen mogen wegvallen bij het vergelijken. Het gaat er niet om
# taalkundig te ontleden, maar om te voorkomen dat "vochtig", "vochtige" en
# "vochtigs" drie aparte knopjes worden.
_UITGANGEN = ("etjes", "ejes", "eren", "tjes", "jes", "en", "es", "e", "s")


def stam(woord: str) -> str:
    """
    Kort een woord in tot zijn stam, ruw maar voorspelbaar.

    Alleen om twee schrijfwijzen van hetzelfde woord bij elkaar te brengen.
    Korte woorden blijven heel: van "pads" mag geen "pad" worden gemaakt zonder
    dat het iets oplevert, en van "vol" al helemaal niets.

    De dubbele medeklinker gaat er aan het eind af. Dat is geen franje maar het
    hele punt: in het Nederlands wordt "halfvol" verbogen tot "halfvolle", en
    zonder deze stap blijven dat twee verschillende woorden. Precies dat zou de
    ene winkel bij het knopje "halfvol" zetten en de andere bij "halfvolle".
    """
    if len(woord) <= 4:
        return woord
    for uitgang in _UITGANGEN:
        if woord.endswith(uitgang) and len(woord) - len(uitgang) >= 4:
            return _enkele_medeklinker(woord[: -len(uitgang)])
    return woord


def _enkele_medeklinker(woord: str) -> str:
    """Haalt een verdubbelde slotmedeklinker weg: "voll" wordt "vol"."""
    if len(woord) >= 4 and woord[-1] == woord[-2] and woord[-1] not in "aeiou":
        return woord[:-1]
    return woord


def _stamvorm(kenmerk: str) -> str:
    """Het hele kenmerk op stam, zodat twee kenmerken vergelijkbaar worden."""
    return " ".join(stam(woord) for woord in kenmerk.split())


def opschonen(ruw: str | None, hoofdgroep: str | None, subgroep: str | None) -> str | None:
    """
    Maakt van een ruw antwoord een bruikbaar kenmerk, of niets.

    Er gaan drie dingen af. Eerst de vorm: kleine letters, geen accenten, geen
    leestekens. Dan de woorden van de lade zelf — geeft de AI "toiletpapier
    vochtig" terug, dan is alleen "vochtig" de verbijzondering; de rest wisten we
    al. En tot slot de woorden die niets zeggen.

    Blijft er niets over, dan is dat het goede antwoord: deze winkelgroep dekt
    de hele lade en heeft niets te verbijzonderen.
    """
    plat = schoon(ruw)
    if not plat:
        return None

    # De naam van de lade en de afdeling zijn geen verbijzondering: die staan al
    # boven het knopje. Op stam vergeleken, want een winkel schrijft "papier"
    # waar onze lade "Toiletpapier" heet.
    eigen_woorden = {
        stam(woord)
        for naam in (hoofdgroep, subgroep)
        for woord in schoon(naam).split()
    }

    woorden = [
        woord for woord in plat.split()
        if woord not in GEEN_KENMERK
        and stam(woord) not in eigen_woorden
        and not woord.isdigit()
    ]

    if not woorden or len(woorden) > MAXIMUM_WOORDEN:
        return None

    kenmerk = " ".join(woorden)
    if len(kenmerk) > MAXIMUM_TEKENS or len(kenmerk) < 3:
        return None
    return kenmerk


class Woordenlijst:
    """
    Wat we per lade aan kenmerken kennen.

    Bewust geen tabel in de database en geen lijst in de code: de inhoud komt
    uit het vertaalboekje dat er toch al is. Elke winkelgroep die vertaald is,
    heeft mogelijk een kenmerk opgeleverd, en samen vormen die de woordenschat
    van die lade. Komt er een winkel bij, dan groeit de lijst vanzelf mee.
    """

    def __init__(self) -> None:
        # Per lade de kenmerken, en per lade de stamvorm -> het gekozen woord.
        # Dat tweede is wat "vochtige" op "vochtig" laat vallen.
        self._per_lade: dict[tuple[str, str], set[str]] = {}
        self._per_stam: dict[tuple[str, str], dict[str, str]] = {}

    # -- opbouwen ------------------------------------------------------------
    @classmethod
    def van_koppelingen(cls, rijen: Iterable[dict[str, Any]]) -> "Woordenlijst":
        """Bouwt de lijst op uit het vertaalboekje zoals het in de database staat."""
        lijst = cls()
        for rij in rijen:
            if rij.get("hoofdgroep") and rij.get("subgroep") and rij.get("kenmerk"):
                lijst.leer(rij["hoofdgroep"], rij["subgroep"], rij["kenmerk"])
        return lijst

    def leer(self, hoofdgroep: str, subgroep: str, kenmerk: str) -> None:
        """Zet een kenmerk in de lijst. Al bekend is geen bezwaar."""
        sleutel = (hoofdgroep, subgroep)
        plat = schoon(kenmerk)
        if not plat:
            return
        self._per_lade.setdefault(sleutel, set()).add(plat)
        self._per_stam.setdefault(sleutel, {}).setdefault(_stamvorm(plat), plat)

    # -- opzoeken ------------------------------------------------------------
    def bekend(self, hoofdgroep: str | None, subgroep: str | None) -> tuple[str, ...]:
        """De kenmerken die deze lade al kent, de langste eerst."""
        if not hoofdgroep or not subgroep:
            return ()
        gevonden = self._per_lade.get((hoofdgroep, subgroep), set())
        return tuple(sorted(gevonden, key=lambda woord: (-len(woord), woord)))

    def laden(self) -> tuple[tuple[str, str], ...]:
        """Alle laden waarvoor we kenmerken kennen, op alfabet."""
        return tuple(sorted(self._per_lade))

    def pas_in(
        self, hoofdgroep: str | None, subgroep: str | None, ruw: str | None
    ) -> str | None:
        """
        Schoont een nieuw kenmerk op en laat het op een bestaand woord vallen.

        Dit is de plek waar de lijst zichzelf bij elkaar houdt. De opdracht aan
        de AI vraagt al om een bestaand woord te hergebruiken, maar vragen is
        geen garantie: hier wordt het afgedwongen. Komt er "vochtige" binnen
        terwijl de lade "vochtig" kent, dan wordt het "vochtig".

        Een lade zonder subgroep krijgt geen kenmerk. Dat is geen beperking maar
        een keuze: zonder lade is "vochtig" niet te plaatsen, want dat bestaat
        bij het toiletpapier én bij de doekjes.
        """
        if not hoofdgroep or not subgroep:
            return None

        kenmerk = opschonen(ruw, hoofdgroep, subgroep)
        if not kenmerk:
            return None

        bestaand = self._per_stam.get((hoofdgroep, subgroep), {}).get(_stamvorm(kenmerk))
        if bestaand and bestaand != kenmerk:
            log.debug("Kenmerk %r valt samen met het bestaande %r (%s / %s).",
                      kenmerk, bestaand, hoofdgroep, subgroep)
            return bestaand

        self.leer(hoofdgroep, subgroep, kenmerk)
        return kenmerk

    def uit_naam(
        self, hoofdgroep: str | None, subgroep: str | None, product_naam: str | None
    ) -> str | None:
        """
        Vist het kenmerk uit de productnaam. Het vangnet.

        Nodig voor de winkels die het onderscheid niet in hun groepsnaam maken:
        bij Dirk heet alles gewoon "Toiletpapier", maar op het pak staat wel
        degelijk "vochtig". Er wordt uitsluitend gezocht naar woorden die deze
        lade al kent van een andere winkel — dus nooit naar iets dat zelf
        bedacht is, en altijd binnen een handjevol mogelijkheden.

        Op hele woorden, niet op letterreeksen: anders zou "vol" ook aanslaan op
        "volkoren" en "voller".
        """
        kandidaten = self.bekend(hoofdgroep, subgroep)
        if not kandidaten:
            return None

        naam = schoon(product_naam)
        if not naam:
            return None

        woorden = [stam(woord) for woord in naam.split()]
        # De langste kandidaat eerst: "halfvolle melk" gaat vóór "vol".
        for kenmerk in kandidaten:
            delen = [stam(deel) for deel in kenmerk.split()]
            if _bevat_reeks(woorden, delen):
                return kenmerk
        return None

    # -- voor de AI-opdracht -------------------------------------------------
    def als_tekst(self, maximum_regels: int = 250) -> str:
        """
        De bekende kenmerken in de vorm die de opdracht aan de AI nodig heeft.

        Alleen de laden die al kenmerken hebben; de rest zou de opdracht alleen
        maar langer maken. Bij de eerste ronde is dit dus leeg en verzint de AI
        ze allemaal zelf — daarna groeit het uit naar een woordenschat die
        stabiel blijft.
        """
        regels = []
        for hoofdgroep, subgroep in self.laden():
            woorden = ", ".join(sorted(self._per_lade[(hoofdgroep, subgroep)]))
            regels.append(f"{hoofdgroep} / {subgroep}: {woorden}")
            if len(regels) >= maximum_regels:
                regels.append("(en verder)")
                break
        return "\n".join(regels)


def _bevat_reeks(woorden: list[str], reeks: list[str]) -> bool:
    """Staat deze reeks woorden achter elkaar in de naam?"""
    if not reeks or len(reeks) > len(woorden):
        return False
    for start in range(len(woorden) - len(reeks) + 1):
        if woorden[start:start + len(reeks)] == reeks:
            return True
    return False


def tel_per_lade(producten: Iterable[dict[str, Any]]) -> dict[tuple[str, str, str], int]:
    """
    Hoe vaak komt elk kenmerk voor? Om ruis te kunnen herkennen.

    Een kenmerk dat maar bij één product voorkomt is geen keuze maar een
    toevalstreffer. De website filtert die er bij het tonen uit; deze telling is
    er om het in het verslag te kunnen laten zien.
    """
    teller: dict[tuple[str, str, str], int] = {}
    for product in producten:
        hoofd, sub, ken = (product.get("hoofdgroep"), product.get("subgroep"),
                           product.get("kenmerk"))
        if hoofd and sub and ken:
            sleutel = (hoofd, sub, ken)
            teller[sleutel] = teller.get(sleutel, 0) + 1
    return teller
