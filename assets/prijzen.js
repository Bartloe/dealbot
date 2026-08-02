/**
 * =============================================================================
 *  Dealbot — de standaardprijzen-pagina
 *
 *  Versie      : 1.0
 *  Reden       : Nieuwe pagina. Naast de weekaanbiedingen wil je kunnen zien wat
 *                iets gewoon kost. Vomar publiceert zijn hele assortiment met
 *                vaste prijzen; dat is de vulling van deze pagina.
 *  Datum       : 02-08-2026 13:30
 *
 *  Er staan ruim zesduizend producten in de database. Die worden bewust niet in
 *  één keer opgehaald: de pagina vraagt eerst om een zoekterm of een groep, en
 *  haalt dan alleen dat stukje op.
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en vult het keuzemenu
 *    vulGroepen()      - zet de productgroepen in de keuzelijst
 *    zoek()            - haalt op wat bij de invoer past en toont het
 *    maakProduct()     - één product als kaart op het scherm
 *    toonLeeg()        - wat je ziet vóór het zoeken en bij nul treffers
 * =============================================================================
 */

import { haalPrijsgroepen, zoekStandaardprijzen, DealbotFout } from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { euro, kiloprijsTekst, productTitel } from './opmaak.js';

const zoekterm = document.getElementById('zoekterm');
const groepskeuze = document.getElementById('groep');
const samenvatting = document.getElementById('samenvatting');
const melding = document.getElementById('melding');
const lijst = document.getElementById('lijst');

// Zoeken tijdens het typen, maar niet bij élke toetsaanslag: pas als iemand
// even ophoudt. Anders staat er een vraag aan de database per letter.
const TYPEPAUZE = 350;
let typeklok = null;

// Elke zoekopdracht krijgt een nummer. Komt een ouder antwoord later binnen dan
// een nieuwer, dan wordt het genegeerd — anders zie je de treffers van een
// zoekterm die je al weer weggetypt hebt.
let laatsteVraag = 0;

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

/** De inhoud als "500 gram", of een lege tekst als die onbekend is. */
function inhoudTekst(product) {
    const waarde = Number(product.inhoud_waarde);
    if (!Number.isFinite(waarde) || waarde <= 0 || !product.inhoud_eenheid) {
        return '';
    }
    // 500.000 uit de database is gewoon 500; hele getallen zonder komma tonen.
    const netjes = Number.isInteger(waarde) ? waarde : Number(waarde.toFixed(3));
    return `${netjes} ${product.inhoud_eenheid}`;
}

/** Eén product als kaart. */
function maakProduct(product) {
    const kaart = maak('article', 'product');
    const kop = maak('div', 'producttop');

    if (product.afbeelding_url) {
        const plaatje = document.createElement('img');
        plaatje.src = product.afbeelding_url;
        plaatje.alt = '';
        plaatje.loading = 'lazy';
        // Een kapotte link naar een plaatje mag geen gat in de pagina slaan.
        plaatje.addEventListener('error', () => plaatje.remove());
        kop.append(plaatje);
    }

    const tekst = maak('div', 'producttekst');
    tekst.append(maak('h2', null, productTitel(product)));

    const inhoud = inhoudTekst(product);
    if (inhoud) {
        tekst.append(maak('p', 'aantal', inhoud));
    }
    if (product.productgroep) {
        tekst.append(maak('p', 'groep', product.productgroep));
    }

    kop.append(tekst);
    kaart.append(kop);

    const regel = maak('div', 'prijsregel');
    if (product.prijs !== null && product.prijs !== undefined) {
        regel.append(maak('strong', 'prijs', euro(product.prijs)));
    }

    const kiloprijs = kiloprijsTekst(product);
    regel.append(maak(
        'span',
        kiloprijs === 'kiloprijs onbekend' ? 'kiloprijs onbekend' : 'kiloprijs',
        kiloprijs,
    ));

    if (product.product_url) {
        const link = maak('a', 'winkellink', 'Bekijk in de winkel');
        link.href = product.product_url;
        link.target = '_blank';
        link.rel = 'noopener';
        regel.append(link);
    }

    kaart.append(regel);
    return kaart;
}

/**
 * Wat er staat als er niets te tonen is.
 *
 * Twee verschillende situaties: nog niets ingevuld, of wel gezocht maar niets
 * gevonden. Die verdienen een andere tekst.
 */
