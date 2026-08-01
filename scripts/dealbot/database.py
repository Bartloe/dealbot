"""
===============================================================================
 Dealbot — verkeer met de database (Supabase)

 Versie      : 1.3
 Reden       : De groepenlijst groeide alleen maar aan. Toen Albert Heijn een
               andere indeling kreeg (de lade "Koffiebonen" in plaats van 1791
               merkschappen) bleven de oude namen dus staan. De lijst wordt nu
               vervangen in plaats van aangevuld, met een rem erop voor het geval
               een ronde half mislukt.
 Datum       : 01-08-2026 21:35

 Onderdelen:
   Database.start_ronde()      - zet een regel in het logboek en geeft het moment
   Database.schrijf()          - schrijft de aanbiedingen weg in blokken
   Database.ruim_oude_op()     - wist wat niet in deze ronde is ververst
   Database.bewaar_groepen()   - zet de winkelindeling in de blijvende lijst
   Database.sluit_ronde()      - schrijft het resultaat in het logboek
===============================================================================
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests

from .model import Aanbieding

log = logging.getLogger(__name__)

_BLOKGROOTTE = 200          # zoveel aanbiedingen per keer wegschrijven
_TIJDSLIMIET = 60


class DatabaseFout(RuntimeError):
    """Er ging iets mis bij het praten met de database."""


class Database:
    """
    Verbinding met Supabase met de geheime servicesleutel.

    Die sleutel hoort alleen in het ophaalscript te zitten, nooit in de website.
    Hij omzeilt namelijk alle toegangsregels.
    """

    def __init__(self, url: str | None = None, sleutel: str | None = None) -> None:
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.sleutel = sleutel or os.environ.get("SUPABASE_SERVICE_KEY", "")

        if not self.url or not self.sleutel:
            raise DatabaseFout(
                "SUPABASE_URL en SUPABASE_SERVICE_KEY moeten ingesteld zijn. "
                "Lokaal zet je die in een .env-bestand, online in de "
                "instellingen van GitHub."
            )

        self.sessie = requests.Session()
        self.sessie.headers.update({
            "apikey": self.sleutel,
            "Authorization": f"Bearer {self.sleutel}",
            "Content-Type": "application/json",
        })

    # -- hulpmiddelen --------------------------------------------------------

    def _rest(self, methode: str, pad: str, **opties: Any) -> requests.Response:
        adres = f"{self.url}/rest/v1/{pad}"
        try:
            antwoord = self.sessie.request(methode, adres, timeout=_TIJDSLIMIET, **opties)
        except requests.RequestException as fout:
            raise DatabaseFout(f"Database niet bereikbaar ({pad}): {fout}") from fout

        if not antwoord.ok:
            raise DatabaseFout(
                f"Database gaf foutcode {antwoord.status_code} bij {methode} {pad}: "
                f"{antwoord.text[:300]}"
            )
        return antwoord

    # -- logboek -------------------------------------------------------------

    def start_ronde(self, winkel_id: int) -> tuple[int | None, str]:
        """
        Zet een regel in het logboek en geeft het startmoment terug.

        Dat moment is later nodig om te bepalen welke aanbiedingen niet meer
        voorkomen en dus opgeruimd mogen worden.
        """
        moment = datetime.now(timezone.utc).isoformat()
        try:
            antwoord = self._rest(
                "POST", "scan_logs",
                json={"winkel_id": winkel_id, "gestart_op": moment, "status": "bezig"},
                headers={"Prefer": "return=representation"},
            )
            return antwoord.json()[0]["id"], moment
        except (DatabaseFout, ValueError, KeyError, IndexError) as fout:
            # Een mislukt logboek mag het ophalen zelf niet tegenhouden.
            log.warning("Kon het logboek niet bijwerken: %s", fout)
            return None, moment

    def sluit_ronde(
        self, log_id: int | None, status: str, aantal: int, melding: str | None = None
    ) -> None:
        """Schrijft het resultaat van de ronde in het logboek."""
        if log_id is None:
            return
        try:
            self._rest(
                "PATCH", f"scan_logs?id=eq.{log_id}",
                json={
                    "klaar_op": datetime.now(timezone.utc).isoformat(),
                    "status": status,
                    "aantal": aantal,
                    "melding": (melding or "")[:1000] or None,
                },
                headers={"Prefer": "return=minimal"},
            )
        except DatabaseFout as fout:
            log.warning("Kon het logboek niet afsluiten: %s", fout)

    # -- aanbiedingen --------------------------------------------------------

    def schrijf(self, aanbiedingen: list[Aanbieding], moment: str) -> int:
        """
        Schrijft de aanbiedingen weg; bestaande regels worden bijgewerkt.

        Alles krijgt hetzelfde ophaalmoment mee, zodat daarna precies te bepalen
        is wat níet meer voorkomt.
        """
        weggeschreven = 0

        for start in range(0, len(aanbiedingen), _BLOKGROOTTE):
            blok = aanbiedingen[start:start + _BLOKGROOTTE]
            rijen = []
            for aanbieding in blok:
                rij = aanbieding.als_rij()
                rij["opgehaald_op"] = moment
                rijen.append(rij)

            self._rest(
                "POST", "aanbiedingen?on_conflict=winkel_id,bron_id",
                json=rijen,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            weggeschreven += len(rijen)
            log.info("  %s van %s aanbiedingen weggeschreven.", weggeschreven, len(aanbiedingen))

        return weggeschreven

    def ruim_oude_op(self, winkel_id: int, moment: str) -> None:
        """
        Wist de aanbiedingen van deze winkel die in deze ronde niet terugkwamen.

        Dit gebeurt bewust pas ná het wegschrijven: mislukt het ophalen 's
        ochtends, dan blijft de lijst van gisteren staan in plaats van dat de
        website een dag leeg is.
        """
        # Het moment gaat als parameter mee en niet in het adres zelf: een
        # tijdstip bevat een plusteken, en dat betekent in een webadres "spatie".
        self._rest(
            "DELETE", "aanbiedingen",
            params={
                "winkel_id": f"eq.{winkel_id}",
                "opgehaald_op": f"lt.{moment}",
            },
            headers={"Prefer": "return=minimal"},
        )
        log.info("  Aanbiedingen van vóór deze ronde opgeruimd.")

    # -- productgroepen ------------------------------------------------------

    def bewaar_groepen(self, winkel_id: int, groepen: list[str]) -> int:
        """
        Zet de winkelindeling van deze winkel in de blijvende groepenlijst.

        Hier komt de volledige indeling van de winkel binnen — het hele
        assortiment dus, niet alleen wat er deze week in de bonus ligt. Daardoor
        is elke groep aan te vinken als zoekvraag, ook eentje die nog nooit in de
        aanbieding heeft gezeten. Precies waar een zoekvraag voor bedoeld is.

        De lijst wordt niet alleen aangevuld maar ook opgeschoond: deelt een
        winkel zijn assortiment anders in, dan horen de oude groepsnamen te
        verdwijnen. De database weigert dat opschonen als de nieuwe lijst
        verdacht kort is, zodat een half mislukte ronde de keuzelijst niet
        leeghaalt.

        Lukt dit niet, dan is dat vervelend maar niet fataal: de aanbiedingen
        zelf staan er dan al in. De ronde gaat dus gewoon door.
        """
        if not groepen:
            log.info("  Geen productgroepen om te bewaren.")
            return 0

        try:
            antwoord = self._rest(
                "POST", "rpc/vervang_productgroepen",
                json={"p_winkel_id": winkel_id, "p_groepen": groepen},
            )
            uitslag = (antwoord.json() or [{}])[0]
        except (DatabaseFout, ValueError, IndexError) as fout:
            log.warning("Kon de groepenlijst niet bijwerken: %s", fout)
            return 0

        log.info(
            "  Groepenlijst bijgewerkt: %s nieuw, %s vervallen, %s ongewijzigd.",
            uitslag.get("toegevoegd", 0), uitslag.get("verwijderd", 0),
            uitslag.get("behouden", 0),
        )
        return len(groepen)

    def aantal_aanbiedingen(self, winkel_id: int) -> int:
        """Hoeveel aanbiedingen er nu voor deze winkel in de database staan."""
        antwoord = self._rest(
            "GET", f"aanbiedingen?winkel_id=eq.{winkel_id}&select=id",
            headers={"Prefer": "count=exact", "Range": "0-0"},
        )
        bereik = antwoord.headers.get("Content-Range", "")
        try:
            return int(bereik.split("/")[-1])
        except (ValueError, IndexError):
            return 0
