/**
 * =============================================================================
 *  Dealbot — de profielpagina met mijn zoekvragen
 *
 *  Versie      : 2.0
 *  Reden       : De keuzelijst met 479 groepen van Albert Heijn was niet meer om
 *                door te scrollen, en wie "koffie" zocht vond niets: die groepen
 *                heten "Douwe Egberts koffiebonen" en staan dus onder de D. Je
 *                zoekt nu op een woord, dwars door alle winkels heen, en kunt in
 *                één keer meerdere groepen aanvinken.
 *  Datum       : 01-08-2026 14:32
 *
 *  Onderdelen:
 *    bouwPagina()       - regelt de toegang en haalt de gegevens op
 *    toonZoekvragen()   - zet de zoekvragen op het scherm
 *    koppelFormulier()  - slaat een zoekvraag op merk of vrije tekst op
 *    koppelGroepkiezer()- zoeken, aanvinken en opslaan van productgroepen
 * =============================================================================
 */

import {
    haalZoekvragen,
    haalProductgroepen,
    voegZoekvragenToe,
    verwijderZoekvraag,
    DealbotFout,
} from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { zoekvraagTekst } from './opmaak.js';

const lijst = document.getElementById('zoekvragen');
const formulier = document.getElementById('zoekvraagformulier');
const melding = document.getElementById('melding');
const adres = document.getElementById('adres');

const zoekveld = document.getElementById('groepzoek');
const resultaten = document.getElementById('groepresultaten');
const gekozenlijst = document.getElementById('gekozen');
const zoekhulp = document.getElementById('zoekhulp');
const groepenknop = document.getElementById('groepenopslaan');

// Hoeveel treffers we hoogstens tonen. Meer is niet te overzien; typ dan verder.
const MAX_TREFFERS = 40;

// Alle bekende groepen, en wat de gebruiker heeft aangevinkt. De sleutel bevat
// de winkel, want dezelfde groepsnaam kan bij twee winkels voorkomen.
let allegroepen = [];
const gekozen = new Map();

const sleutelVan = (groep) => `${groep.winkel_id}|${groep.productgroep}`;

function toonMelding(tekst, soort = 'fout') {
    melding.textContent = tekst;
    melding.className = `melding ${soort}`;
    melding.hidden = !tekst;
}

function maak(soort, klasse, tekst) {
    const element = document.createElement(soort);
    if (klasse) element.className = klasse;
    if (tekst) element.textContent = tekst;
    return element;
}

/** Eén zoekvraag met een knop om hem weg te halen. */
function maakZoekvraag(zoekvraag, naVerwijderen) {
    const regel = maak('li', 'zoekvraag');
    regel.append(maak('span', 'omschrijving', zoekvraagTekst(zoekvraag)));

    const knop = maak('button', 'verwijder', 'Verwijderen');
    knop.type = 'button';
    knop.addEventListener('click', async () => {
        if (!window.confirm('Deze zoekvraag verwijderen?')) {
            return;
        }
        knop.disabled = true;
        try {
            await verwijderZoekvraag(zoekvraag.id);
            toonMelding('De zoekvraag is verwijderd.', 'goed');
            await naVerwijderen();
        } catch (fout) {
            knop.disabled = false;
            toonMelding(fout instanceof DealbotFout
                ? fout.message
                : 'De zoekvraag kon niet worden verwijderd.');
            if (!(fout instanceof DealbotFout)) {
                console.error('Dealbot — verwijderen mislukt:', fout);
            }
        }
    });

    regel.append(knop);
    return regel;
}

/**
 * Zegt achter een groep wat erin zit op dit moment.
 *
 * Nul is nadrukkelijk geen reden om de groep te verbergen: juist dan is een
 * zoekvraag nuttig, want die blijft klaarstaan tot de winkel er weer iets van
 * in de bonus doet.
 */
function aantalTekst(aantal) {
    if (aantal === 0) return 'nu niets in de bonus';
    if (aantal === 1) return 'nu 1 aanbieding';
    return `nu ${aantal} aanbiedingen`;
}