function toonLeeg(heeftGezocht) {
    const kaart = maak('div', 'leeg');

    if (!heeftGezocht) {
        kaart.append(maak('h2', null, 'Waar ben je naar op zoek?'));
        kaart.append(maak('p', null,
            'Typ hierboven een merk of een productnaam, of kies een productgroep. '
            + 'Dan verschijnen hier de gewone winkelprijzen, van goedkoop naar duur '
            + 'per kilo.'));
    } else {
        kaart.append(maak('h2', null, 'Niets gevonden'));
        kaart.append(maak('p', null,
            'Er is geen product dat hierbij past. Probeer een korter woord, of kies '
            + 'een productgroep uit de lijst.'));
    }

    lijst.replaceChildren(kaart);
}

/**
 * Haalt op wat bij de huidige invoer past en zet het op het scherm.
 *
 * Zoekterm en groep werken samen: vul je allebei in, dan moet een product aan
 * allebei voldoen.
 */
async function zoek() {
    const tekst = zoekterm.value.trim();
    const groep = groepskeuze.value;
    const vraagnummer = ++laatsteVraag;

    toonMelding('');

    if (!tekst && !groep) {
        samenvatting.hidden = true;
        toonLeeg(false);
        return;
    }

    lijst.replaceChildren(maak('p', 'bezig', 'Prijzen ophalen…'));

    try {
        const producten = await zoekStandaardprijzen({ groep, tekst });

        // Een antwoord op een inmiddels achterhaalde vraag negeren we.
        if (vraagnummer !== laatsteVraag) {
            return;
        }

        if (producten.length === 0) {
            samenvatting.hidden = true;
            toonLeeg(true);
            return;
        }

        samenvatting.textContent = producten.length === 1
            ? '1 product gevonden.'
            : `${producten.length} producten gevonden, van goedkoop naar duur per kilo.`;
        samenvatting.hidden = false;

        lijst.replaceChildren(...producten.map(maakProduct));
    } catch (fout) {
        if (vraagnummer !== laatsteVraag) {
            return;
        }
        lijst.replaceChildren();
        samenvatting.hidden = true;
        if (fout instanceof DealbotFout) {
            toonMelding(fout.message);
        } else {
            console.error('Dealbot — standaardprijzen ophalen mislukt:', fout);
            toonMelding('De prijzen konden niet worden opgehaald. Probeer het later nog eens.');
        }
    }
}

/**
 * Zet de productgroepen in de keuzelijst, gebundeld per afdeling.
 *
 * Lukt dat niet, dan blijft alleen het zoekveld over. Dat is jammer maar geen
 * reden om de hele pagina te laten struikelen.
 */
async function vulGroepen() {
    let groepen;
    try {
        groepen = await haalPrijsgroepen();
    } catch (fout) {
        console.error('Dealbot — productgroepen niet opgehaald:', fout);
        groepskeuze.disabled = true;
        return;
    }

    const perAfdeling = new Map();
    for (const groep of groepen) {
        const afdeling = groep.afdeling || 'Overig';
        if (!perAfdeling.has(afdeling)) {
            perAfdeling.set(afdeling, []);
        }
        perAfdeling.get(afdeling).push(groep);
    }

    for (const [afdeling, inhoud] of perAfdeling) {
        const blok = document.createElement('optgroup');
        blok.label = afdeling;
        for (const groep of inhoud) {
            const keuze = document.createElement('option');
            keuze.value = groep.productgroep;
            keuze.textContent = `${groep.productgroep} (${groep.aantal})`;
            blok.append(keuze);
        }
        groepskeuze.append(blok);
    }

    console.info(`Dealbot — standaardprijzen: ${groepen.length} productgroepen in de lijst.`);
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    toonLeeg(false);
    await vulGroepen();

    zoekterm.addEventListener('input', () => {
        clearTimeout(typeklok);
        typeklok = setTimeout(zoek, TYPEPAUZE);
    });

    // Enter niet afwachten: meteen zoeken.
    zoekterm.addEventListener('keydown', (gebeurtenis) => {
        if (gebeurtenis.key === 'Enter') {
            gebeurtenis.preventDefault();
            clearTimeout(typeklok);
            zoek();
        }
    });

    groepskeuze.addEventListener('change', () => {
        clearTimeout(typeklok);
        zoek();
    });
}

bouwPagina();
