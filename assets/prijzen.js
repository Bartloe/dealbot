/**
 * =============================================================================
 *  Dealbot — de standaardprijzen-pagina
 *
 *  Versie      : 3.0
 *  Reden       : De verfijningsknopjes stonden op de groepsnaam van de winkel
 *                zelf. Voor hetzelfde vochtige toiletpapier kreeg je er daardoor
 *                drie naast elkaar — "Toiletpapier Vochtig", "Toiletpapier -
 *                vochtig" en "vochtig toiletpapier" — en elk knopje verborg de
 *                producten van de andere twee ketens.
 *
 *                Ze staan nu op het kenmerk: één woord in onze eigen taal, dat
 *                bij het indelen uit die winkelnamen is overgehouden. Eén knopje
 *                "vochtig" laat dus alle winkels tegelijk zien, precies zoals de
 *                keuzelijst erboven dat al deed. Het is bovendien hetzelfde
 *                knopje als op het profielscherm: wat je hier ziet, kun je daar
 *                gaan volgen.
 *  Datum       : 05-08-2026 16:00
 *
 *  Er staan ruim zesduizend producten in de database. Die worden bewust niet in
 *  één keer opgehaald: de pagina vraagt eerst om een zoekterm of een lade, en
 *  haalt dan alleen dat stukje op.
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en vult het keuzemenu
 *    vulIndeling()     - zet onze afdelingen en laden in de keuzelijst
 *    zoek()            - haalt op wat bij de invoer past
 *    toonUitkomst()    - tekent de verfijningsknopjes en de lijst
 *    telKenmerken()    - welke kenmerken zitten er in de uitkomst
 *    maakVerfijning()  - de knopjes waarmee je binnen een lade verfijnt
 *    maakProduct()     - één product als kaart op het scherm
 *    toonLeeg()        - wat je ziet vóór het zoeken en bij nul treffers
 * =============================================================================
 */

import {
    haalPrijsindeling, zoekStandaardprijzen, PRIJZEN_MAXIMUM, DealbotFout,
} from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { euro, kiloprijsTekst, productTitel } from './opmaak.js';

const zoekterm = document.getElementById('zoekterm');
const groepskeuze = document.getElementById('groep');
const verfijning = document.getElementById('verfijning');
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

// De regels uit onze indeling zoals ze in de keuzelijst staan. De keuzelijst
// bewaart alleen het nummer van de regel: een afdeling en een lade samen in één
// tekstwaarde proppen vraagt om gedoe met scheidingstekens.
let keuzes = [];

// Wat er nu op het scherm staat, en op welke winkelgroep daarbinnen verfijnd is.
// Die verfijning gebeurt in het scherm zelf: de producten zijn al opgehaald, dus
// een tweede vraag aan de database zou alleen maar vertraging opleveren.
let gevonden = [];
let verfijndOp = null;

// Producten waarvan het kenmerk niet bekend is, vallen onder dit knopje. Ze
// horen wél in de lade — er is alleen niets naders over te zeggen.
const ZONDER_KENMERK = 'overig';

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
            'Typ hierboven een merk of een productnaam, of kies een afdeling of lade. '
            + 'Dan verschijnen hier de gewone winkelprijzen, van goedkoop naar duur '
            + 'per kilo.'));
    } else {
        kaart.append(maak('h2', null, 'Niets gevonden'));
        kaart.append(maak('p', null,
            'Er is geen product dat hierbij past. Probeer een korter woord, of kies '
            + 'een lade uit de lijst.'));
    }

    lijst.replaceChildren(kaart);
}

/**
 * Welke kenmerken zitten er in deze uitkomst, en hoeveel producten hebben ze?
 *
 * Dit is de bron van de verfijningsknopjes. Het kenmerk is de derde laag onder
 * onze indeling: één woord in onze eigen taal, dat bij het indelen is
 * overgehouden uit de groepsnamen van de winkels. Daardoor staat er één knopje
 * "vochtig" in plaats van drie winkelvarianten van hetzelfde.
 *
 * Wat geen kenmerk heeft, komt onder "overig" te staan en verdwijnt dus niet:
 * het ligt gewoon in de lade, we weten er alleen niets naders van.
 *
 * De grootste groep staat voorop; bij gelijk aantal op alfabet, zodat de volgorde
 * niet verspringt tussen twee zoekopdrachten.
 */
