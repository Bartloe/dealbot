/**
 * =============================================================================
 *  Dealbot — de profielpagina met mijn zoekvragen
 *
 *  Versie      : 1.1
 *  Reden       : "Variant" is vervangen door "Productgroep" met een keuzelijst.
 *                Die lijst komt uit de aanbiedingen van deze week, per winkel
 *                gegroepeerd, zodat niemand een groep kan kiezen die niets
 *                oplevert of die bij die winkel niet bestaat.
 *  Datum       : 31-07-2026 01:12
 *
 *  Onderdelen:
 *    bouwPagina()        - regelt de toegang en haalt de gegevens op
 *    vulProductgroepen() - zet de beschikbare groepen in de keuzelijst
 *    toonZoekvragen()    - zet de zoekvragen op het scherm
 *    koppelFormulier()   - slaat een nieuwe zoekvraag op
 * =============================================================================
 */

import {
    haalZoekvragen,
    haalProductgroepen,
    voegZoekvraagToe,
    verwijderZoekvraag,
    DealbotFout,
} from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { zoekvraagTekst } from './opmaak.js';

const lijst = document.getElementById('zoekvragen');
const formulier = document.getElementById('zoekvraagformulier');
const melding = document.getElementById('melding');
const adres = document.getElementById('adres');
const groepenlijst = document.getElementById('productgroep');

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
 * Vult de keuzelijst met de productgroepen van deze week.
 *
 * Per winkel een eigen kopje, want elke keten deelt zijn assortiment anders in:
 * Albert Heijn tot op "Toiletpapier - vochtig", Dirk niet verder dan
 * "Dranken, sap, koffie & thee". Het aantal aanbiedingen staat erbij, zodat
 * zichtbaar is hoe breed een groep is voordat je hem kiest.
 *
 * Lukt het ophalen niet, dan blijft het veld leeg en bruikbaar: de gebruiker
 * kan dan nog steeds op merk of vrije tekst zoeken.
 */
function vulProductgroepen(groepen) {
    const leeg = document.createElement('option');
    leeg.value = '';
    leeg.textContent = groepen.length === 0
        ? 'Geen groepen beschikbaar'
        : 'Alle groepen (niet op groep zoeken)';

    const perWinkel = new Map();
    for (const groep of groepen) {
        if (!perWinkel.has(groep.winkel)) {
            perWinkel.set(groep.winkel, []);
        }
        perWinkel.get(groep.winkel).push(groep);
    }

    const kopjes = [...perWinkel.entries()].map(([winkel, regels]) => {
        const kopje = document.createElement('optgroup');
        kopje.label = winkel;
        for (const regel of regels) {
            const keuze = document.createElement('option');
            keuze.value = regel.productgroep;
            keuze.textContent = `${regel.productgroep} (${regel.aantal})`;
            kopje.append(keuze);
        }
        return kopje;
    });

    groepenlijst.replaceChildren(leeg, ...kopjes);
    groepenlijst.disabled = groepen.length === 0;
}

/** Haalt de keuzelijst op; een storing hier mag de pagina niet blokkeren. */
async function laadProductgroepen() {
    try {
        const groepen = await haalProductgroepen();
        console.info(`Dealbot — profiel: ${groepen.length} productgroepen geladen.`);
        vulProductgroepen(groepen);
    } catch (fout) {
        vulProductgroepen([]);
        console.error('Dealbot — productgroepen laden mislukt:', fout);
    }
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
            productgroep: groepenlijst.value,
            vrije_tekst: document.getElementById('vrije_tekst').value,
        };

        try {
            await voegZoekvraagToe(velden);
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

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    adres.textContent = gebruiker.email || '';
    koppelFormulier();
    await Promise.all([ververs(), laadProductgroepen()]);
}

bouwPagina();
