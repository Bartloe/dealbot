"""
===============================================================================
 Dealbot — vragen stellen aan Gemini over een folderpagina

 Versie      : 1.0
 Reden       : De aanbiedingen van Vomar staan alleen in een digitale folder.
               Die is met het blote oog prima te lezen maar niet met gewone
               programmacode: prijzen staan als losse cijfers over de plaatjes
               heen. Een AI die naar de pagina kíjkt lost dat op. Deze module
               regelt het gesprek met Google Gemini en houdt vol als de dienst
               het even laat afweten (foutmelding 503, "high demand").
 Datum       : 02-08-2026 22:40

 De aanpak met de sleutels en het geduld is overgenomen uit project subs, waar
 hetzelfde probleem al is uitgevochten: dezelfde foutcode betekent daar soms
 "je gaat te snel" (wachten helpt) en soms "je bent door je dagvoorraad heen"
 (alleen een andere sleutel helpt). Wie dat door elkaar haalt, schrijft sleutels
 af die nog prima werken.

 Onderdelen:
   sleutels()          - de Gemini-sleutels uit .env, op volgorde
   Antwoord            - wat er uit één vraag komt: gegevens of een nette fout
   Vraagbaak           - stelt de vraag, wisselt van sleutel en heeft geduld
   _soort_fout()       - vertaalt de klacht van Google naar wat we moeten doen
   _voorgestelde_rust()- de wachttijd die Google zelf noemt, met een bovengrens
===============================================================================
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

# Welk model naar de folderpagina's kijkt. Te veranderen zonder programmeerwerk
# via GEMINI_MODEL in .env; Google sluit oudere modellen na verloop van tijd af.
STANDAARD_MODEL = "gemini-3.6-flash"

# Laag houden: we willen dat het model afleest wat er staat, niet dat het iets
# aardigs verzint.
TEMPERATUUR = 0.1

# Rust tussen twee vragen op dezelfde sleutel, zodat de minuutlimiet niet knelt.
RUST_TUSSEN_VRAGEN = 4.0

# Wachttijden bij drukte, bij dezelfde sleutel. Deze reeks loopt op zodat een
# drukke dienst de ruimte krijgt om af te koelen.
GEDULD = (4, 8, 16, 32)
MAX_WACHTEN = 90.0            # nooit langer stilstaan, ook niet als Google dat vraagt
MAX_RONDES = 3                # zo vaak alle sleutels langs bij een storing
PAUZE_TUSSEN_RONDES = (10, 20)

# Meldingen waarbij het zin heeft het gewoon nog eens te proberen: de dienst is
# overbelast of de verbinding valt weg. De 503 "high demand" hoort hierbij.
_HAPERINGEN = (
    "503", "unavailable", "overloaded", "high demand", "500", "502", "504",
    "internal", "server disconnected", "remoteprotocolerror", "connecterror",
    "readerror", "readtimeout", "writeerror", "timed out", "timeout",
    "connection reset", "connection aborted", "eof occurred", "sslerror",
)

# Een lege tegoedmeter komt óók binnen als 429, maar gaat niet over met wachten.
_TEGOED_OP = ("prepayment", "credits are depleted", "credits_depleted", "enable billing")

# Google zet de gevraagde rusttijd in de foutmelding: "retryDelay: '23s'".
_RUSTVERZOEK = re.compile(r"retry[_-]?delay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)\s*s",
                          re.IGNORECASE)


def sleutels() -> list[tuple[str, str]]:
    """
    De Gemini-sleutels uit de omgeving, op volgorde van gebruik.

    GEMINI_API_KEY, daarna GEMINI_API_KEY_2, _3 en zo verder. Elke sleutel heeft
    zijn eigen gratis dagvoorraad, dus hoe meer er staan, hoe meer folderpagina's
    er op een dag gelezen kunnen worden.
    """
    gevonden: list[tuple[str, str]] = []
    eerste = os.environ.get("GEMINI_API_KEY")
    if eerste:
        gevonden.append(("GEMINI_API_KEY", eerste.strip()))

    nummer = 2
    while True:
        naam = f"GEMINI_API_KEY_{nummer}"
        waarde = os.environ.get(naam)
        if not waarde:
            break
        gevonden.append((naam, waarde.strip()))
        nummer += 1

    return gevonden


@dataclass
class Antwoord:
    """Wat één vraag oplevert: de gegevens, of een uitleg waarom het niet lukte."""

    inhoud: Any = None
    fout: str = ""
    sleutel: str = ""
    invoer_tokens: int = 0
    uitvoer_tokens: int = 0
    denk_tokens: int = 0

    @property
    def gelukt(self) -> bool:
        return not self.fout and self.inhoud is not None


class Vraagbaak:
    """
    Stelt vragen aan Gemini over een afbeelding, en blijft daarbij overeind.

    Eén exemplaar per ophaalronde: hij onthoudt welke sleutels op zijn, zodat
    een volgende pagina niet opnieuw tegen dezelfde muur loopt.
    """

    def __init__(self, model: str = "", rust: float = RUST_TUSSEN_VRAGEN):
        self._sleutels = sleutels()
        self._op: set[int] = set()               # sleutels die deze ronde niets meer kunnen
        self._zonder_tegoed: set[int] = set()
        self._zonder_toegang: set[int] = set()
        self._laatst_gebruikt: dict[int, float] = {}
        self.model = model or os.environ.get("GEMINI_MODEL") or STANDAARD_MODEL
        self.rust = rust
        self.aanroepen = 0                       # om achteraf te kunnen zeggen wat het kostte
        self.tokens = 0

    # --------------------------------------------------------------- toestand

    def beschikbaar(self) -> tuple[bool, str]:
        """
        Valt er nog iets te vragen, en zo nee: waarom niet?

        De reden is belangrijk, want het advies verschilt. Een opgebruikt
        dagquotum gaat morgen vanzelf over, een leeg tegoed niet.
        """
        if not self._sleutels:
            return False, ("er staat geen Gemini-sleutel in .env (GEMINI_API_KEY). "
                           "Zonder sleutel is de folder niet te lezen")
        if self._bruikbaar():
            return True, ""
        if len(self._zonder_toegang) == len(self._sleutels):
            return False, (f"geen enkele sleutel mag het model {self.model} gebruiken; "
                           f"zet een ander model in .env (GEMINI_MODEL)")
        if len(self._zonder_tegoed) == len(self._sleutels):
            return False, ("het tegoed van alle Gemini-sleutels is op; zet de projecten "
                           "in AI Studio terug op de gratis stand")
        return False, "de dagvoorraad van alle Gemini-sleutels is op"

    def _bruikbaar(self) -> list[int]:
        return [nummer for nummer in range(len(self._sleutels)) if nummer not in self._op]

    def sleutelnamen(self) -> list[str]:
        return [naam for naam, _ in self._sleutels]

    # ----------------------------------------------------------------- vragen

    def vraag_over_afbeelding(self, afbeelding: bytes, opdracht: str,
                              vorm: dict[str, Any], omschrijving: str = "") -> Antwoord:
        """
        Laat Gemini naar één afbeelding kijken en antwoorden in een vaste vorm.

        De volgorde is: bij drukte geduldig blijven op dezelfde sleutel, pas
        doorschakelen als die sleutel echt niet meer kan, en pas helemaal opnieuw
        beginnen als de hele rij niets opleverde.
        """
        kan, reden = self.beschikbaar()
        if not kan:
            return Antwoord(fout=reden)

        instelling = self._instelling(vorm)
        if instelling is None:
            return Antwoord(fout="de bibliotheek google-genai is niet geïnstalleerd")

        naam_erbij = f" ({omschrijving})" if omschrijving else ""
        laatste_klacht = ""

        for ronde in range(1, MAX_RONDES + 1):
            for nummer in self._bruikbaar():
                naam = self._sleutels[nummer][0]
                antwoord, soort, melding = self._sleutel_gebruiken(
                    nummer, afbeelding, opdracht, instelling)

                if antwoord is not None:
                    return antwoord

                if soort == "quotum":
                    self._op.add(nummer)
                    log.warning("Gemini: de dagvoorraad van %s is op; volgende sleutel.", naam)
                    continue

                if soort == "geen tegoed":
                    self._op.add(nummer)
                    self._zonder_tegoed.add(nummer)
                    log.warning("Gemini: het tegoed van %s is op; die sleutel doet deze "
                                "ronde niet meer mee.", naam)
                    continue

                if soort == "geen toegang":
                    self._op.add(nummer)
                    self._zonder_toegang.add(nummer)
                    log.warning("Gemini: %s mag het model %s niet gebruiken; die sleutel "
                                "doet deze ronde niet meer mee.", naam, self.model)
                    continue

                if soort in ("tempo", "hapering"):
                    laatste_klacht = melding
                    uitleg = ("de dienst bleef om rust vragen" if soort == "tempo"
                              else "de dienst was overbelast of de verbinding viel weg")
                    log.info("Gemini%s: %s bij %s (%s); volgende sleutel.",
                             naam_erbij, uitleg, naam, melding[:120])
                    continue

                return Antwoord(fout=f"Gemini gaf een fout ({naam}): {melding[:200]}")

            if not self._bruikbaar():
                break
            if ronde < MAX_RONDES:
                pauze = PAUZE_TUSSEN_RONDES[min(ronde, len(PAUZE_TUSSEN_RONDES)) - 1]
                log.warning("Gemini%s: geen enkele sleutel kwam door (ronde %s van %s); "
                            "%s seconden wachten.", naam_erbij, ronde, MAX_RONDES, pauze)
                time.sleep(pauze)

        if not self._bruikbaar():
            _, reden = self.beschikbaar()
            return Antwoord(fout=reden)
        if laatste_klacht:
            return Antwoord(fout=(f"Gemini bleef {MAX_RONDES} rondes lang onbereikbaar bij "
                                  f"elke sleutel ({laatste_klacht[:120]})"))
        return Antwoord(fout="Gemini gaf geen antwoord")

    def _sleutel_gebruiken(self, nummer: int, afbeelding: bytes, opdracht: str,
                           instelling) -> tuple[Antwoord | None, str, str]:
        """
        Probeert één sleutel, en blijft geduldig zolang het alleen om drukte gaat.

        Levert (Antwoord, "", "") bij succes, en anders (None, soort, melding),
        zodat de aanroeper weet of doorschakelen zin heeft.
        """
        naam, sleutel = self._sleutels[nummer]

        for poging, wachttijd in enumerate(GEDULD, start=1):
            self._rust_houden(nummer)

            begonnen = time.time()
            ruw, soort, melding = self._proberen(sleutel, afbeelding, opdracht, instelling)
            self._laatst_gebruikt[nummer] = time.time()

            if ruw is not None:
                self.aanroepen += 1
                antwoord = self._uitpakken(ruw, naam)
                self.tokens += (antwoord.invoer_tokens + antwoord.uitvoer_tokens
                                + antwoord.denk_tokens)
                if antwoord.gelukt:
                    log.debug("Gemini: antwoord van %s na %.0fs.", naam, time.time() - begonnen)
                    return antwoord, "", ""
                # Een leeg of onleesbaar antwoord: het opnieuw proberen is zinvol,
                # net als bij drukte.
                melding, soort = antwoord.fout, "tempo"

            if soort != "tempo":
                return None, soort, melding

            if poging == len(GEDULD):
                return None, "tempo", melding

            pauze = _voorgestelde_rust(melding) or float(wachttijd)
            log.info("Gemini: %s vraagt om rust (poging %s van %s); %.0f seconden wachten.",
                     naam, poging, len(GEDULD), pauze)
            time.sleep(pauze)

        return None, "tempo", ""

    def _rust_houden(self, nummer: int) -> None:
        """Wacht zo nodig tot deze sleutel weer aan de beurt is."""
        verstreken = time.time() - self._laatst_gebruikt.get(nummer, 0.0)
        if verstreken < self.rust:
            time.sleep(self.rust - verstreken)

    # ----------------------------------------------------------------- intern

    def _instelling(self, vorm: dict[str, Any]):
        """Bouwt de instellingen voor de aanroep; None als de bibliotheek ontbreekt."""
        try:
            from google.genai import types
        except ImportError as fout:
            log.error("De bibliotheek google-genai is niet geïnstalleerd: %s", fout)
            return None

        return types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=vorm,
            temperature=TEMPERATUUR,
        )

    def _proberen(self, sleutel: str, afbeelding: bytes, opdracht: str, instelling):
        """Eén sleutel één keer proberen. Elke fout komt als tekst terug, niet als crash."""
        from google import genai
        from google.genai import types

        try:
            klant = genai.Client(api_key=sleutel)
            antwoord = klant.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=afbeelding, mime_type="image/jpeg"),
                    opdracht,
                ],
                config=instelling,
            )
            return antwoord, "", ""
        except Exception as fout:  # noqa: BLE001 - elke fout netjes vertalen
            melding = f"{type(fout).__name__}: {fout}"
            return None, _soort_fout(melding), melding

    @staticmethod
    def _uitpakken(ruw, sleutel: str) -> Antwoord:
        """Haalt de gegevens en het tokenverbruik uit wat Gemini teruggaf."""
        import json

        invoer, uitvoer, denken = _tokens(ruw)
        tekst = getattr(ruw, "text", None)
        if not tekst:
            return Antwoord(fout="Gemini gaf een leeg antwoord", sleutel=sleutel,
                            invoer_tokens=invoer, uitvoer_tokens=uitvoer, denk_tokens=denken)
        try:
            inhoud = json.loads(tekst)
        except (json.JSONDecodeError, ValueError) as fout:
            return Antwoord(fout=f"het antwoord was geen bruikbare vorm ({fout})",
                            sleutel=sleutel, invoer_tokens=invoer, uitvoer_tokens=uitvoer,
                            denk_tokens=denken)

        return Antwoord(inhoud=inhoud, sleutel=sleutel, invoer_tokens=invoer,
                        uitvoer_tokens=uitvoer, denk_tokens=denken)


def _tokens(antwoord) -> tuple[int, int, int]:
    """Het tokenverbruik: erin, eruit en nagedacht. Het nadenken telt gewoon mee."""
    meting = getattr(antwoord, "usage_metadata", None)
    if meting is None:
        return 0, 0, 0

    def getal(veld: str) -> int:
        return int(getattr(meting, veld, 0) or 0)

    invoer = getal("prompt_token_count")
    uitvoer = getal("candidates_token_count")
    denken = getal("thoughts_token_count")
    if not denken:
        denken = max(0, getal("total_token_count") - invoer - uitvoer)
    return invoer, uitvoer, denken


def _soort_fout(melding: str) -> str:
    """
    Wat voor fout is dit: tempo, quotum, geen tegoed, geen toegang of hapering?

    Google stuurt voor "je gaat te snel" en "je dagvoorraad is op" dezelfde code
    (429). Alleen als er letterlijk over een dag gesproken wordt is de sleutel
    echt op; in alle andere gevallen gaan we ervan uit dat we te snel waren.
    Wachten kost niets, een sleutel ten onrechte afschrijven wel.
    """
    laag = melding.lower()
    if "404" in melding and ("model" in laag or "not_found" in laag):
        return "geen toegang"
    if any(stuk in laag for stuk in _TEGOED_OP):
        return "geen tegoed"
    if "429" in melding or "resource_exhausted" in laag:
        samengeperst = laag.replace(" ", "").replace("_", "").replace("-", "")
        if "perday" in samengeperst or "daily" in samengeperst:
            return "quotum"
        return "tempo"
    if any(stuk in laag for stuk in _HAPERINGEN):
        return "hapering"
    return "overig"


def _voorgestelde_rust(melding: str) -> float:
    """De rusttijd die Google zelf noemt, begrensd; 0 als hij niets voorstelt."""
    treffer = _RUSTVERZOEK.search(melding)
    if not treffer:
        return 0.0
    try:
        return min(float(treffer.group(1)), MAX_WACHTEN)
    except ValueError:
        return 0.0
