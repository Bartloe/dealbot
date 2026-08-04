/**
 * =============================================================================
 *  Dealbot — de startpagina met mijn aanbiedingen
 *
 *  Versie      : 1.3
 *  Reden       : De gevonden producten staan nu gebundeld onder de afdeling en
 *                de lade van onze eigen indeling. Sinds een zoekvraag over een
 *                hele afdeling kan gaan, werd de lijst anders één lange rij
 *                kaarten waarin niets meer te vinden was.
 *  Datum       : 04-08-2026 12:10
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en haalt de gegevens op
 *    toonAanbiedingen()- zet de gevonden aanbiedingen per afdeling op het scherm
 *    maakAfdeling()    - één afdeling als blok, met zijn laden erin
 *    maakProduct()     - één product met alle aanbiedingen die erbij horen
 *    toonLaatsteRun()  - meldt wanneer er voor het laatst is opgehaald
 *    toonGeenResultaat() - melding als er niets te halen valt
 * =============================================================================
 */

import { haalAanbiedingen, haalZoekvragen, haalLaatsteRun, DealbotFout } from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import {
    euro,
    kiloprijsTekst,
    geldigheidTekst,
    momentTekst,
    groepeerPerProduct,
    bundelPerIndeling,
} from './opmaak.js';

// Tot en met dit aantal afdelingen staat alles meteen open. Daarboven zijn de
// blokken dicht, zodat je eerst ziet in welke afdelingen iets ligt in plaats van
// meteen door tientallen kaarten te moeten scrollen.
const AFDELINGEN_OPEN_TOT = 6;

const lijst = document.getElementById('lijst');
const samenvatting = document.getElementById('samenvatting');
const laatsterun = document.getElementById('laatsterun');
const melding = document.getElementById('melding');

function toonMelding(tekst, soort = 'fout') {
    melding.textContent = tekst;
    melding.className = `melding ${soort}`;
    melding.hidden = !tekst;
}

/** Maakt een element met tekst erin; tekst uit de database gaat nooit als code. */
function maak(soort, klasse, tekst) {
    const element = document.createElement(soort);
    if (klasse) element.className = klasse;
    if (tekst) element.textContent = tekst;
    return element;
}

/** Eén aanbieding als regel binnen een product. */
function maakRegel(aanbieding, isBeste) {
    const regel = maak('li', `regel${isBeste ? ' beste' : ''}`);

    regel.append(maak('span', 'winkel', aanbieding.winkel));

    const prijzen = maak('span', 'prijzen');
    if (aanbieding.prijs !== null && aanbieding.prijs !== undefined) {
        prijzen.append(maak('strong', 'prijs', euro(aanbieding.prijs)));
    }
    if (aanbieding.normale_prijs && aanbieding.normale_prijs !== aanbieding.prijs) {
        prijzen.append(maak('s', 'oude-prijs', euro(aanbieding.normale_prijs)));
    }
    if (prijzen.childElementCount > 0) {
        regel.append(prijzen);
    }

    if (aanbieding.actie_tekst) {
        regel.append(maak('span', 'actie', aanbieding.actie_tekst));
    }

    const kiloprijs = kiloprijsTekst(aanbieding);
    regel.append(maak('span', kiloprijs === 'kiloprijs onbekend' ? 'kiloprijs onbekend' : 'kiloprijs', kiloprijs));

    const geldig = geldigheidTekst(aanbieding);
    if (geldig) {
        regel.append(maak('span', 'geldig', geldig));
    }

    if (isBeste) {
        regel.append(maak('span', 'label', 'beste prijs'));
    }
    return regel;
}

/** Eén product met alle aanbiedingen die erbij horen. */
function maakProduct(groep) {
    const kaart = maak('article', 'product');
    const kop = maak('div', 'producttop');

    if (groep.naamgever.afbeelding_url) {
        const plaatje = document.createElement('img');
        plaatje.src = groep.naamgever.afbeelding_url;
        plaatje.alt = '';
        plaatje.loading = 'lazy';
        // Een kapotte link naar een plaatje mag geen gat in de pagina slaan.
        plaatje.addEventListener('error', () => plaatje.remove());
        kop.append(plaatje);
    }

    const tekst = maak('div', 'producttekst');
    tekst.append(maak('h2', null, groep.titel));
    if (groep.regels.length > 1) {
        tekst.append(maak('p', 'aantal', `${groep.regels.length} aanbiedingen`));
    }
    kop.append(tekst);
    kaart.append(kop);

    const regels = maak('ul', 'aanbiedingen');
    groep.regels.forEach((aanbieding, nummer) => {
        regels.append(maakRegel(aanbieding, nummer === 0 && groep.vergelijkbaar));
    });
    kaart.append(regels);

    // Verschillende eenheden binnen één product: dan is de volgorde geen
    // eerlijke rangschikking en zegt het scherm dat er ook bij.
    if (groep.regels.length > 1 && !groep.vergelijkbaar) {
        kaart.append(maak('p', 'kanttekening',
            'De verpakkingen verschillen, dus deze prijzen zijn niet één op één te vergelijken.'));
    }

    return kaart;
}

/**
 * Eén afdeling als blok om in en uit te klappen, met de laden erbinnen.
 *
 * De naam van de lade staat als tussenkopje boven zijn producten. Heeft een
 * afdeling maar één lade en is die onbekend gebleven, dan blijft dat kopje weg:
 * "Overig" boven de hele afdeling zegt niets.
 */