function telKenmerken(producten) {
    const teller = new Map();
    for (const product of producten) {
        const naam = (product.kenmerk || '').trim() || ZONDER_KENMERK;
        teller.set(naam, (teller.get(naam) || 0) + 1);
    }
    return [...teller.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'nl'));
}

/** Eén knopje, dat de lijst verfijnt op één kenmerk. */
function maakKnopje(naam, aantal, actief) {
    const knop = maak('button', `chip${actief ? ' actief' : ''}`);
    knop.type = 'button';
    knop.setAttribute('aria-pressed', String(actief));
    knop.append(maak('span', 'chipnaam', naam));
    knop.append(maak('span', 'chipaantal', String(aantal)));

    knop.addEventListener('click', () => {
        // Nog een keer op hetzelfde knopje betekent: laat weer alles zien.
        verfijndOp = (verfijndOp === naam) ? null : naam;
        toonUitkomst();
    });

    return knop;
}

/**
 * De rij knopjes boven de lijst.
 *
 * Blijft weg als er maar één kenmerk in de uitkomst zit: dan valt er niets te
 * verfijnen en zou de rij alleen maar afleiden.
 */
function maakVerfijning(groepen) {
    verfijning.replaceChildren();

    if (groepen.length < 2) {
        verfijning.hidden = true;
        return;
    }

    const alles = maak('button', `chip${verfijndOp === null ? ' actief' : ''}`);
    alles.type = 'button';
    alles.setAttribute('aria-pressed', String(verfijndOp === null));
    alles.append(maak('span', 'chipnaam', 'alles'));
    alles.append(maak('span', 'chipaantal', String(gevonden.length)));
    alles.addEventListener('click', () => {
        verfijndOp = null;
        toonUitkomst();
    });
    verfijning.append(alles);

    for (const [naam, aantal] of groepen) {
        verfijning.append(maakKnopje(naam, aantal, verfijndOp === naam));
    }

    verfijning.hidden = false;
}

/**
 * Zet de gevonden producten op het scherm, met de verfijning erboven.
 *
 * Wordt zowel na een nieuwe zoekopdracht aangeroepen als na een klik op een
 * knopje. In dat tweede geval gaat er geen vraag naar de database: de producten
 * liggen er al.
 */
function toonUitkomst() {
    if (gevonden.length === 0) {
        verfijning.hidden = true;
        samenvatting.hidden = true;
        toonLeeg(true);
        return;
    }

    maakVerfijning(telKenmerken(gevonden));

    const tonen = verfijndOp === null
        ? gevonden
        : gevonden.filter(
            (p) => ((p.kenmerk || '').trim() || ZONDER_KENMERK) === verfijndOp,
        );

    const aantalTekst = tonen.length === 1
        ? '1 product gevonden.'
        : `${tonen.length} producten gevonden, van goedkoop naar duur per kilo.`;

    // De database geeft niet meer dan deze grens terug. Dat hoort de gebruiker te
    // weten: anders lijkt een afgekapte lijst gewoon de hele lijst.
    const afgekapt = gevonden.length >= PRIJZEN_MAXIMUM
        ? ' Er zijn er mogelijk meer; verfijn met een zoekwoord.'
        : '';

    samenvatting.textContent = aantalTekst + afgekapt;
    samenvatting.hidden = false;

    lijst.replaceChildren(...tonen.map(maakProduct));
}

/**
 * Haalt op wat bij de huidige invoer past en zet het op het scherm.
 *
 * Zoekterm en keuze werken samen: vul je allebei in, dan moet een product aan
 * allebei voldoen. Een nieuwe zoekopdracht laat de verfijning los — die hoort bij
 * de vorige uitkomst en zou anders stilletjes producten wegfilteren.
 */
