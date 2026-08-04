/**
 * =============================================================================
 *  Dealbot — de beheerpagina
 *
 *  Versie      : 1.0
 *  Reden       : Tot nu toe was nergens te zien hoe het ophalen van vanochtend
 *                is gegaan. Bij een storing zag de site er gewoon uit, alleen
 *                met oudere prijzen. Deze pagina laat per winkel zien wanneer
 *                er voor het laatst is opgehaald, of dat lukte en hoeveel er
 *                binnenkwam — en wat er aan de oogst ontbreekt.
 *  Datum       : 04-08-2026 22:35
 *
 *  Onderdelen:
 *    bouwPagina()    - regelt de toegang en haalt beide overzichten op
 *    toonRunstatus() - de laatste ronde per winkel als tabel
 *    toonKwaliteit() - aantallen per winkel, met wat er ontbreekt
 *    maakTabel()     - een tabel met kop en regels, zonder opsmuk
 * =============================================================================
 */

import { benIkBeheerder, haalRunstatus, haalKwaliteit, DealbotFout } from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { momentTekst } from './opmaak.js';

// Wat voor ronde het was, in gewone taal. Vomar levert er twee: zijn gewone
// schapprijzen en zijn folder, en die zijn allebei apart de moeite waard.
const SOORTEN = {
    aanbiedingen: 'Aanbiedingen',
    assortiment: 'Schapprijzen',
    folder: 'Folder (voorgelezen)',
};

const RESULTAAT = {
    gelukt: 'gelukt',
    mislukt: 'mislukt',
    bezig: 'nog bezig',
};

const melding = document.getElementById('melding');
const beheer = document.getElementById('beheer');
const runstatus = document.getElementById('runstatus');
const kwaliteit = document.getElementById('kwaliteit');

function toonMelding(tekst, soort = 'fout') {
    melding.textContent = tekst;
    melding.className = `melding ${soort}`;
    melding.hidden = !tekst;
}

/** Maakt een element met tekst erin; tekst uit de database gaat nooit als code. */
function maak(soort, klasse, tekst) {
    const element = document.createElement(soort);
    if (klasse) element.className = klasse;
    if (tekst !== undefined && tekst !== null) element.textContent = tekst;
    return element;
}

/**
 * Een tabel met een kopregel en daaronder de gegeven regels.
 *
 * Elke cel is óf een stuk tekst óf een kant-en-klaar element, zodat een regel
 * met een storingsmelding eronder net zo gebouwd wordt als een gewone.
 */
function maakTabel(koppen, regels) {
    const tabel = maak('table', 'beheertabel');

    const kop = document.createElement('thead');
    const koprij = document.createElement('tr');
    for (const tekst of koppen) {
        koprij.append(maak('th', null, tekst));
    }
    kop.append(koprij);
    tabel.append(kop);

    const lijf = document.createElement('tbody');
    for (const regel of regels) {
        const rij = maak('tr', regel.klasse);
        for (const cel of regel.cellen) {
            const vak = maak('td', cel.klasse);
            if (cel.breedte) {
                vak.colSpan = cel.breedte;
            }
            if (cel.element) {
                vak.append(cel.element);
            } else {
                vak.textContent = cel.tekst ?? '';
            }
            rij.append(vak);
        }
        lijf.append(rij);
    }
    tabel.append(lijf);

    return tabel;
}

/** Een getal met daarachter het aandeel van het geheel, als dat iets toevoegt. */
function metAandeel(aantal, totaal) {
    const getal = Number(aantal) || 0;
    const geheel = Number(totaal) || 0;
    if (getal === 0) {
        return '0';
    }
    if (geheel === 0) {
        return String(getal);
    }
    return `${getal} (${Math.round((getal / geheel) * 100)}%)`;
}

/** De naam van de winkel, met een aantekening als hij uitstaat. */
function winkelnaam(regel) {
    return regel.actief ? regel.winkel : `${regel.winkel} (staat uit)`;
}

/**
 * De laatste ronde per winkel.
 *
 * Een winkel die nog nooit heeft gedraaid blijft in de lijst staan met lege
 * velden: dat je van Nettorama niets ziet is zelf ook een bericht. Ging er iets
 * mis, dan staat de melding uit het logboek eronder — dat is doorgaans genoeg
 * om te weten welke bron dicht zit.
 */
