/**
 * =============================================================================
 *  Dealbot — de profielpagina met mijn zoekvragen
 *
 *  Versie      : 3.0
 *  Reden       : Je koos tot nu toe de groepsnaam van één winkel. Wie
 *                koffiebonen wilde volgen moest dat dus bij elke keten apart
 *                doen, in de woorden van die keten — en bij Vomar kon het
 *                helemaal niet. Nu staat onze eigen indeling op het scherm:
 *                afdelingen met daaronder groepen, bij elke winkel hetzelfde.
 *                Eén keer "Koffiebonen" aanvinken dekt alle winkels.
 *  Datum       : 04-08-2026 11:05
 *
 *  Onderdelen:
 *    bouwPagina()       - regelt de toegang en haalt de gegevens op
 *    toonZoekvragen()   - zet de zoekvragen op het scherm
 *    koppelFormulier()  - slaat een zoekvraag op merk of vrije tekst op
 *    koppelGroepkiezer()- zoeken, aanvinken en opslaan binnen onze indeling
 *    bouwAfdelingen()   - maakt van de losse regels afdelingen met hun groepen
 *    toonIndeling()     - tekent de indeling, gefilterd op het zoekwoord
 * =============================================================================
 */

import {
    haalZoekvragen,
    haalEigenIndeling,
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
const indelingsvak = document.getElementById('indeling');
const gekozenlijst = document.getElementById('gekozen');
const zoekhulp = document.getElementById('zoekhulp');
const groepenknop = document.getElementById('groepenopslaan');

// Onze indeling: afdelingen met hun groepen, zoals de database ze levert.
let afdelingen = [];

// Wat de gebruiker nu aanvinkt, en wat hij al volgt. Beide op dezelfde sleutel,
// zodat een groep die al in een zoekvraag zit niet nog eens te kiezen is.
const gekozen = new Map();
let alGevolgd = new Set();

// Welke afdelingen openstaan. Nodig omdat de lijst opnieuw getekend wordt zodra
// je iets aanvinkt; zonder dit klapt de afdeling waar je in bezig bent dicht.
const openstaand = new Set();

const sleutelVan = (hoofdgroep, subgroep) => `${hoofdgroep}||${subgroep || ''}`;

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
 * zoekvraag nuttig, want die blijft klaarstaan tot er weer iets van in de bonus
 * komt.
 */
function aantalTekst(aantal) {
    if (!aantal) return 'nu niets in de bonus';
    if (aantal === 1) return 'nu 1 aanbieding';
    return `nu ${aantal} aanbiedingen`;
}

/**
 * Maakt van de losse regels uit de database afdelingen met hun groepen.
 *
 * De database levert per afdeling eerst de regel van de afdeling zelf (zonder
 * subgroep, met het totaal) en daarna zijn groepen op volgorde. Die volgorde
 * blijft hier staan: hij komt uit de indeling en is niet alfabetisch, zodat
 * verwante groepen bij elkaar blijven.
 */
function bouwAfdelingen(regels) {
    const perAfdeling = new Map();

    for (const regel of regels) {
        if (!regel.hoofdgroep) {
            continue;
        }
        if (!perAfdeling.has(regel.hoofdgroep)) {
            perAfdeling.set(regel.hoofdgroep, {
                naam: regel.hoofdgroep,
                aantal: 0,
                groepen: [],
            });
        }
        const afdeling = perAfdeling.get(regel.hoofdgroep);

        if (regel.subgroep) {
            afdeling.groepen.push({ naam: regel.subgroep, aantal: Number(regel.aantal) || 0 });
        } else {
            afdeling.aantal = Number(regel.aantal) || 0;
        }
    }

    return [...perAfdeling.values()];
}

/**
 * De afdelingen die bij het zoekwoord passen, met alleen de passende groepen.
 *
 * Past de afdelingsnaam zelf ("koffie" op "Koffie & thee"), dan blijven al zijn
 * groepen staan: je bent dan waarschijnlijk op zoek naar de hele afdeling en
 * wilt zien wat erin zit.
 */
function zoekInIndeling(woord) {
    const term = woord.trim().toLowerCase();
    if (term === '') {
        return afdelingen;
    }

    const treffers = [];
    for (const afdeling of afdelingen) {
        const afdelingPast = afdeling.naam.toLowerCase().includes(term);
        const groepen = afdelingPast
            ? afdeling.groepen
            : afdeling.groepen.filter((groep) => groep.naam.toLowerCase().includes(term));

        if (afdelingPast || groepen.length > 0) {
            treffers.push({ ...afdeling, groepen });
        }
    }
    return treffers;
}

/**
 * Eén aan te vinken regel: de hele afdeling, of één groep daarbinnen.
 *
 * Wat al in een zoekvraag zit, staat er wel bij maar is niet nog eens aan te
 * vinken — dat zou dezelfde zoekvraag dubbel opslaan.
 */
function maakKeuze(hoofdgroep, subgroep, naam, aantal) {
    const sleutel = sleutelVan(hoofdgroep, subgroep);
    const gevolgd = alGevolgd.has(sleutel);

    const regel = maak('li', subgroep ? 'keuze' : 'keuze afdelingbreed');
    const label = document.createElement('label');

    const vinkje = document.createElement('input');
    vinkje.type = 'checkbox';
    vinkje.checked = gekozen.has(sleutel);
    vinkje.disabled = gevolgd;
    vinkje.addEventListener('change', () => {
        if (vinkje.checked) {
            gekozen.set(sleutel, { hoofdgroep, subgroep });
        } else {
            gekozen.delete(sleutel);
        }
        toonGekozen();
    });

    label.append(vinkje, maak('span', 'keuzenaam', naam));
    label.append(maak('span', gevolgd ? 'keuzeaantal gevolgd' : 'keuzeaantal',
        gevolgd ? 'volg je al' : aantalTekst(aantal)));

    regel.append(label);
    return regel;
}

/** Tekent de indeling, gefilterd op wat er in het zoekveld staat. */
function toonIndeling() {
    const woord = zoekveld.value;
    const treffers = zoekInIndeling(woord);
    const zoekt = woord.trim() !== '';

    if (afdelingen.length === 0) {
        indelingsvak.replaceChildren();
        zoekhulp.textContent = 'De productgroepen konden niet worden opgehaald. '
            + 'Probeer de pagina te verversen.';
        return;
    }

    if (treffers.length === 0) {
        indelingsvak.replaceChildren();
        zoekhulp.textContent = `Geen afdeling of groep gevonden met "${woord.trim()}". `
            + 'Probeer een korter woord, of gebruik hieronder het veld Vrije tekst.';
        return;
    }

    zoekhulp.textContent = zoekt
        ? `${treffers.length} ${treffers.length === 1 ? 'afdeling' : 'afdelingen'} met een treffer.`
        : `${afdelingen.length} afdelingen. Klik een afdeling open, of typ een woord om te zoeken.`;

    indelingsvak.replaceChildren(...treffers.map((afdeling) => {
        const vak = maak('details', 'afdeling');
        // Bij zoeken staat alles open: je wilt de treffer meteen zien.
        vak.open = zoekt || openstaand.has(afdeling.naam);
        vak.addEventListener('toggle', () => {
            if (vak.open) {
                openstaand.add(afdeling.naam);
            } else {
                openstaand.delete(afdeling.naam);
            }
        });

        const kop = document.createElement('summary');
        kop.append(maak('span', 'afdelingnaam', afdeling.naam));
        kop.append(maak('span', 'keuzeaantal', aantalTekst(afdeling.aantal)));
        vak.append(kop);

        const keuzes = maak('ul', 'keuzes');
        keuzes.append(maakKeuze(afdeling.naam, null,
            `Alles uit ${afdeling.naam}`, afdeling.aantal));
        for (const groep of afdeling.groepen) {
            keuzes.append(maakKeuze(afdeling.naam, groep.naam, groep.naam, groep.aantal));
        }
        vak.append(keuzes);

        return vak;
    }));
}

/** De aangevinkte groepen boven het zoekveld, zodat je ze niet kwijtraakt. */
function toonGekozen() {
    const regels = [...gekozen.entries()].map(([sleutel, keuze]) => {
        const regel = maak('li', 'gekozen-groep');
        regel.append(maak('span', null, keuze.subgroep
            ? `${keuze.hoofdgroep} › ${keuze.subgroep}`
            : `${keuze.hoofdgroep} (hele afdeling)`));

        const weg = maak('button', 'weg', '×');
        weg.type = 'button';
        weg.title = 'Deze keuze weghalen';
        weg.addEventListener('click', () => {
            gekozen.delete(sleutel);
            toonGekozen();
            toonIndeling();
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

/** Haalt de indeling op; een storing hier mag de pagina niet blokkeren. */
async function laadIndeling() {
    try {
        const regels = await haalEigenIndeling();
        afdelingen = bouwAfdelingen(regels);
        console.info(`Dealbot — profiel: ${afdelingen.length} afdelingen geladen `
            + `met samen ${afdelingen.reduce((som, a) => som + a.groepen.length, 0)} groepen.`);
    } catch (fout) {
        afdelingen = [];
        console.error('Dealbot — indeling laden mislukt:', fout);
    }
    toonIndeling();
}

function toonZoekvragen(zoekvragen, herlaad) {
    // Wat al gevolgd wordt, mag niet nog eens aan te vinken zijn.
    alGevolgd = new Set(zoekvragen
        .filter((zoekvraag) => zoekvraag.hoofdgroep)
        .map((zoekvraag) => sleutelVan(zoekvraag.hoofdgroep, zoekvraag.subgroep)));

    if (zoekvragen.length === 0) {
        lijst.replaceChildren(maak('li', 'leeg-regel',
            'Je hebt nog geen zoekvragen. Kies er hieronder één.'));
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
    // De indeling moet mee: een groep die je net bent gaan volgen of hebt
    // weggehaald, hoort meteen als zodanig op het scherm te staan.
    toonIndeling();
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
 * Het zoeken en aanvinken binnen onze eigen indeling.
 *
 * Elke aangevinkte afdeling of groep wordt een eigen zoekvraag. Ze staan los van
 * elkaar en tellen bij elkaar op, dus je kunt in één handeling drie soorten
 * tegelijk in de gaten laten houden — bij alle winkels.
 */
function koppelGroepkiezer() {
    zoekveld.addEventListener('input', toonIndeling);

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

        const nieuwe = [...gekozen.values()].map((keuze) => ({
            hoofdgroep: keuze.hoofdgroep,
            subgroep: keuze.subgroep,
        }));

        try {
            const opgeslagen = await voegZoekvragenToe(nieuwe);
            gekozen.clear();
            zoekveld.value = '';
            toonGekozen();
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

    // Eerst de zoekvragen, dan de indeling: pas als bekend is wat er al gevolgd
    // wordt, kan de indeling dat erbij zetten.
    await ververs();
    await laadIndeling();
}

bouwPagina();