function maakAfdeling(afdeling, openVanzelf) {
    const blok = document.createElement('details');
    blok.className = 'afdelingblok';
    blok.open = openVanzelf;

    const kop = document.createElement('summary');
    kop.append(maak('span', 'afdelingnaam', afdeling.naam));
    kop.append(maak('span', 'afdelingaantal', String(afdeling.aantal)));
    blok.append(kop);

    const inhoud = maak('div', 'afdelinginhoud');
    const kopjesTonen = !(afdeling.laden.length === 1 && afdeling.laden[0].onbekend);

    for (const lade of afdeling.laden) {
        if (kopjesTonen) {
            const ladekop = maak('p', 'ladekop', lade.naam);
            ladekop.append(maak('span', 'ladeaantal', String(lade.producten.length)));
            inhoud.append(ladekop);
        }
        inhoud.append(...lade.producten.map(maakProduct));
    }

    blok.append(inhoud);
    return blok;
}

function toonAanbiedingen(aanbiedingen) {
    const producten = groepeerPerProduct(aanbiedingen);
    const afdelingen = bundelPerIndeling(producten);

    const aantalTekst = producten.length === 1
        ? '1 product met een aanbieding voor jou'
        : `${producten.length} producten met een aanbieding voor jou`;
    const afdelingTekst = afdelingen.length === 1
        ? 'in 1 afdeling.'
        : `in ${afdelingen.length} afdelingen.`;

    samenvatting.textContent = `${aantalTekst}, ${afdelingTekst}`;
    samenvatting.hidden = false;

    const openVanzelf = afdelingen.length <= AFDELINGEN_OPEN_TOT;
    lijst.replaceChildren(...afdelingen.map((afdeling) => maakAfdeling(afdeling, openVanzelf)));
}

/**
 * Meldt wanneer de aanbiedingen voor het laatst zijn opgehaald.
 *
 * Staat er sinds die ronde een mislukking in het logboek, dan komt dat erbij:
 * de lijst is dan ouder dan de gebruiker op grond van de klok zou aannemen, en
 * dat hoort hij te weten voordat hij op pad gaat.
 *
 * Deze regel is bijzaak — lukt het opzoeken niet, dan blijft hij gewoon weg.
 */
function toonLaatsteRun(run) {
    const moment = momentTekst(run.gelukt);
    if (!moment) {
        laatsterun.hidden = true;
        return;
    }

    laatsterun.textContent = run.storing
        ? `Laatste run gedraaid op: ${moment} — de poging van ${momentTekst(run.storing)} is mislukt.`
        : `Laatste run gedraaid op: ${moment}`;
    laatsterun.className = run.storing ? 'laatste-run storing' : 'laatste-run';
    laatsterun.hidden = false;
}

/**
 * Wat de gebruiker ziet als er niets te tonen is.
 *
 * Twee heel verschillende situaties: nog geen zoekvragen ingevuld, of wel
 * zoekvragen maar deze week geen treffer. Die verdienen een andere tekst.
 */
function toonGeenResultaat(heeftZoekvragen) {
    const kaart = maak('div', 'leeg');

    if (!heeftZoekvragen) {
        kaart.append(maak('h2', null, 'Je hebt nog geen zoekvragen'));
        kaart.append(maak('p', null,
            'Vertel eerst waar je op wilt letten — een merk, een productgroep of gewoon '
            + 'een stukje tekst. Daarna verschijnen hier de aanbiedingen die daarbij passen.'));

        const knop = maak('a', 'knop', 'Zoekvragen instellen');
        knop.href = 'profiel.html';
        kaart.append(knop);
    } else {
        kaart.append(maak('h2', null, 'Deze week even niets'));
        kaart.append(maak('p', null,
            'Er zijn op dit moment geen aanbiedingen die bij jouw zoekvragen passen. '
            + 'Kijk gerust morgen weer, of pas je zoekvragen aan.'));

        const knoppen = maak('div', 'knoppen');
        const naarPrijzen = maak('a', 'knop', 'Bekijk de standaardprijzen');
        naarPrijzen.href = 'standaardprijzen.html';
        const naarProfiel = maak('a', 'knop tweede', 'Zoekvragen aanpassen');
        naarProfiel.href = 'profiel.html';
        knoppen.append(naarPrijzen, naarProfiel);
        kaart.append(knoppen);
    }

    lijst.replaceChildren(kaart);
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    lijst.replaceChildren(maak('p', 'bezig', 'Aanbiedingen ophalen…'));

    // Los van de aanbiedingen: deze regel is prettig om te weten, maar mag de
    // lijst niet ophouden en al helemaal niet tegenhouden als hij niet lukt.
    haalLaatsteRun()
        .then(toonLaatsteRun)
        .catch((fout) => {
            laatsterun.hidden = true;
            console.error('Dealbot — laatste ophaalronde onbekend:', fout);
        });

    try {
        const [zoekvragen, aanbiedingen] = await Promise.all([
            haalZoekvragen(),
            haalAanbiedingen(),
        ]);

        console.info(
            `Dealbot — startpagina: ${zoekvragen.length} zoekvragen, `
            + `${aanbiedingen.length} passende aanbiedingen.`
        );

        if (aanbiedingen.length === 0) {
            samenvatting.hidden = true;
            toonGeenResultaat(zoekvragen.length > 0);
            return;
        }

        toonAanbiedingen(aanbiedingen);
    } catch (fout) {
        lijst.replaceChildren();
        samenvatting.hidden = true;
        if (fout instanceof DealbotFout) {
            toonMelding(fout.message);
        } else {
            console.error('Dealbot — startpagina kon niet worden opgebouwd:', fout);
            toonMelding('De aanbiedingen konden niet worden opgehaald. Probeer het later nog eens.');
        }
    }
}

bouwPagina();
