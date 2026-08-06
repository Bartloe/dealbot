"""
===============================================================================
 Dealbot — alles onder onze eigen productindeling hangen

 Versie      : 2.3
 Reden       : Dit script kan voortaan meedraaien in de ochtendronde op GitHub,
               en daar mag het nooit een AI-vraag kosten. Met --zonder-ai wordt
               het vertalen overgeslagen en alleen het bestaande boekje
               toegepast: nieuwe aanbiedingen krijgen dan meteen hun plek in
               onze indeling, zonder de sleutels op te eten die de folderlezer
               diezelfde ochtend nodig heeft.

               Onbekende groepsnamen verdwijnen daarmee niet uit beeld. Ze
               worden geteld en gemeld, en dezelfde telling staat op de
               beheerpagina — dat is het sein om het vertalen met de hand te
               starten.
 Datum       : 06-08-2026 15:05

 Vorige      : Producten uit een grove winkelgroep vallen nu terug op de afdeling
               van die groep in plaats van te verdwijnen. Daarnaast kent het
               vertaalboekje een nieuw soort regel: de eigenschapgroep. Die heeft
               géén afdeling — bij "Glutenvrij" valt er niets te noemen — maar de
               producten tellen wel mee; daar beslist de productnaam.
 Datum       : 06-08-2026 01:25

 Vorige      : Een vertaalronde die halverwege stilviel — de dagvoorraad
               AI-vragen is op — kon alleen nog helemaal opnieuw of helemaal
               niet. Alles opnieuw gooit het werk van de vorige avond weg;
               zonder --opnieuw slaat hij alles over, want élke groep staat al
               in het boekje. Met --verder wordt de ronde hervat: overgeslagen
               wordt wat er in deze ronde al is bijgewerkt, gevraagd wordt de
               rest.
 Datum       : 06-08-2026 00:30

 Vorige      : De ketens spreken elk hun eigen taal: samen ruim tweeduizend
               groepsnamen waarmee je met één zoekvraag nooit alle winkels vond.
               Dit script legt het vertaalboekje aan (winkelgroep -> onze eigen
               groep) en deelt daarmee alles in.

               Het vertalen gebeurt één keer per groepsnaam en wordt bewaard.
               Een groepsnaam verandert immers niet elke week, en zo kost een
               gewone ophaalronde 's ochtends geen enkele AI-vraag.

               Nieuw is het kenmerk: de derde laag onder de lade. Onze lade
               Toiletpapier bevat het droge en het vochtige door elkaar, terwijl
               de winkels dat onderscheid in hun eigen groepsnaam allang maken.
               Dat woord wordt nu bewaard in onze taal, zodat je in je profiel
               alleen het vochtige kunt volgen — bij alle winkels tegelijk.

               Voor winkels die het onderscheid niet in hun groepsnaam maken,
               wordt het kenmerk uit de productnaam gevist, met de woorden die
               de lade van de ándere winkels heeft geleerd. Er wordt dus nergens
               een lijstje met de hand bijgehouden.
 Datum       : 05-08-2026 15:15

 Onderdelen:
   main()              - de drie stappen achter elkaar, met een samenvatting
   stap_indeling()     - onze eigen indeling naar de database
   stap_vertalen()     - onbekende winkelgroepen door de AI, resultaat bewaren
   tel_onvertaald()    - hoeveel groepsnamen nog buiten het boekje vallen
   stap_toepassen()    - aanbiedingen én standaardprijzen opnieuw indelen
   _lees_boekje()      - het vertaalboekje in de vorm die het indelen nodig heeft
   _deel_tabel_in()    - één tabel indelen; beide gaan langs dezelfde weg
   _plek_van()         - de plek van één product: winkelgroep, dan productnaam
   _kenmerk_van()      - de verbijzondering: winkelgroep, dan productnaam
   _verslag()          - wat het opgeleverd heeft, per tabel, winkel en groep
   _verslag_kenmerken()- welke kenmerken er onder de laden zijn komen hangen
   _grens_van()        - vanaf welk moment deze ronde al gedaan is
   _moment()           - het moment waarop een regel is bijgewerkt

 Uitvoeren:
   python scripts/indeel.py                alles: vertalen en toepassen
   python scripts/indeel.py --zonder-ai    niet vertalen, alleen het boekje
                                           toepassen (de ochtendronde doet dit)
   python scripts/indeel.py --proef        niets wegschrijven, alleen laten zien
   python scripts/indeel.py --opnieuw      ook al vertaalde groepen opnieuw vragen
   python scripts/indeel.py --verder       een afgebroken ronde hervatten
   python scripts/indeel.py --verder 05-08-2026
                                           idem, maar de ronde begon op die dag
   python scripts/indeel.py --woorden koffie,thee
                                           alleen groepsnamen met die woorden erin
===============================================================================
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dealbot import indeling as eigen  # noqa: E402
from dealbot.ai import Vraagbaak  # noqa: E402
from dealbot.database import Database, DatabaseFout  # noqa: E402
from dealbot.groepvertaler import Koppeling, vertaal  # noqa: E402
from dealbot.kenmerken import Woordenlijst, tel_per_lade  # noqa: E402

log = logging.getLogger("indeel")


def _lees_env() -> None:
    """Leest .env in, zodat de sleutels ook zonder GitHub beschikbaar zijn."""
    bestand = Path(__file__).resolve().parents[1] / ".env"
    if not bestand.exists():
        return
    for regel in bestand.read_text(encoding="utf-8").splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#") or "=" not in regel:
            continue
        naam, _, waarde = regel.partition("=")
        os.environ.setdefault(naam.strip(), waarde.strip())


# -----------------------------------------------------------------------------
# Stap 1 — onze eigen indeling naar de database.
# -----------------------------------------------------------------------------
def stap_indeling(db: Database, proef: bool) -> int:
    """
    Zet de indeling uit indeling.py in de database.

    De indeling wordt op één plek onderhouden — in de code — en hier alleen
    naartoe gekopieerd, zodat de website precies dezelfde keuzelijst toont als
    waarmee het ophaalscript indeelt.
    """
    regels = []
    for hoofd, subs in eigen.INDELING.items():
        for volgnummer, sub in enumerate(subs, start=1):
            regels.append({"hoofdgroep": hoofd, "subgroep": sub, "volgorde": volgnummer})

    log.info("Onze indeling: %s hoofdgroepen met %s subgroepen.",
             len(eigen.INDELING), len(regels))
    if proef:
        return len(regels)
    return db.bewaar_eigen_indeling(regels)


# -----------------------------------------------------------------------------
# Stap 2 — de winkelgroepen vertalen.
# -----------------------------------------------------------------------------
def _moment(waarde) -> datetime | None:
    """Leest het moment waarop een regel voor het laatst is bijgewerkt."""
    if not waarde:
        return None
    try:
        gelezen = datetime.fromisoformat(str(waarde).replace("Z", "+00:00"))
    except ValueError:
        return None
    # Een moment zonder tijdzone komt uit de database en is daar altijd UTC.
    return gelezen if gelezen.tzinfo else gelezen.replace(tzinfo=timezone.utc)


def _grens_van(bestaand: list[dict], verder: str) -> datetime | None:
    """
    Vanaf welk moment is het boekje al in deze ronde bijgewerkt?

    Nodig om een afgebroken vertaalronde te kunnen hervatten. Wat na dit moment
    is bijgewerkt, is al gevraagd en wordt overgeslagen; de rest gaat alsnog
    langs de AI.

    Zonder eigen datum wordt het moment afgeleid: een etmaal terug vanaf de
    laatst bijgewerkte regel. Dat is bewust geen kalenderdag — een ronde die om
    kwart voor twaalf 's avonds begint en na middernacht doorloopt, hoort één
    ronde te zijn en geen twee. Duurde het langer dan een etmaal, geef dan zelf
    een datum mee.
    """
    if verder and verder != "auto":
        for vorm in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                dag = datetime.strptime(verder, vorm)
            except ValueError:
                continue
            return dag.replace(tzinfo=ZoneInfo("Europe/Amsterdam"))
        raise ValueError(f"'{verder}' is geen datum. Schrijf hem als 05-08-2026.")

    momenten = [m for m in (_moment(rij.get("gewijzigd_op")) for rij in bestaand) if m]
    if not momenten:
        return None
    return max(momenten) - timedelta(hours=24)


def stap_vertalen(
    db: Database,
    proef: bool,
    opnieuw: bool,
    woorden: list[str],
    verder: str = "",
) -> tuple[list[Koppeling], list[str]]:
    """
    Hangt de nog onbekende groepsnamen van de winkels onder onze indeling.

    Standaard worden alleen groepen gevraagd die nog niet in het vertaalboekje
    staan. Dat houdt het goedkoop: de eerste keer kost het tientallen AI-vragen,
    daarna alleen nog de handvol groepen die een winkel nieuw invoert. Breekt een
    ronde halverwege af, dan pakt de volgende ronde precies op waar deze bleef.

    Wat met de hand is verbeterd blijft altijd staan, ook bij --opnieuw. Een mens
    die de moeite neemt een koppeling recht te zetten, hoort niet de volgende dag
    door de AI overruled te worden.

    Met "verder" wordt een afgebroken ronde hervat. Dan telt niet of een groep al
    in het boekje staat — dat doen ze allemaal — maar of hij in déze ronde al is
    bijgewerkt. Zo hoeven de vragen van gisteren niet nog eens gesteld te worden,
    terwijl de rest wel aan de beurt komt.
    """
    winkels = db.winkels()
    bestaand = db.koppelingen()
    met_de_hand = {
        (rij["winkel_id"], rij["productgroep"].lower())
        for rij in bestaand if rij.get("herkomst") == "hand"
    }
    al_bekend = {(rij["winkel_id"], rij["productgroep"].lower()) for rij in bestaand}

    grens = _grens_van(bestaand, verder) if verder else None
    al_gedaan: set[tuple[int, str]] = set()
    if grens:
        al_gedaan = {
            (rij["winkel_id"], rij["productgroep"].lower())
            for rij in bestaand
            if (moment := _moment(rij.get("gewijzigd_op"))) and moment >= grens
        }
        log.info("Verder waar de vorige ronde bleef: %s van de %s groepen zijn "
                 "sinds %s bijgewerkt en worden overgeslagen.",
                 len(al_gedaan), len(bestaand),
                 grens.astimezone(ZoneInfo("Europe/Amsterdam")).strftime("%d-%m-%Y %H:%M"))

    te_doen: dict[int, list[str]] = {}
    for rij in db.winkelgroepen():
        winkel_id, naam = rij["winkel_id"], rij["productgroep"]
        sleutel = (winkel_id, naam.lower())

        if sleutel in met_de_hand:
            continue
        if grens:
            if sleutel in al_gedaan:
                continue
        elif sleutel in al_bekend and not opnieuw:
            continue
        if woorden and not any(woord in eigen.schoon(naam) for woord in woorden):
            continue
        te_doen.setdefault(winkel_id, []).append(naam)

    totaal = sum(len(lijst) for lijst in te_doen.values())
    if not totaal:
        log.info("Alle winkelgroepen staan al in het vertaalboekje.")
        return [], []

    vragen = sum(-(-len(lijst) // 60) for lijst in te_doen.values())
    log.info("%s groepsnamen te vertalen in ongeveer %s AI-vragen.", totaal, vragen)

    vraagbaak = Vraagbaak()
    kan, reden = vraagbaak.beschikbaar()
    if not kan:
        log.error("Vertalen kan niet: %s.", reden)
        return [], [reden]

    # Elk blok gaat meteen naar de database. Een AI-vraag is schaars — de
    # dagvoorraad is beperkt — dus een storing halverwege mag nooit het al
    # gedane werk meenemen.
    def bewaar(koppelingen: list[Koppeling]) -> None:
        db.bewaar_koppelingen([k.als_rij() for k in koppelingen])

    # Eén woordenlijst voor álle winkels, gevuld met wat er al bekend is. Zo
    # krijgt de tweede keten de kenmerken van de eerste te zien en levert
    # "Toiletpapier - vochtig" hetzelfde woord op als "vochtig toiletpapier".
    woordenlijst = Woordenlijst.van_koppelingen(bestaand)

    alles: list[Koppeling] = []
    klachten: list[str] = []
    for winkel_id, lijst in sorted(te_doen.items()):
        naam = winkels.get(winkel_id, str(winkel_id))
        log.info("%s: %s groepsnamen.", naam, len(lijst))
        koppelingen, fouten = vertaal(
            vraagbaak, winkel_id, lijst, naam, bewaar=None if proef else bewaar,
            woordenlijst=woordenlijst,
        )
        alles.extend(koppelingen)
        klachten.extend(fouten)

    raak = sum(1 for k in alles if k.hoofdgroep)
    eigenschap = sum(1 for k in alles if k.eigenschapgroep)
    met_kenmerk = sum(1 for k in alles if k.kenmerk)
    log.info("%s van de %s bekeken groepsnamen kregen een afdeling, %s met een "
             "kenmerk. %s zijn eigenschapgroepen zonder afdeling (daar beslist de "
             "productnaam) en %s gaan over andere boodschappen. "
             "%s AI-vragen, %s tokens.",
             raak, len(alles), met_kenmerk, eigenschap,
             len(alles) - raak - eigenschap, vraagbaak.aanroepen, vraagbaak.tokens)

    return alles, klachten


def tel_onvertaald(db: Database) -> dict[int, int]:
    """
    Hoeveel groepsnamen staan er nog niet in het vertaalboekje, per winkel?

    Dit is de tegenhanger van het vertalen voor de ochtendronde: die mag geen
    AI-vraag stellen, maar mag het ook niet stilzwijgend laten liggen. Een
    nieuwe winkel brengt in één klap een paar honderd onbekende groepsnamen mee,
    en zolang die niet vertaald zijn hangen zijn producten nergens onder.

    Alleen tellen dus, en melden. Dezelfde telling staat op de beheerpagina;
    daar is het sein om `python scripts/indeel.py` met de hand te draaien.
    """
    bekend = {(rij["winkel_id"], rij["productgroep"].lower())
              for rij in db.koppelingen()}

    open_per_winkel: Counter = Counter()
    for rij in db.winkelgroepen():
        if (rij["winkel_id"], rij["productgroep"].lower()) not in bekend:
            open_per_winkel[rij["winkel_id"]] += 1

    if not open_per_winkel:
        log.info("Vertalen overgeslagen; alle winkelgroepen staan al in het boekje.")
        return {}

    winkels = db.winkels()
    totaal = sum(open_per_winkel.values())
    log.warning(
        "Vertalen overgeslagen, maar %s staat nog buiten het boekje: %s. "
        "Die producten blijven zonder plek tot 'python scripts/indeel.py' draait.",
        "1 groepsnaam" if totaal == 1 else f"{totaal} groepsnamen",
        ", ".join(f"{winkels.get(w, w)} {a}"
                  for w, a in sorted(open_per_winkel.items(), key=lambda p: -p[1])),
    )
    return dict(open_per_winkel)


# -----------------------------------------------------------------------------
# Stap 3 — alle aanbiedingen indelen.
# -----------------------------------------------------------------------------
class Boekjeregel(NamedTuple):
    """
    Wat het vertaalboekje over één winkelgroep zegt.

    Bij een eigenschapgroep ("Glutenvrij", "Kerst") is de hoofdgroep leeg. Dat
    hoort zo: die producten liggen door de hele winkel en er valt geen afdeling
    over te zeggen.
    """

    hoofdgroep: str | None
    subgroep: str | None
    eigenschapgroep: bool
    kenmerk: str | None


def _plek_van(
    regel: dict,
    boekje: dict[tuple[int, str], Boekjeregel],
) -> eigen.Plek | None:
    """
    Waar hoort dit product? Eerst het vertaalboekje, dan de productnaam.

    De winkelgroep is leidend voor de hoofdgroep — een winkel legt zijn eigen
    product in zijn eigen schap, dus dat klopt vrijwel altijd. Alleen de fijne
    plek ontbreekt bij een grove indeling, en die mag de productnaam aanvullen.

    Of de winkel überhaupt een groep meelevert gaat apart mee. Dat is namelijk
    iets anders dan een groep die niet onder onze indeling valt: in dat tweede
    geval heeft de winkel al gezegd wat voor product het is.
    """
    winkelgroep = eigen.schoon(regel.get("productgroep"))
    uit_boekje = boekje.get((regel["winkel_id"], winkelgroep)) if winkelgroep else None

    uit_winkelgroep = None
    if uit_boekje and uit_boekje.hoofdgroep:
        uit_winkelgroep = eigen.Plek(uit_boekje.hoofdgroep, uit_boekje.subgroep,
                                     herkomst="winkelgroep")

    return eigen.plaats(
        regel.get("product_naam"),
        uit_winkelgroep,
        winkel_heeft_groep=bool(winkelgroep),
        eigenschapgroep=bool(uit_boekje and uit_boekje.eigenschapgroep),
    )


def _kenmerk_van(
    regel: dict,
    plek: eigen.Plek | None,
    uit_boekje: Boekjeregel | None,
    woordenlijst: Woordenlijst,
) -> str | None:
    """
    Wat verbijzondert dit product binnen zijn lade?

    Twee wegen, in deze volgorde. Eerst de winkelgroep: heeft de winkel het
    onderscheid zelf gemaakt ("Toiletpapier Vochtig"), dan staat het kenmerk al
    in het vertaalboekje en is dat het zekerste antwoord.

    Zo niet, dan de productnaam. Dat is het vangnet voor de winkels die alles
    "Toiletpapier" noemen terwijl op het pak wel degelijk "vochtig" staat. Er
    wordt daarbij uitsluitend gezocht naar kenmerken die deze lade al kent van
    een andere winkel — nooit naar iets zelfbedachts.

    Zonder lade geen kenmerk. "Vochtig" bestaat bij het toiletpapier én bij de
    doekjes, dus zonder te weten in welke lade het product ligt zegt het niets.
    """
    if plek is None or not plek.subgroep:
        return None

    # Het kenmerk uit het boekje geldt alleen als het product ook werkelijk in
    # de lade beland is waar dat kenmerk bij hoort. Bij een grove winkelgroep
    # heeft de productnaam de lade bepaald en kan dat een andere zijn.
    if uit_boekje and uit_boekje.kenmerk and uit_boekje.subgroep == plek.subgroep:
        return uit_boekje.kenmerk

    return woordenlijst.uit_naam(plek.hoofdgroep, plek.subgroep,
                                 regel.get("product_naam"))


def _lees_boekje(db: Database) -> tuple[dict[tuple[int, str], Boekjeregel], Woordenlijst]:
    """
    Het vertaalboekje in de vorm waarin het indelen het nodig heeft.

    Regels zonder hoofdgroep horen bewust niet in het boekje: die zeggen "deze
    winkelgroep hoort nergens bij ons". Ze staan er alleen zodat de AI er niet
    nog eens naar gevraagd wordt.

    Op één na: een eigenschapgroep heeft ook geen hoofdgroep maar moet wél mee.
    Daar zegt de lege hoofdgroep niet "hoort er niet bij" maar "er valt geen
    afdeling over te zeggen — kijk naar de productnaam".

    De woordenlijst komt uit datzelfde boekje: alle kenmerken die de winkels
    samen hebben opgeleverd, gesorteerd per lade. Dat is de woordenschat waarmee
    straks de productnamen worden afgezocht.
    """
    alle_regels = db.koppelingen()
    boekje = {
        (rij["winkel_id"], eigen.schoon(rij["productgroep"])):
            Boekjeregel(rij.get("hoofdgroep"), rij.get("subgroep"),
                        bool(rij.get("eigenschapgroep")), rij.get("kenmerk"))
        for rij in alle_regels
        if rij.get("hoofdgroep") or rij.get("eigenschapgroep")
    }
    eigenschap = sum(1 for rij in alle_regels if rij.get("eigenschapgroep"))
    afgevallen = sum(1 for rij in alle_regels
                     if not rij.get("hoofdgroep") and not rij.get("eigenschapgroep"))
    log.info("Vertaalboekje: %s winkelgroepen onder onze indeling, "
             "%s eigenschapgroepen waar de productnaam beslist, "
             "%s bekeken en afgevallen.",
             len(alle_regels) - afgevallen - eigenschap, eigenschap, afgevallen)

    woordenlijst = Woordenlijst.van_koppelingen(alle_regels)
    laden = woordenlijst.laden()
    log.info("Kenmerken: %s laden hebben er samen %s.",
             len(laden), sum(len(woordenlijst.bekend(h, s)) for h, s in laden))
    return boekje, woordenlijst


def _deel_tabel_in(
    db: Database,
    tabel: str,
    naam: str,
    boekje: dict[tuple[int, str], Boekjeregel],
    woordenlijst: Woordenlijst,
    proef: bool,
) -> tuple[list[dict], Counter, Counter]:
    """
    Deelt alles in één tabel in volgens het vertaalboekje.

    Aanbiedingen en standaardprijzen gaan langs precies dezelfde weg: allebei
    hebben ze een winkel, een productnaam en de groep van de winkel zelf, en
    allebei hangen ze onder dezelfde eigen indeling.
    """
    producten = db.producten_ruw(tabel)
    log.info("%s %s om in te delen.", len(producten), naam)

    ingedeeld: list[dict] = []
    bijwerken: list[dict] = []
    per_winkel: Counter = Counter()
    per_groep: Counter = Counter()

    for product in producten:
        winkelgroep = eigen.schoon(product.get("productgroep"))
        uit_boekje = boekje.get((product["winkel_id"], winkelgroep)) if winkelgroep else None

        plek = _plek_van(product, boekje)
        hoofdgroep = plek.hoofdgroep if plek else None
        subgroep = plek.subgroep if plek else None
        kenmerk = _kenmerk_van(product, plek, uit_boekje, woordenlijst)

        # Alleen wegschrijven wat werkelijk verandert. Een verbeterd
        # vertaalboekje raakt meestal een handvol groepen; dan hoeven er geen
        # duizenden ongewijzigde regels langs de database.
        if (hoofdgroep, subgroep, kenmerk) != (product.get("hoofdgroep"),
                                               product.get("subgroep"),
                                               product.get("kenmerk")):
            bijwerken.append({
                "id": product["id"],
                "hoofdgroep": hoofdgroep,
                "subgroep": subgroep,
                "kenmerk": kenmerk,
            })

        if plek is None:
            continue

        ingedeeld.append({"id": product["id"], "hoofdgroep": hoofdgroep,
                          "subgroep": subgroep, "kenmerk": kenmerk})
        per_winkel[product["winkel_id"]] += 1
        per_groep[(plek.hoofdgroep, plek.subgroep or "(alleen de afdeling)")] += 1

    kwijt = sum(1 for regel in bijwerken if regel["hoofdgroep"] is None)
    if kwijt:
        log.info("%s %s vallen niet langer onder de indeling en worden "
                 "leeggemaakt.", kwijt, naam)

    if bijwerken and not proef:
        db.zet_eigen_groepen(bijwerken, tabel)
    elif not bijwerken:
        log.info("Er verandert niets bij de %s; alles stond al op de goede plek.", naam)

    return ingedeeld, per_winkel, per_groep


def stap_toepassen(
    db: Database, proef: bool
) -> dict[str, tuple[list[dict], Counter, Counter]]:
    """
    Deelt alles wat er nu staat in volgens het vertaalboekje.

    Zowel de aanbiedingen van deze week als de standaardprijzen van het gewone
    schap. Dat laatste is nodig omdat de standaardprijzen-pagina anders alleen
    de groepsnamen van de winkel zelf kan tonen: bij Vomar heet vochtig
    toiletpapier "Toiletpapier Vochtig" en dat is niet de taal van Dealbot.

    Het gebeurt hier in één keer voor alles, zodat een verbeterd vertaalboekje
    meteen doorwerkt zonder op de ophaalronde van morgenochtend te wachten.
    """
    boekje, woordenlijst = _lees_boekje(db)

    return {
        "aanbiedingen": _deel_tabel_in(
            db, "aanbiedingen", "aanbiedingen", boekje, woordenlijst, proef
        ),
        "standaardprijzen": _deel_tabel_in(
            db, "standaardprijzen", "standaardprijzen", boekje, woordenlijst, proef
        ),
    }


# -----------------------------------------------------------------------------
# Verslag
# -----------------------------------------------------------------------------
def _verslag_tabel(
    winkels: dict[int, str],
    naam: str,
    ingedeeld: list[dict],
    per_winkel: Counter,
    per_groep: Counter,
) -> None:
    """Wat één tabel heeft opgeleverd, in gewone taal."""
    print(f"\n  --- {naam} ---")

    if not ingedeeld:
        print("    Nog niets. Staat het vertaalboekje al in de database?")
        return

    print(f"\n    {len(ingedeeld)} ingedeeld.\n")
    print("    Per winkel:")
    for winkel_id, aantal in sorted(per_winkel.items(), key=lambda p: -p[1]):
        print(f"      {winkels.get(winkel_id, winkel_id):<15} {aantal:>6}")

    onvolledig = sum(a for (_, sub), a in per_groep.items() if sub == "(alleen de afdeling)")
    if onvolledig:
        deel = onvolledig / len(ingedeeld) * 100
        print(f"\n    {onvolledig} daarvan ({deel:.0f}%) kwamen niet verder dan de "
              "afdeling: de winkelgroep was te grof en de productnaam gaf niets prijs.")


def _verslag(db: Database, uitkomst: dict[str, tuple[list[dict], Counter, Counter]]) -> None:
    """
    Vertelt in gewone taal wat het opgeleverd heeft.

    Per tabel het aantal en de verdeling over de winkels, en daarna de volledige
    verdeling over onze eigen groepen — die laatste over alles bij elkaar, want
    daar gaat het om: hoe vol zit elke lade.
    """
    winkels = db.winkels()

    print("\n" + "=" * 70)
    print("  Wat er nu onder onze eigen indeling hangt")
    print("=" * 70)

    alles: Counter = Counter()
    for naam, (ingedeeld, per_winkel, per_groep) in uitkomst.items():
        _verslag_tabel(winkels, naam, ingedeeld, per_winkel, per_groep)
        alles.update(per_groep)

    if not alles:
        return

    print("\n  Per groep (alles bij elkaar):")
    for (hoofd, sub), aantal in sorted(alles.items()):
        print(f"    {hoofd} / {sub:<32} {aantal:>6}")

    _verslag_kenmerken(uitkomst)


def _verslag_kenmerken(
    uitkomst: dict[str, tuple[list[dict], Counter, Counter]]
) -> None:
    """
    Welke kenmerken zijn er onder de laden komen hangen?

    Dit is het deel om na een ronde even langs te lopen. Een lade met twee of
    drie kenmerken is precies de bedoeling; ziet u er tien, dan heeft de AI de
    groepsnamen zitten overschrijven in plaats van er iets uit te halen.

    De ruis staat er nadrukkelijk bij: kenmerken die maar bij één product
    voorkomen worden op de website niet getoond, maar hier wel geteld — anders
    is niet te zien dat ze bestaan.
    """
    teller: dict[tuple[str, str, str], int] = {}
    for ingedeeld, _, _ in uitkomst.values():
        for sleutel, aantal in tel_per_lade(ingedeeld).items():
            teller[sleutel] = teller.get(sleutel, 0) + aantal

    if not teller:
        print("\n  Nog geen kenmerken. Draai het vertalen om ze op te halen.")
        return

    getoond = {s: a for s, a in teller.items() if a >= 2}
    ruis = len(teller) - len(getoond)
    laden = {(hoofd, sub) for hoofd, sub, _ in getoond}

    print(f"\n  Kenmerken: {len(getoond)} verdeeld over {len(laden)} laden"
          + (f", plus {ruis} die maar bij één product voorkomen." if ruis else "."))

    vorige = None
    for (hoofd, sub, kenmerk), aantal in sorted(getoond.items(),
                                                key=lambda p: (p[0][0], p[0][1], -p[1])):
        if (hoofd, sub) != vorige:
            print(f"\n    {hoofd} / {sub}")
            vorige = (hoofd, sub)
        print(f"      {kenmerk:<26} {aantal:>6}")


def main() -> int:
    argumenten = argparse.ArgumentParser(
        description="Hangt alle aanbiedingen onder onze eigen productindeling."
    )
    argumenten.add_argument("--proef", action="store_true",
                            help="alleen laten zien, niets wegschrijven")
    argumenten.add_argument("--zonder-ai", action="store_true", dest="zonder_ai",
                            help="niet vertalen, alleen het bestaande boekje "
                                 "toepassen; kost geen enkele AI-vraag")
    argumenten.add_argument("--opnieuw", action="store_true",
                            help="ook groepen opnieuw vragen die al vertaald zijn")
    argumenten.add_argument("--woorden", default="",
                            help="alleen groepsnamen waar een van deze woorden in zit")
    argumenten.add_argument("--verder", nargs="?", const="auto", default="",
                            metavar="DATUM",
                            help="een afgebroken ronde hervatten: overslaan wat al "
                                 "bijgewerkt is. Duurde de ronde langer dan een "
                                 "etmaal, geef dan de begindatum mee (05-08-2026)")
    keuze = argumenten.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _lees_env()

    woorden = [eigen.schoon(w) for w in keuze.woorden.split(",") if w.strip()]

    try:
        db = Database()
    except DatabaseFout as fout:
        log.error("%s", fout)
        return 1

    if keuze.proef:
        log.info("PROEF — er wordt niets weggeschreven.\n")

    if keuze.zonder_ai and (keuze.opnieuw or keuze.verder or woorden):
        log.error("--zonder-ai gaat niet samen met --opnieuw, --verder of "
                  "--woorden: die drie gaan juist over het vertalen.")
        return 1

    try:
        stap_indeling(db, keuze.proef)
        klachten: list[str] = []
        if keuze.zonder_ai:
            tel_onvertaald(db)
        else:
            _, klachten = stap_vertalen(db, keuze.proef, keuze.opnieuw, woorden,
                                        keuze.verder)
        uitkomst = stap_toepassen(db, keuze.proef)
    except ValueError as fout:
        log.error("%s", fout)
        return 1
    except DatabaseFout as fout:
        log.error("Het ging mis met de database: %s", fout)
        return 1

    _verslag(db, uitkomst)

    if klachten:
        print("\n  Let op, dit ging niet goed:")
        for klacht in klachten:
            print("   -", klacht)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
