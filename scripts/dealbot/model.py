"""
===============================================================================
 Dealbot — gemeenschappelijke vorm van een aanbieding

 Versie      : 1.0
 Reden       : Elke winkel levert zijn gegevens anders aan. Door alles eerst naar
               dezelfde vorm te vertalen, hoeft de rest van het programma niets
               te weten over de bron.
 Datum       : 27-07-2026 21:04

 Onderdelen:
   Aanbieding      - één aanbieding zoals die in de database terechtkomt
   maak_aanbieding - vult de kiloprijs en de groepeersleutel automatisch aan
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalisatie import effectieve_prijs, lees_inhoud, prijs_per_eenheid, product_sleutel


@dataclass
class Aanbieding:
    winkel_id: int
    bron_id: str
    product_naam: str
    merk: str | None = None
    variant: str | None = None
    actie_tekst: str | None = None
    prijs: float | None = None
    normale_prijs: float | None = None
    inhoud_waarde: float | None = None
    inhoud_eenheid: str | None = None
    prijs_per_eenheid: float | None = None
    eenheid_norm: str | None = None
    product_sleutel: str = ""
    geldig_van: str | None = None
    geldig_tot: str | None = None
    product_url: str | None = None
    afbeelding_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def als_rij(self) -> dict[str, Any]:
        """De aanbieding als regel voor de database."""
        return {
            "winkel_id": self.winkel_id,
            "bron_id": self.bron_id,
            "product_naam": self.product_naam,
            "merk": self.merk,
            "variant": self.variant,
            "actie_tekst": self.actie_tekst,
            "prijs": self.prijs,
            "normale_prijs": self.normale_prijs,
            "inhoud_waarde": self.inhoud_waarde,
            "inhoud_eenheid": self.inhoud_eenheid,
            "prijs_per_eenheid": self.prijs_per_eenheid,
            "eenheid_norm": self.eenheid_norm,
            "product_sleutel": self.product_sleutel,
            "geldig_van": self.geldig_van,
            "geldig_tot": self.geldig_tot,
            "product_url": self.product_url,
            "afbeelding_url": self.afbeelding_url,
        }


def maak_aanbieding(
    *,
    winkel_id: int,
    bron_id: str,
    product_naam: str,
    merk: str | None = None,
    variant: str | None = None,
    actie_tekst: str | None = None,
    actieprijs: float | None = None,
    normale_prijs: float | None = None,
    inhoud_tekst: str | None = None,
    geldig_van: str | None = None,
    geldig_tot: str | None = None,
    product_url: str | None = None,
    afbeelding_url: str | None = None,
) -> Aanbieding:
    """
    Maakt een aanbieding en rekent daarbij zelf de kiloprijs uit.

    Lukt dat niet — bijvoorbeeld bij "per bosje" — dan blijft de kiloprijs leeg.
    De aanbieding verdwijnt daarmee niet, maar zakt naar onderen in de lijst.
    """
    inhoud = lees_inhoud(inhoud_tekst)
    prijs = effectieve_prijs(actie_tekst, actieprijs, normale_prijs)

    return Aanbieding(
        winkel_id=winkel_id,
        bron_id=str(bron_id),
        product_naam=product_naam.strip(),
        merk=(merk or None),
        variant=(variant or None),
        actie_tekst=(actie_tekst or None),
        prijs=prijs,
        normale_prijs=normale_prijs,
        inhoud_waarde=inhoud.waarde if inhoud else None,
        inhoud_eenheid=inhoud.eenheid if inhoud else None,
        prijs_per_eenheid=prijs_per_eenheid(prijs, inhoud) if inhoud else None,
        eenheid_norm=inhoud.norm_eenheid if inhoud else None,
        product_sleutel=product_sleutel(merk, product_naam),
        geldig_van=geldig_van,
        geldig_tot=geldig_tot,
        product_url=product_url,
        afbeelding_url=afbeelding_url,
    )
