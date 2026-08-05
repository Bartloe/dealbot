/**
 * =============================================================================
 *  Dealbot — de winkelpagina
 *
 *  Versie      : 1.0
 *  Reden       : Nieuwe pagina. Naast je eigen zoekvragen wil je soms gewoon
 *                zien wat er déze week bij één winkel ligt — zoals je door een
 *                folder bladert, maar dan geordend per productgroep.
 *  Datum       : 03-08-2026 21:20
 *
 *  De winkel kies je door op zijn logo te klikken; die keuze komt achter het
 *  adres te staan (winkel.html#jumbo), zodat verversen je op dezelfde winkel
 *  laat staan en de link te bewaren is.
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en zet de winkelstrook neer
 *    maakTegel()       - één winkel als logo om op te klikken
 *    kiesWinkel()      - haalt de aanbiedingen van die winkel op en toont ze
 *    toonGroepen()     - de aanbiedingen gebundeld per productgroep
 *    maakRegel()       - één aanbieding als regel binnen een groep
 * =============================================================================
 */

import { haalWinkels, telAanbiedingen, haalWinkelAanbiedingen, DealbotFout } from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { euro, kiloprijsTekst, geldigheidTekst, productTitel } from './opmaak.js';

const kiezer = document.getElementById('winkelkiezer');
const samenvatting = document.getElementById('samenvatting');
const groepknoppen = document.getElementById('groepknoppen');
const melding = document.getElementById('melding');
const lijst = document.getElementById('lijst');

// Het logo per winkel. Staat er geen bestand bij een winkel, of laadt het niet,
// dan komt de naam in beeld — een winkel zonder logo mag geen leeg vlak worden.
const LOGOS = {
    ah: 'assets/logos/ah.png',
    jumbo: 'assets/logos/jumbo.png',
    dirk: 'assets/logos/dirk.png',
    vomar: 'assets/logos/vomar.png',
    lidl: 'assets/logos/lidl.svg',
    picnic: 'assets/logos/picnic.png',
};

// Tot en met dit aantal groepen staat alles meteen open. Daarboven — Albert
// Heijn en Jumbo hebben er honderden — zijn de groepen dichtgeklapt, zodat je
// eerst een overzicht van de productgroepen ziet in plaats van duizend regels.
const GROEPEN_OPEN_TOT = 12;

// De groep waar de aanbiedingen in vallen die de winkel niet heeft ingedeeld.
const OVERIG = 'Overig';

let gekozenWinkel = null;

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

// -- de winkelstrook ---------------------------------------------------------

/**
 * Eén winkel als knop met zijn logo erop.
 *
 * Onder het logo staat hoeveel er deze week ligt. Is dat nul, dan blijft de
 * winkel gewoon te kiezen: je krijgt dan een duidelijke melding in plaats van
 * een knop die niets doet.
 */
function maakTegel(winkel) {
    const tegel = maak('button', 'winkeltegel');
    tegel.type = 'button';
    tegel.dataset.code = winkel.code;

    const logo = LOGOS[winkel.code];
    if (logo) {
        const plaatje = document.createElement('img');
        plaatje.src = logo;
        plaatje.alt = winkel.naam;
        // Ontbreekt het bestand, dan komt de naam ervoor in de plaats.
        plaatje.addEventListener('error', () => {
            plaatje.replaceWith(maak('span', 'winkelnaam', winkel.naam));
        });
        tegel.append(plaatje);
    } else {
        tegel.append(maak('span', 'winkelnaam', winkel.naam));
    }

    const aantal = maak('span', 'winkelaantal', '…');
    tegel.append(aantal);

    tegel.addEventListener('click', () => {
        window.location.hash = winkel.code;
        kiesWinkel(winkel);
    });

    // Het aantal komt na de tegel binnen: de strook moet meteen staan, ook als
    // het tellen nog loopt of niet lukt.
    telAanbiedingen(winkel.id).then((gevonden) => {
        if (gevonden === null) {
            aantal.textContent = '';
            return;
        }
        aantal.textContent = gevonden === 1 ? '1 aanbieding' : `${gevonden} aanbiedingen`;
        if (gevonden === 0) {
            tegel.classList.add('leegwinkel');
        }
    });

    return tegel;
}