function toonRunstatus(regels) {
    if (regels.length === 0) {
        runstatus.replaceChildren(maak('p', 'leeg-regel', 'Er is nog niets opgehaald.'));
        return;
    }

    const rijen = [];
    for (const regel of regels) {
        const heeftRonde = Boolean(regel.status);
        const resultaat = heeftRonde
            ? (RESULTAAT[regel.status] || regel.status)
            : 'nog nooit gedraaid';

        const wanneer = maak('span', null, momentTekst(regel.klaar_op || regel.gestart_op) || '—');
        const uitkomst = maak('span', regel.status === 'mislukt' ? 'fout-tekst' : null, resultaat);

        rijen.push({
            klasse: regel.actief ? null : 'uit',
            cellen: [
                { tekst: winkelnaam(regel) },
                { tekst: heeftRonde ? (SOORTEN[regel.soort] || regel.soort) : '—' },
                { element: wanneer },
                { element: uitkomst },
                { tekst: heeftRonde ? String(regel.aantal ?? 0) : '—', klasse: 'getal' },
            ],
        });

        if (regel.melding) {
            rijen.push({
                klasse: 'meldingregel',
                cellen: [
                    { tekst: '' },
                    { tekst: regel.melding, klasse: 'storingtekst', breedte: 4 },
                ],
            });
        }
    }

    runstatus.replaceChildren(
        maakTabel(['Winkel', 'Wat', 'Wanneer', 'Resultaat', 'Aantal'], rijen)
    );
}

/**
 * Hoeveel er per winkel staat, en hoeveel daarvan onvolledig is.
 *
 * Winkels waar helemaal niets van in de database staat blijven staan, maar in
 * lichtere letters: die vragen geen aandacht, ze doen alleen niet mee.
 */
function toonKwaliteit(regels) {
    if (regels.length === 0) {
        kwaliteit.replaceChildren(maak('p', 'leeg-regel', 'Er staat nog niets in de database.'));
        return;
    }

    const rijen = regels.map((regel) => {
        const leeg = Number(regel.aanbiedingen) === 0 && Number(regel.standaardprijzen) === 0;
        return {
            klasse: leeg ? 'uit' : null,
            cellen: [
                { tekst: winkelnaam(regel) },
                { tekst: String(regel.aanbiedingen ?? 0), klasse: 'getal' },
                { tekst: metAandeel(regel.zonder_kiloprijs, regel.aanbiedingen), klasse: 'getal' },
                { tekst: metAandeel(regel.zonder_indeling, regel.aanbiedingen), klasse: 'getal' },
                { tekst: String(regel.standaardprijzen ?? 0), klasse: 'getal' },
                { tekst: metAandeel(regel.prijzen_zonder_kilo, regel.standaardprijzen), klasse: 'getal' },
            ],
        };
    });

    kwaliteit.replaceChildren(maakTabel(
        ['Winkel', 'Aanbiedingen', 'zonder kiloprijs', 'zonder indeling',
            'Schapprijzen', 'zonder kiloprijs'],
        rijen
    ));
}

/** Haalt beide overzichten op en zet ze op het scherm. */
async function laadOverzichten() {
    runstatus.replaceChildren(maak('p', 'bezig', 'Overzicht ophalen…'));
    kwaliteit.replaceChildren(maak('p', 'bezig', 'Cijfers ophalen…'));

    try {
        const [rondes, cijfers] = await Promise.all([haalRunstatus(), haalKwaliteit()]);
        console.info(
            `Dealbot — beheer: ${rondes.length} rondes en ${cijfers.length} winkels opgehaald.`
        );
        toonRunstatus(rondes);
        toonKwaliteit(cijfers);
        toonMelding('');
    } catch (fout) {
        runstatus.replaceChildren();
        kwaliteit.replaceChildren();
        if (fout instanceof DealbotFout) {
            toonMelding(fout.message);
        } else {
            console.error('Dealbot — beheerpagina kon niet worden opgebouwd:', fout);
            toonMelding('De beheergegevens konden niet worden opgehaald. Probeer het later nog eens.');
        }
    }
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    // De echte grendel zit in de database; deze controle is er om een gewone
    // gebruiker een fatsoenlijke uitleg te geven in plaats van een foutmelding.
    if (!(await benIkBeheerder())) {
        beheer.hidden = true;
        toonMelding('Deze pagina is alleen voor de beheerder.');
        return;
    }

    beheer.hidden = false;
    document.getElementById('verversen').addEventListener('click', laadOverzichten);
    await laadOverzichten();
}

bouwPagina();
