"""
===============================================================================
 Dealbot — verkeer met de database (Supabase)

 Versie      : 1.6
 Reden       : Dealbot krijgt een eigen productindeling van twee lagen, los van
               wat de winkels zelf hanteren. Daar hoort verkeer bij: de indeling
               wegschrijven, het vertaalboekje van winkelgroepen lezen en
               bijwerken, en de groepsnamen ophalen die nog vertaald moeten
               worden.
 Datum       : 03-08-2026 22:50

 Onderdelen:
   Database.start_ronde()             - logboekregel, en geeft het moment terug
   Database.schrijf()                 - schrijft de aanbiedingen weg in blokken
   Database.ruim_oude_op()            - wist wat niet in deze ronde is ververst
   Database.schrijf_standaardprijzen()- idem, voor het gewone schap
   Database.ruim_oude_prijzen_op()    - idem
   Database.bewaar_groepen()          - zet de winkelindeling in de vaste lijst
   Database.folder_al_gelezen()       - staat deze folderuitgave er al in?
   Database.sluit_ronde()             - schrijft het resultaat in het logboek

   Database.winkels()                 - de winkels met hun naam
   Database.winkelgroepen()           - de groepsnamen van de winkels zelf
   Database.bewaar_eigen_indeling()   - onze eigen indeling wegschrijven
   Database.koppelingen()             - het vertaalboekje, per winkel
   Database.bewaar_koppelingen()      - vertalingen toevoegen of bijwerken
===============================================================================
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests

from .model import Aanbieding, Standaardprijs

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

    # -- standaardprijzen ----------------------------------------------------

    def schrijf_standaardprijzen(self, producten: list[Standaardprijs], moment: str) -> int:
        """
        Schrijft het gewone schap weg; bestaande regels worden bijgewerkt.

        Gaat net als bij de aanbiedingen in blokken, met hetzelfde ophaalmoment
        voor alles, zodat daarna precies te bepalen is welke producten de winkel
        niet meer voert.
        """
        weggeschreven = 0

        for start in range(0, len(producten), _BLOKGROOTTE):
            blok = producten[start:start + _BLOKGROOTTE]
            rijen = []
            for product in blok:
                rij = product.als_rij()
                rij["opgehaald_op"] = moment
                rijen.append(rij)

            self._rest(
                "POST", "standaardprijzen?on_conflict=winkel_id,bron_id",
                json=rijen,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            weggeschreven += len(rijen)
            log.info("  %s van %s producten weggeschreven.", weggeschreven, len(producten))

        return weggeschreven

    def ruim_oude_prijzen_op(self, winkel_id: int, moment: str) -> None:
        """
        Wist de producten van deze winkel die in deze ronde niet terugkwamen.

        Net als bij de aanbiedingen bewust pas ná het wegschrijven: mislukt het
        ophalen, dan blijft de lijst van gisteren staan in plaats van dat de
        pagina leeg is.
        """
        self._rest(
            "DELETE", "standaardprijzen",
            params={
                "winkel_id": f"eq.{winkel_id}",
                "opgehaald_op": f"lt.{moment}",
            },
            headers={"Prefer": "return=minimal"},
        )
        log.info("  Producten van vóór deze ronde opgeruimd.")

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

    def folder_al_gelezen(self, winkel_id: int, voorvoegsel: str) -> bool:
        """
        Staat deze folder al in de database?

        Een folder uitlezen kost tientallen AI-vragen, en die zijn per dag
        beperkt. De folder verandert maar één keer per week, dus als de uitgave
        die nu op de site hangt er al in staat, hoeft hij niet nog een keer
        gelezen te worden. Elke regel draagt de folder waar hij uit komt in zijn
        bron_id, dus daar is het aan te zien.

        Bij twijfel (de database antwoordt niet) zeggen we "nee": een folder een
        keer te veel lezen is minder erg dan een week zonder aanbiedingen.
        """
        try:
            antwoord = self._rest(
                "GET", "aanbiedingen",
                params={
                    "winkel_id": f"eq.{winkel_id}",
                    "bron_id": f"like.{voorvoegsel}%",
                    "select": "id",
                    "limit": "1",
                },
            )
            return bool(antwoord.json())
        except (DatabaseFout, ValueError) as fout:
            log.warning("Kon niet nagaan of de folder al ingelezen is: %s", fout)
            return False

    # -- eigen indeling ------------------------------------------------------

    def _alles(self, pad: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """
        Haalt een hele tabel op, in blokken.

        De database geeft hooguit 1000 regels per keer terug. Bij 2606
        groepsnamen zou je zonder deze lus dus stilzwijgend twee derde missen —
        precies het soort fout dat pas weken later opvalt.
        """
        alles: list[dict[str, Any]] = []
        sprong = 1000
        offset = 0

        while True:
            opties = dict(params or {})
            opties.update({"limit": str(sprong), "offset": str(offset)})
            blok = self._rest("GET", pad, params=opties).json()
            alles.extend(blok)
            if len(blok) < sprong:
                return alles
            offset += sprong

    def winkels(self) -> dict[int, str]:
        """De winkels met hun naam, om leesbaar te kunnen melden wat er gebeurt."""
        rijen = self._rest("GET", "winkels", params={"select": "id,naam"}).json()
        return {rij["id"]: rij["naam"] for rij in rijen}

    def winkelgroepen(self, winkel_id: int | None = None) -> list[dict[str, Any]]:
        """
        De groepsnamen zoals de winkels ze zelf hanteren.

        Dit is de lijst die vertaald moet worden naar onze eigen indeling. Hij
        komt uit het hele assortiment van elke winkel, niet alleen uit wat er
        deze week in de bonus ligt.
        """
        params = {"select": "winkel_id,productgroep", "order": "winkel_id,productgroep"}
        if winkel_id is not None:
            params["winkel_id"] = f"eq.{winkel_id}"
        return self._alles("bekende_productgroepen", params)

    def bewaar_eigen_indeling(self, regels: list[dict[str, Any]]) -> int:
        """
        Zet onze eigen indeling in de database.

        De indeling zelf staat in indeling.py — dat is de enige plek waar hij
        wordt onderhouden. Hier komt hij terecht zodat de website dezelfde
        keuzelijst kan tonen als waarmee het ophaalscript indeelt.
        """
        if not regels:
            return 0

        self._rest(
            "POST", "eigen_groepen?on_conflict=hoofdgroep,subgroep",
            json=regels,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        log.info("  Eigen indeling bijgewerkt: %s subgroepen.", len(regels))
        return len(regels)

    def koppelingen(self, winkel_id: int | None = None) -> list[dict[str, Any]]:
        """Het vertaalboekje: welke winkelgroep hangt onder welke eigen groep."""
        params = {"select": "winkel_id,productgroep,hoofdgroep,subgroep,gemengd,herkomst"}
        if winkel_id is not None:
            params["winkel_id"] = f"eq.{winkel_id}"
        return self._alles("groep_koppelingen", params)

    def bewaar_koppelingen(self, koppelingen: list[dict[str, Any]]) -> int:
        """
        Schrijft vertalingen weg; bestaande regels worden bijgewerkt.

        Gaat in blokken, net als de aanbiedingen. Wat met de hand verbeterd is
        (herkomst 'hand') hoort niet overschreven te worden — dat filtert de
        aanroeper eruit, want alleen die weet wat er nu in de database staat.
        """
        weggeschreven = 0

        for start in range(0, len(koppelingen), _BLOKGROOTTE):
            blok = koppelingen[start:start + _BLOKGROOTTE]
            for rij in blok:
                rij["gewijzigd_op"] = datetime.now(timezone.utc).isoformat()

            self._rest(
                "POST", "groep_koppelingen?on_conflict=winkel_id,productgroep",
                json=blok,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            weggeschreven += len(blok)

        log.info("  %s koppelingen weggeschreven.", weggeschreven)
        return weggeschreven

    def aanbiedingen_ruw(
        self,
        velden: str = "id,winkel_id,product_naam,productgroep,hoofdgroep,subgroep",
    ) -> list[dict[str, Any]]:
        """Alle aanbiedingen die er nu staan, om ze opnieuw in te kunnen delen."""
        return self._alles("aanbiedingen", {"select": velden, "order": "id"})

    def zet_eigen_groepen(self, regels: list[dict[str, Any]]) -> int:
        """
        Zet bij bestaande aanbiedingen onze hoofd- en subgroep.

        Wordt gebruikt om in één keer alles opnieuw in te delen nadat het
        vertaalboekje is bijgewerkt, zonder eerst een hele ophaalronde te hoeven
        draaien.

        Het bijwerken gaat per groep en niet per aanbieding. Dat scheelt enorm:
        duizenden aanbiedingen krijgen dezelfde twee waarden, dus één opdracht
        met een lijst nummers volstaat. Die lijst gaat in stukken, want een
        webadres mag niet eindeloos lang worden.
        """
        per_groep: dict[tuple[str | None, str | None], list[int]] = {}
        for regel in regels:
            sleutel = (regel.get("hoofdgroep"), regel.get("subgroep"))
            per_groep.setdefault(sleutel, []).append(regel["id"])

        bijgewerkt = 0
        for (hoofdgroep, subgroep), nummers in per_groep.items():
            for start in range(0, len(nummers), _BLOKGROOTTE):
                blok = nummers[start:start + _BLOKGROOTTE]
                self._rest(
                    "PATCH", "aanbiedingen",
                    params={"id": f"in.({','.join(str(n) for n in blok)})"},
                    json={"hoofdgroep": hoofdgroep, "subgroep": subgroep},
                    headers={"Prefer": "return=minimal"},
                )
                bijgewerkt += len(blok)

            log.info("  %s / %s: %s aanbiedingen.",
                     hoofdgroep or "(uit de indeling gehaald)",
                     subgroep or "(alleen de afdeling)", len(nummers))

        return bijgewerkt

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
