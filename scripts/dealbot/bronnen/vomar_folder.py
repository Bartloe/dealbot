"""
===============================================================================
 Dealbot — de aanbiedingen van Vomar uit de weekfolder

 Versie      : 1.0
 Reden       : Vomar publiceert zijn aanbiedingen nergens als lijst, alleen als
               digitale folder. Die folder blijkt wél automatisch op te halen:
               vomar.nl toont hem via Publitas, en daar is de folder als PDF te
               downloaden. Wat er in staat laten we aflezen door de AI-lezer.
 Datum       : 03-08-2026 00:20

 Welke folder is de juiste? Vomar heeft twee vaste ingangen die altijd naar de
 nieuwste uitgave wijzen: "folder deze week" en "folder volgende week". Wij
 volgen "deze week"; dat is per definitie de folder die nu in de winkel geldt.
 De folder van volgende week staat er lang niet altijd (op zondag 2 augustus
 bijvoorbeeld niet), dus die is een keuze en geen vanzelfsprekendheid.

 Let op de weeknummers: op zondag 2 augustus 2026 stond in "deze week" al de
 folder met "week 32" in de titel, met acties van zondag 2 t/m zaterdag 8
 augustus. De folderweek van Vomar loopt dus van zondag tot en met zaterdag en
 begint een dag eerder dan de kalenderweek. Die periode lezen we bij voorkeur
 gewoon van de omslag af; het weeknummer is alleen de terugval.

 Onderdelen:
   zoek_folder()   - welke folder hangt er nu, en waar staat de PDF
   haal_pdf()      - de folder als PDF binnenhalen
   haal_op()       - het geheel: folder zoeken, laten aflezen, aanbiedingen terug
   _periode()      - de week van zondag tot en met zaterdag als terugval
===============================================================================
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta

import requests

from ..folderlezer import lees_folder
from ..model import Oogst

log = logging.getLogger(__name__)

WINKEL_ID = 5
WINKEL_NAAM = "Vomar"

# De vaste ingangen van Vomar. Deze adressen veranderen niet; er hangt elke week
# een nieuwe uitgave achter.
KANALEN = {
    "deze-week": "https://view.publitas.com/folder-deze-week",
    "volgende-week": "https://view.publitas.com/folder-volgende-week",
}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

_PDF_IN_PAGINA = re.compile(r'"downloadPdfUrl"\s*:\s*"(https://[^"]+)"')
_WEEK_IN_TITEL = re.compile(r"week\s*(\d{1,2})", re.IGNORECASE)
_TITEL = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class FolderFout(RuntimeError):
    """De folder van Vomar is niet op te halen."""


@dataclass
class Folderinfo:
    """Welke folder er nu hangt en waar de PDF vandaan komt."""

    titel: str
    folder_url: str
    pdf_url: str
    week: int | None = None

    @property
    def voorvoegsel(self) -> str:
        """
        Waaraan de aanbiedingen uit déze uitgave te herkennen zijn.

        Het staat vooraan in het bron_id van elke regel, zodat naderhand te zien
        is uit welke folder een aanbieding komt — en dus of een folder al eens
        gelezen is.
        """
        return f"folder-{self.week or 'x'}"


def zoek_folder(welke: str = "deze-week") -> Folderinfo:
    """
    Zoekt op welke folder er nu achter de vaste ingang van Vomar hangt.

    Staat er niets (de folder van volgende week is vaak nog niet klaar), dan is
    dat geen storing maar gewoon een mededeling — de aanroeper mag beslissen wat
    hij daarmee doet.
    """
    ingang = KANALEN.get(welke)
    if not ingang:
        raise FolderFout(f"Onbekende folder gevraagd: {welke!r}. "
                         f"Kies uit: {', '.join(KANALEN)}.")

    try:
        antwoord = requests.get(ingang, headers={"User-Agent": _USER_AGENT},
                                timeout=60, allow_redirects=True)
    except requests.RequestException as fout:
        raise FolderFout(f"Kon de folderpagina van Vomar niet bereiken: {fout}") from fout

    if antwoord.status_code == 404:
        raise FolderFout(f"Vomar heeft nu geen folder voor '{welke.replace('-', ' ')}' "
                         f"klaarstaan.")
    if not antwoord.ok:
        raise FolderFout(f"De folderpagina van Vomar gaf foutcode {antwoord.status_code}.")

    pagina = antwoord.text
    pdf = _PDF_IN_PAGINA.search(pagina)
    if not pdf:
        raise FolderFout("Op de folderpagina van Vomar staat geen te downloaden PDF meer; "
                         "de opzet van Publitas is kennelijk veranderd.")

    titel_stuk = _TITEL.search(pagina)
    titel = (titel_stuk.group(1).strip() if titel_stuk else "").replace(" - Pagina 1", "")
    week_stuk = _WEEK_IN_TITEL.search(titel)

    return Folderinfo(
        titel=titel or "folder",
        folder_url=antwoord.url,
        pdf_url=pdf.group(1).encode().decode("unicode_escape"),
        week=int(week_stuk.group(1)) if week_stuk else None,
    )


def haal_pdf(folder: Folderinfo) -> bytes:
    """Haalt de folder als PDF binnen. Dat is één bestand van zo'n 25 MB."""
    try:
        antwoord = requests.get(folder.pdf_url, headers={"User-Agent": _USER_AGENT},
                                timeout=180)
        antwoord.raise_for_status()
    except requests.RequestException as fout:
        raise FolderFout(f"Kon de folder-PDF van Vomar niet ophalen: {fout}") from fout

    if not antwoord.content.startswith(b"%PDF"):
        raise FolderFout("Wat Vomar terugstuurde is geen PDF.")

    log.info("%s: folder '%s' opgehaald (%.1f MB).",
             WINKEL_NAAM, folder.titel, len(antwoord.content) / 1_000_000)
    return antwoord.content