/** Zet de gekozen winkel in de strook in beeld. */
function markeerKeuze(code) {
    for (const tegel of kiezer.querySelectorAll('.winkeltegel')) {
        const gekozen = tegel.dataset.code === code;
        tegel.classList.toggle('gekozen', gekozen);
        tegel.setAttribute('aria-pressed', gekozen ? 'true' : 'false');
    }
}

// -- de aanbiedingen ---------------------------------------------------------

/** Eén aanbieding als regel binnen zijn productgroep. */
function maakRegel(aanbieding) {
    const regel = maak('li', 'winkelregel');

    if (aanbieding.afbeelding_url) {
        const plaatje = document.createElement('img');
        plaatje.src = aanbieding.afbeelding_url;
        plaatje.alt = '';
        plaatje.loading = 'lazy';
        // Een kapotte link naar een plaatje mag geen gat in de pagina slaan.
        plaatje.addEventListener('error', () => plaatje.remove());
        regel.append(plaatje);
    }

    const tekst = maak('div', 'regeltekst');

    // Een link naar de winkel als die er is; anders gewoon de naam.
    if (aanbieding.product_url) {
        const link = maak('a', 'regelnaam', productTitel(aanbieding));
        link.href = aanbieding.product_url;
        link.target = '_blank';
        link.rel = 'noopener';
        tekst.append(link);
    } else {
        tekst.append(maak('span', 'regelnaam', productTitel(aanbieding)));
    }

    const onder = maak('div', 'regeldetails');

    if (aanbieding.prijs !== null && aanbieding.prijs !== undefined) {
        onder.append(maak('strong', 'prijs', euro(aanbieding.prijs)));
    }
    if (aanbieding.normale_prijs && aanbieding.normale_prijs !== aanbieding.prijs) {
        onder.append(maak('s', 'oude-prijs', euro(aanbieding.normale_prijs)));
    }
    if (aanbieding.actie_tekst) {
        onder.append(maak('span', 'actie', aanbieding.actie_tekst));
    }

    const kiloprijs = kiloprijsTekst(aanbieding);
    onder.append(maak(
        'span',
        kiloprijs === 'kiloprijs onbekend' ? 'kiloprijs onbekend' : 'kiloprijs',
        kiloprijs,
    ));

    const geldig = geldigheidTekst(aanbieding);
    if (geldig) {
        onder.append(maak('span', 'geldig', geldig));
    }

    tekst.append(onder);
    regel.append(tekst);
    return regel;
}

/**
 * Bundelt de aanbiedingen per productgroep.
 *
 * De database levert ze al op volgorde van groep, en daarbinnen van goedkoop
 * naar duur per kilo. Wat de winkel niet heeft ingedeeld komt onder "Overig"
 * te staan, helemaal onderaan — dat is een restje, geen productgroep.
 */
function bundelPerGroep(aanbiedingen) {
    const groepen = new Map();

    for (const aanbieding of aanbiedingen) {
        const naam = (aanbieding.productgroep || '').trim() || OVERIG;
        if (!groepen.has(naam)) {
            groepen.set(naam, []);
        }
        groepen.get(naam).push(aanbieding);
    }

    return [...groepen.entries()]
        .map(([naam, regels]) => ({ naam, regels }))
        .sort((a, b) => {
            if (a.naam === OVERIG) return 1;
            if (b.naam === OVERIG) return -1;
            return a.naam.localeCompare(b.naam, 'nl');
        });
}

/** Zet de gebundelde aanbiedingen op het scherm, elke groep in te klappen. */
function toonGroepen(winkel, aanbiedingen) {
    const groepen = bundelPerGroep(aanbiedingen);
    const openVanzelf = groepen.length <= GROEPEN_OPEN_TOT;

    samenvatting.textContent = `${winkel.naam}: ${aanbiedingen.length} aanbiedingen `
        + `in ${groepen.length} ${groepen.length === 1 ? 'productgroep' : 'productgroepen'}, `
        + 'per groep van goedkoop naar duur per kilo.';
    samenvatting.hidden = false;
    groepknoppen.hidden = groepen.length <= 1;

    const blokken = groepen.map((groep) => {
        const blok = document.createElement('details');
        blok.className = 'groepblok';

        const kop = document.createElement('summary');
        kop.append(maak('span', 'groepnaam', groep.naam));
        kop.append(maak('span', 'groepaantal', String(groep.regels.length)));
        blok.append(kop);

        const regels = maak('ul', 'winkelregels');
        blok.append(regels);

        // De regels worden pas gemaakt zodra de groep opengaat. Albert Heijn
        // heeft er ruim vierduizend; die allemaal ineens neerzetten maakt de
        // pagina traag, terwijl je er hooguit een paar groepen van opent.
        const vul = () => {
            if (blok.open && regels.childElementCount === 0) {
                regels.append(...groep.regels.map(maakRegel));
            }
        };

        blok.addEventListener('toggle', vul);
        blok.open = openVanzelf;
        vul();

        return blok;
    });

    lijst.replaceChildren(...blokken);
}