async function zoek() {
    const tekst = zoekterm.value.trim();
    // De eerste keuze heeft nummer 0, en de regel "kies een afdeling of lade"
    // heeft een lege waarde. Zonder deze controle zou die lege waarde als nul
    // gelezen worden en dus stilzwijgend de eerste afdeling openen.
    const keuze = groepskeuze.value === '' ? null : keuzes[Number(groepskeuze.value)] || null;
    const vraagnummer = ++laatsteVraag;

    toonMelding('');
    verfijndOp = null;

    if (!tekst && !keuze) {
        gevonden = [];
        verfijning.hidden = true;
        samenvatting.hidden = true;
        toonLeeg(false);
        return;
    }

    verfijning.hidden = true;
    lijst.replaceChildren(maak('p', 'bezig', 'Prijzen ophalen…'));

    try {
        const producten = await zoekStandaardprijzen({
            hoofdgroep: keuze ? keuze.hoofdgroep : '',
            subgroep: keuze ? keuze.subgroep : '',
            zonderIndeling: Boolean(keuze && keuze.zonderIndeling),
            tekst,
        });

        // Een antwoord op een inmiddels achterhaalde vraag negeren we.
        if (vraagnummer !== laatsteVraag) {
            return;
        }

        gevonden = producten;
        toonUitkomst();
    } catch (fout) {
        if (vraagnummer !== laatsteVraag) {
            return;
        }
        gevonden = [];
        lijst.replaceChildren();
        verfijning.hidden = true;
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
 * Zet onze afdelingen en laden in de keuzelijst.
 *
 * Elke afdeling wordt een kopje met daaronder eerst "alles" en daarna zijn laden.
 * De restbak — producten die nog nergens onder hangen — komt onderaan te staan:
 * dat is een achtste van het assortiment en die horen vindbaar te blijven.
 *
 * Lukt het ophalen niet, dan blijft alleen het zoekveld over. Dat is jammer maar
 * geen reden om de hele pagina te laten struikelen.
 */
async function vulIndeling() {
    let regels;
    try {
        regels = await haalPrijsindeling();
    } catch (fout) {
        console.error('Dealbot — de indeling is niet opgehaald:', fout);
        groepskeuze.disabled = true;
        return;
    }

    const perAfdeling = new Map();
    const restbak = [];

    for (const regel of regels) {
        if (!regel.hoofdgroep) {
            restbak.push(regel);
            continue;
        }
        if (!perAfdeling.has(regel.hoofdgroep)) {
            perAfdeling.set(regel.hoofdgroep, []);
        }
        perAfdeling.get(regel.hoofdgroep).push(regel);
    }

    /** Zet één regel als keuze in de lijst en onthoudt waar hij voor staat. */
    const voegToe = (blok, label, keuze) => {
        const optie = document.createElement('option');
        optie.value = String(keuzes.length);
        optie.textContent = label;
        blok.append(optie);
        keuzes.push(keuze);
    };

    for (const [afdeling, regelsVanAfdeling] of perAfdeling) {
        const blok = document.createElement('optgroup');
        blok.label = afdeling;

        for (const regel of regelsVanAfdeling) {
            if (regel.subgroep) {
                voegToe(blok, `${regel.subgroep} (${regel.aantal})`,
                    { hoofdgroep: afdeling, subgroep: regel.subgroep });
            } else {
                voegToe(blok, `Hele afdeling (${regel.aantal})`,
                    { hoofdgroep: afdeling, subgroep: '' });
            }
        }

        groepskeuze.append(blok);
    }

    for (const regel of restbak) {
        const blok = document.createElement('optgroup');
        blok.label = 'Overig';
        voegToe(blok, `Nog niet ingedeeld (${regel.aantal})`,
            { hoofdgroep: '', subgroep: '', zonderIndeling: true });
        groepskeuze.append(blok);
    }

    console.info(`Dealbot — standaardprijzen: ${keuzes.length} keuzes in de lijst.`);
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    toonLeeg(false);
    await vulIndeling();

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