def haal_op(welke: str = "deze-week", *, folder: Folderinfo | None = None,
            laatste_pagina: int = 0) -> Oogst:
    """
    Haalt de aanbiedingen van Vomar uit de folder die nu geldt.

    Is er al opgezocht welke folder er hangt, geef die dan mee: dat scheelt een
    tweede bezoek aan de folderpagina.

    Met `laatste_pagina` is het lezen te beperken tot de eerste zoveel pagina's;
    handig om te proberen zonder de hele dagvoorraad AI-vragen op te maken.
    """
    folder = folder or zoek_folder(welke)
    log.info("%s: folder gevonden — %s (%s).", WINKEL_NAAM, folder.titel, folder.folder_url)

    pdf = haal_pdf(folder)
    oogst = lees_folder(
        pdf,
        winkel_id=WINKEL_ID,
        winkel_naam=WINKEL_NAAM,
        folder_url=folder.folder_url,
        bron_voorvoegsel=folder.voorvoegsel,
        laatste_pagina=laatste_pagina,
    )

    # Stond de periode nergens leesbaar op de pagina's, dan rekenen we hem uit
    # het weeknummer in de titel: zondag tot en met zaterdag.
    if folder.week and any(not a.geldig_van for a in oogst.aanbiedingen):
        van, tot = _periode(folder.week)
        log.info("%s: voor aanbiedingen zonder leesbare periode gerekend met week %s "
                 "(%s t/m %s).", WINKEL_NAAM, folder.week, van, tot)
        for aanbieding in oogst.aanbiedingen:
            if not aanbieding.geldig_van:
                aanbieding.geldig_van, aanbieding.geldig_tot = van, tot

    if oogst.fouten:
        log.warning("%s: %s van de %s pagina's zijn niet gelezen.",
                    WINKEL_NAAM, len(oogst.fouten), oogst.paginas)

    return Oogst(aanbiedingen=oogst.aanbiedingen, productgroepen=[])


def _periode(week: int, jaar: int | None = None) -> tuple[str, str]:
    """
    De folderweek van Vomar: van zondag tot en met zaterdag.

    De kalenderweek begint op maandag, de folderweek een dag eerder. Valt het
    weeknummer rond de jaarwisseling, dan telt het jaar van vandaag; dat scheelt
    een folder die een jaar de verkeerde kant op schiet.
    """
    jaar = jaar or date.today().year
    try:
        maandag = date.fromisocalendar(jaar, week, 1)
    except ValueError:
        maandag = date.today()
    zondag = maandag - timedelta(days=1)
    return zondag.isoformat(), (zondag + timedelta(days=6)).isoformat()