/** Wat er staat als een winkel deze week niets heeft liggen. */
function toonLeeg(winkel) {
    const kaart = maak('div', 'leeg');
    kaart.append(maak('h2', null, `Niets gevonden bij ${winkel.naam}`));
    kaart.append(maak('p', null,
        'Voor deze winkel staan er op dit moment geen aanbiedingen in Dealbot. '
        + 'Dat kan kloppen — niet elke winkel levert elke week iets aan. Kies '
        + 'hierboven een andere winkel.'));
    lijst.replaceChildren(kaart);
}

/**
 * Haalt de aanbiedingen van één winkel op en zet ze op het scherm.
 *
 * De grootste winkel heeft er ruim twaalfhonderd; dat duurt even, dus staat er
 * eerst een regel dat het ophalen loopt.
 */
async function kiesWinkel(winkel) {
    gekozenWinkel = winkel;
    markeerKeuze(winkel.code);
    toonMelding('');
    samenvatting.hidden = true;
    groepknoppen.hidden = true;
    lijst.replaceChildren(maak('p', 'bezig', `Aanbiedingen van ${winkel.naam} ophalen…`));

    try {
        const aanbiedingen = await haalWinkelAanbiedingen(winkel.id);

        // Ondertussen op een andere winkel geklikt: dan is dit antwoord oud nieuws.
        if (gekozenWinkel !== winkel) {
            return;
        }

        console.info(`Dealbot — winkelpagina: ${aanbiedingen.length} aanbiedingen bij ${winkel.naam}.`);

        if (aanbiedingen.length === 0) {
            toonLeeg(winkel);
            return;
        }

        toonGroepen(winkel, aanbiedingen);
    } catch (fout) {
        if (gekozenWinkel !== winkel) {
            return;
        }
        lijst.replaceChildren();
        if (fout instanceof DealbotFout) {
            toonMelding(fout.message);
        } else {
            console.error('Dealbot — aanbiedingen van de winkel ophalen mislukt:', fout);
            toonMelding('De aanbiedingen konden niet worden opgehaald. Probeer het later nog eens.');
        }
    }
}

/** Klapt alle groepen open of dicht. */
function zetAlleGroepen(open) {
    for (const blok of lijst.querySelectorAll('details.groepblok')) {
        blok.open = open;
    }
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    let winkels;
    try {
        winkels = await haalWinkels();
    } catch (fout) {
        console.error('Dealbot — winkels ophalen mislukt:', fout);
        toonMelding(fout instanceof DealbotFout
            ? fout.message
            : 'De winkels konden niet worden opgehaald. Probeer het later nog eens.');
        return;
    }

    if (winkels.length === 0) {
        toonMelding('Er staan nog geen winkels in Dealbot.', 'goed');
        return;
    }

    kiezer.replaceChildren(...winkels.map(maakTegel));

    document.getElementById('allesuit').addEventListener('click', () => zetAlleGroepen(true));
    document.getElementById('allesin').addEventListener('click', () => zetAlleGroepen(false));

    // Terug op deze pagina komen met een winkel achter het adres — of de knop
    // "vorige" gebruiken — brengt je bij diezelfde winkel.
    window.addEventListener('hashchange', () => {
        const winkel = winkels.find((w) => w.code === window.location.hash.slice(1));
        if (winkel && winkel !== gekozenWinkel) {
            kiesWinkel(winkel);
        }
    });

    const uitAdres = winkels.find((w) => w.code === window.location.hash.slice(1));
    kiesWinkel(uitAdres || winkels[0]);
}

bouwPagina();
