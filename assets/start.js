/**
 * =============================================================================
 *  Dealbot — de startpagina met mijn aanbiedingen
 *
 *  Versie      : 1.2
 *  Reden       : Onder de kop staat nu wanneer de aanbiedingen voor het laatst
 *                zijn opgehaald. Zonder dat is niet te zien of de lijst van
 *                vanochtend is of van eergisteren.
 *  Datum       : 01-08-2026 13:18
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en haalt de gegevens op
 *    toonAanbiedingen()- zet de gevonden aanbiedingen op het scherm
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
} from './opmaak.js';

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

function toonAanbiedingen(aanbiedingen) {
    const groepen = groepeerPerProduct(aanbiedingen);

    samenvatting.textContent = groepen.length === 1
        ? '1 product met een aanbieding voor jou.'
        : `${groepen.length} producten met een aanbieding voor jou.`;
    samenvatting.hidden = false;

    lijst.replaceChildren(...groepen.map(maakProduct));
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