/**
 * De groepen die bij een zoekwoord passen.
 *
 * Zoekt in de naam van de groep, waar het woord ook staat: "koffie" moet ook
 * "Douwe Egberts koffiebonen" vinden — juist dat ging mis toen je nog door een
 * alfabetische lijst moest scrollen. Groepen die met het woord beginnen komen
 * bovenaan, daarna wat er nu in de bonus zit.
 */
function zoekGroepen(woord) {
    const term = woord.trim().toLowerCase();
    if (term === '') {
        return [];
    }

    return allegroepen
        .filter((groep) => groep.productgroep.toLowerCase().includes(term))
        .sort((a, b) => {
            const beginA = a.productgroep.toLowerCase().startsWith(term);
            const beginB = b.productgroep.toLowerCase().startsWith(term);
            if (beginA !== beginB) return beginA ? -1 : 1;
            if ((a.aantal > 0) !== (b.aantal > 0)) return a.aantal > 0 ? -1 : 1;
            return a.productgroep.localeCompare(b.productgroep, 'nl');
        });
}

/** Eén treffer om aan te vinken, met de winkel erachter. */
function maakTreffer(groep) {
    const regel = maak('li', 'treffer');
    const label = document.createElement('label');

    const vinkje = document.createElement('input');
    vinkje.type = 'checkbox';
    vinkje.checked = gekozen.has(sleutelVan(groep));
    vinkje.addEventListener('change', () => {
        if (vinkje.checked) {
            gekozen.set(sleutelVan(groep), groep);
        } else {
            gekozen.delete(sleutelVan(groep));
        }
        toonGekozen();
    });

    const naam = maak('span', 'treffernaam', groep.productgroep);
    const erbij = maak('span', 'trefferwinkel', `(${groep.winkel})`);
    const telling = maak('span', groep.aantal > 0 ? 'trefferaantal' : 'trefferaantal leeg',
        aantalTekst(groep.aantal));

    label.append(vinkje, naam, erbij, telling);
    regel.append(label);
    return regel;
}

/** Zet de treffers van het zoekwoord op het scherm. */
function toonTreffers(woord) {
    const gevonden = zoekGroepen(woord);

    if (woord.trim() === '') {
        resultaten.replaceChildren();
        zoekhulp.textContent = allegroepen.length > 0
            ? `Typ een woord om te zoeken in ${allegroepen.length} productgroepen.`
            : 'De productgroepen konden niet worden opgehaald.';
        return;
    }

    if (gevonden.length === 0) {
        resultaten.replaceChildren();
        zoekhulp.textContent = `Geen productgroep gevonden met "${woord.trim()}". `
            + 'Probeer een korter woord, of gebruik hierboven het veld Vrije tekst.';
        return;
    }

    const tonen = gevonden.slice(0, MAX_TREFFERS);
    zoekhulp.textContent = gevonden.length > tonen.length
        ? `${gevonden.length} groepen gevonden; de eerste ${tonen.length} staan hieronder. Typ verder om te verfijnen.`
        : `${gevonden.length} ${gevonden.length === 1 ? 'groep' : 'groepen'} gevonden.`;

    resultaten.replaceChildren(...tonen.map(maakTreffer));
}

/** De aangevinkte groepen boven het zoekveld, zodat je ze niet kwijtraakt. */
function toonGekozen() {
    const regels = [...gekozen.values()].map((groep) => {
        const regel = maak('li', 'gekozen-groep');
        regel.append(maak('span', null, `${groep.productgroep} (${groep.winkel})`));

        const weg = maak('button', 'weg', '×');
        weg.type = 'button';
        weg.title = 'Deze keuze weghalen';
        weg.addEventListener('click', () => {
            gekozen.delete(sleutelVan(groep));
            toonGekozen();
            toonTreffers(zoekveld.value);
        });

        regel.append(weg);
        return regel;
    });

    gekozenlijst.replaceChildren(...regels);
    gekozenlijst.hidden = regels.length === 0;

    groepenknop.disabled = regels.length === 0;
    groepenknop.textContent = regels.length === 0
        ? 'Kies eerst een groep'
        : `${regels.length} ${regels.length === 1 ? 'zoekvraag' : 'zoekvragen'} opslaan`;
}

