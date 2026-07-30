/**
 * =============================================================================
 *  Dealbot — de profielpagina met mijn zoekvragen
 *
 *  Versie      : 1.0
 *  Reden       : De gebruiker moet zelf kunnen bepalen waar Dealbot op let:
 *                zoekvragen bekijken, toevoegen en verwijderen.
 *  Datum       : 30-07-2026 23:07
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en haalt de zoekvragen op
 *    toonZoekvragen()  - zet de zoekvragen op het scherm
 *    koppelFormulier() - slaat een nieuwe zoekvraag op
 * =============================================================================
 */

import { haalZoekvragen, voegZoekvraagToe, verwijderZoekvraag, DealbotFout } from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { zoekvraagTekst } from './opmaak.js';

const lijst = document.getElementById('zoekvragen');
const formulier = document.getElementById('zoekvraagformulier');
const melding = document.getElementById('melding');
const adres = document.getElementById('adres');

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
            variant: document.getElementById('variant').value,
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
    await ververs();
}

bouwPagina();