/** Haalt de groepen op; een storing hier mag de pagina niet blokkeren. */
async function laadProductgroepen() {
    try {
        allegroepen = await haalProductgroepen();
        console.info(`Dealbot — profiel: ${allegroepen.length} productgroepen geladen.`);
    } catch (fout) {
        allegroepen = [];
        console.error('Dealbot — productgroepen laden mislukt:', fout);
    }
    toonTreffers(zoekveld.value);
}

function toonZoekvragen(zoekvragen, herlaad) {
    if (zoekvragen.length === 0) {
        lijst.replaceChildren(maak('li', 'leeg-regel',
            'Je hebt nog geen zoekvragen. Voeg er hieronder één toe.'));
        return;
    }
    lijst.replaceChildren(...zoekvragen.map((z) => maakZoekvraag(z, herlaad)));
}

/** Haalt de zoekvragen opnieuw op en zet ze op het scherm. */
async function ververs() {
    try {
        const zoekvragen = await haalZoekvragen();
        console.info(`Dealbot — profiel: ${zoekvragen.length} zoekvragen geladen.`);
        toonZoekvragen(zoekvragen, ververs);
    } catch (fout) {
        lijst.replaceChildren();
        toonMelding(fout instanceof DealbotFout
            ? fout.message
            : 'De zoekvragen konden niet worden opgehaald.');
        if (!(fout instanceof DealbotFout)) {
            console.error('Dealbot — zoekvragen laden mislukt:', fout);
        }
    }
}

function koppelFormulier() {
    const knop = document.getElementById('opslaan');

    formulier.addEventListener('submit', async (gebeurtenis) => {
        gebeurtenis.preventDefault();
        toonMelding('');
        knop.disabled = true;

        const velden = {
            merk: document.getElementById('merk').value,
            vrije_tekst: document.getElementById('vrije_tekst').value,
        };

        try {
            await voegZoekvragenToe([velden]);
            formulier.reset();
            toonMelding('De zoekvraag is opgeslagen.', 'goed');
            await ververs();
        } catch (fout) {
            toonMelding(fout instanceof DealbotFout
                ? fout.message
                : 'De zoekvraag kon niet worden opgeslagen.');
            if (!(fout instanceof DealbotFout)) {
                console.error('Dealbot — opslaan mislukt:', fout);
            }
        } finally {
            knop.disabled = false;
        }
    });
}

/**
 * Het zoeken en aanvinken van productgroepen.
 *
 * Elke aangevinkte groep wordt een eigen zoekvraag. Ze staan los van elkaar, dus
 * je kunt in één handeling dezelfde soort bij drie winkels in de gaten houden.
 */
function koppelGroepkiezer() {
    zoekveld.addEventListener('input', () => toonTreffers(zoekveld.value));

    // Enter in een zoekveld mag de pagina niet herladen.
    zoekveld.addEventListener('keydown', (gebeurtenis) => {
        if (gebeurtenis.key === 'Enter') {
            gebeurtenis.preventDefault();
        }
    });

    groepenknop.addEventListener('click', async () => {
        if (gekozen.size === 0) {
            return;
        }
        toonMelding('');
        groepenknop.disabled = true;

        const nieuwe = [...gekozen.values()].map((groep) => ({
            productgroep: groep.productgroep,
        }));

        try {
            const opgeslagen = await voegZoekvragenToe(nieuwe);
            gekozen.clear();
            zoekveld.value = '';
            toonGekozen();
            toonTreffers('');
            toonMelding(opgeslagen.length === 1
                ? 'De zoekvraag is opgeslagen.'
                : `${opgeslagen.length} zoekvragen zijn opgeslagen.`, 'goed');
            await ververs();
        } catch (fout) {
            toonGekozen();
            toonMelding(fout instanceof DealbotFout
                ? fout.message
                : 'De zoekvragen konden niet worden opgeslagen.');
            if (!(fout instanceof DealbotFout)) {
                console.error('Dealbot — opslaan van groepen mislukt:', fout);
            }
        }
    });
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    adres.textContent = gebruiker.email || '';
    koppelFormulier();
    koppelGroepkiezer();
    toonGekozen();
    await Promise.all([ververs(), laadProductgroepen()]);
}

bouwPagina();
