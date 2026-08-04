/**
 * =============================================================================
 *  Dealbot — aanbiedingen leesbaar maken
 *
 *  Versie      : 1.4
 *  Reden       : De startpagina zet de gevonden producten voortaan onder de
 *                afdeling en de lade waar ze in onze eigen indeling thuishoren,
 *                zodat een lange lijst leesbaar blijft.
 *  Datum       : 04-08-2026 12:05
 *
 *  Onderdelen:
 *    euro()               - bedrag als € 1,29
 *    kiloprijsTekst()     - "€ 2,58 per kilo" of "kiloprijs onbekend"
 *    geldigheidTekst()    - "geldig t/m 3 augustus"
 *    momentTekst()        - een tijdstip als "01-08  07:12"
 *    productTitel()       - merk en productnaam netjes achter elkaar
 *    groepeerPerProduct() - aanbiedingen van hetzelfde product bij elkaar
 *    bundelPerIndeling()  - die producten onder hun afdeling en lade
 *    zoekvraagTekst()     - een zoekvraag in één leesbare regel
 * =============================================================================
 */

const BEDRAG = new Intl.NumberFormat('nl-NL', {
    style: 'currency',
    currency: 'EUR',
});

const DATUM = new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'long' });

// Altijd Nederlandse tijd: de aanbiedingen zijn Nederlands, dus een gebruiker
// op vakantie hoort niet ineens een ander tijdstip te zien.
const MOMENT = new Intl.DateTimeFormat('nl-NL', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Amsterdam',
});

// De database rekent alles om naar kilo, liter of stuk.
const EENHEDEN = { kg: 'per kilo', l: 'per liter', stuk: 'per stuk' };

export function euro(bedrag) {
    if (bedrag === null || bedrag === undefined || bedrag === '') {
        return '';
    }
    const getal = Number(bedrag);
    return Number.isFinite(getal) ? BEDRAG.format(getal) : '';
}

/**
 * De prijs per kilo of liter. Is die niet bekend, dan zegt het scherm dat
 * eerlijk in plaats van het veld leeg te laten.
 */
export function kiloprijsTekst(aanbieding) {
    const prijs = Number(aanbieding.prijs_per_eenheid);
    if (!Number.isFinite(prijs) || prijs <= 0) {
        return 'kiloprijs onbekend';
    }
    const eenheid = EENHEDEN[aanbieding.eenheid_norm] || 'per eenheid';
    return `${euro(prijs)} ${eenheid}`;
}

/**
 * Een tijdstip uit de database als "01-08  07:12".
 *
 * Geeft een lege tekst terug als er niets bruikbaars in zit; het scherm laat de
 * regel dan gewoon weg in plaats van "Invalid Date" te tonen.
 */
export function momentTekst(moment) {
    if (!moment) {
        return '';
    }
    const datum = new Date(moment);
    if (Number.isNaN(datum.getTime())) {
        return '';
    }
    // Intl zet er "01-08, 07:12" van; de komma mag eruit.
    return MOMENT.format(datum).replace(',', ' ');
}

export function geldigheidTekst(aanbieding) {
    if (!aanbieding.geldig_tot) {
        return '';
    }
    const datum = new Date(aanbieding.geldig_tot);
    return Number.isNaN(datum.getTime()) ? '' : `geldig t/m ${DATUM.format(datum)}`;
}

export function productTitel(aanbieding) {
    const merk = (aanbieding.merk || '').trim();
    const naam = (aanbieding.product_naam || '').trim();

    // Staat het merk al vooraan in de naam, dan niet nog eens herhalen.
    if (merk && !naam.toLowerCase().startsWith(merk.toLowerCase())) {
        return `${merk} ${naam}`;
    }
    return naam || merk;
}

/**
 * Zet de platte lijst om in groepen van hetzelfde product.
 *
 * De database levert de aanbiedingen al gesorteerd van goedkoop naar duur, dus
 * de eerste van elke groep is de beste koop. De groepen zelf komen op
 * alfabetische volgorde, zodat de lijst niet elke dag anders oogt.
 *
 * Per groep wordt ook bepaald of de prijzen eerlijk te vergelijken zijn. Staat
 * er bijvoorbeeld een losse pot koffie (prijs per kilo) naast een voordeelpak
 * (prijs per stuk), dan zijn dat appels en peren en wordt er geen "beste prijs"
 * aangewezen; anders zou het scherm iets aanraden dat het niet waar kan maken.
 */
export function groepeerPerProduct(aanbiedingen) {
    const groepen = new Map();

    for (const aanbieding of aanbiedingen) {
        const sleutel = aanbieding.product_sleutel || `los-${aanbieding.id}`;
        if (!groepen.has(sleutel)) {
            groepen.set(sleutel, []);
        }
        groepen.get(sleutel).push(aanbieding);
    }

    return [...groepen.values()]
        .map((regels) => {
            const naamgever = kortsteNaam(regels);
            return {
                titel: productTitel(naamgever),
                naamgever,
                beste: regels[0],
                regels,
                vergelijkbaar: isVergelijkbaar(regels),
            };
        })
        .sort((a, b) => a.titel.localeCompare(b.titel, 'nl'));
}

/**
 * Kiest de naam die boven de groep komt te staan.
 *
 * Dat is de kortste productnaam: staat er naast een losse pot ook een
 * voordeelpak, dan heet de groep "Aroma rood filterkoffie" en niet
 * "Aroma rood filterkoffie 4-pack".
 */
function kortsteNaam(regels) {
    return regels.reduce((kortste, regel) => (
        (regel.product_naam || '').length < (kortste.product_naam || '').length ? regel : kortste
    ), regels[0]);
}

/** Zijn alle aanbiedingen in een groep in dezelfde eenheid uitgedrukt? */
function isVergelijkbaar(regels) {
    if (regels.length < 2) {
        return false;
    }
    const eenheid = regels[0].eenheid_norm;
    return regels.every((regel) => (
        regel.eenheid_norm === eenheid
        && Number(regel.prijs_per_eenheid) > 0
    ));
}

// Waar een product terechtkomt als de afdeling of de lade onbekend is gebleven.
const OVERIG = 'Overig';

/**
 * Zoekt de meest voorkomende naam in een rijtje; lege namen tellen niet mee.
 * Bij een gelijke stand wint de naam die het eerst voorbijkwam.
 */
function vaakste(namen) {
    const telling = new Map();
    for (const naam of namen) {
        const schoon = (naam || '').trim();
        if (schoon) {
            telling.set(schoon, (telling.get(schoon) || 0) + 1);
        }
    }

    let beste = '';
    let hoogste = 0;
    for (const [naam, aantal] of telling) {
        if (aantal > hoogste) {
            beste = naam;
            hoogste = aantal;
        }
    }
    return beste;
}

/**
 * Bepaalt onder welke afdeling en lade een product komt te staan.
 *
 * Hetzelfde product kan bij twee winkels net anders zijn ingedeeld — de ene
 * folder noemt het koffiebonen, de andere houdt het bij koffie. Het product mag
 * maar op één plek in de lijst staan, dus wint de indeling die het vaakst
 * voorkomt. Weet één winkel de lade wel en de andere niet, dan telt die ene:
 * een bekende lade zegt meer dan een lege.
 */
function plaatsVan(regels) {
    const hoofdgroep = vaakste(regels.map((regel) => regel.hoofdgroep));
    if (!hoofdgroep) {
        return { hoofdgroep: OVERIG, subgroep: OVERIG, onbekend: true };
    }

    const subgroep = vaakste(regels
        .filter((regel) => (regel.hoofdgroep || '').trim() === hoofdgroep)
        .map((regel) => regel.subgroep));

    return {
        hoofdgroep,
        subgroep: subgroep || OVERIG,
        onbekend: !subgroep,
    };
}

/** Alfabetisch, maar "Overig" zakt altijd naar onderen: dat is een restje. */
function opNaam(a, b) {
    if (a.naam === OVERIG) return 1;
    if (b.naam === OVERIG) return -1;
    return a.naam.localeCompare(b.naam, 'nl');
}

/**
 * Zet de producten onder de afdeling en de lade van onze eigen indeling.
 *
 * Zonder deze bundeling is een treffer op een hele afdeling één lange rij
 * kaarten; met de indeling erboven zie je in één oogopslag waar iets ligt.
 *
 * Wat de vertaling niet heeft kunnen plaatsen komt onder "Overig" terecht, altijd
 * onderaan — het verdwijnt dus niet uit beeld.
 */
export function bundelPerIndeling(producten) {
    const afdelingen = new Map();

    for (const product of producten) {
        const plaats = plaatsVan(product.regels);

        if (!afdelingen.has(plaats.hoofdgroep)) {
            afdelingen.set(plaats.hoofdgroep, new Map());
        }
        const laden = afdelingen.get(plaats.hoofdgroep);

        if (!laden.has(plaats.subgroep)) {
            laden.set(plaats.subgroep, { naam: plaats.subgroep, onbekend: plaats.onbekend, producten: [] });
        }
        laden.get(plaats.subgroep).producten.push(product);
    }

    return [...afdelingen.entries()]
        .map(([naam, laden]) => ({
            naam,
            aantal: [...laden.values()].reduce((som, lade) => som + lade.producten.length, 0),
            laden: [...laden.values()].sort(opNaam),
        }))
        .sort(opNaam);
}

/**
 * Een zoekvraag als één regel, bijvoorbeeld:
 * Merk: Lavazza én Groep: Koffie & thee › Koffiebonen
 *
 * Staan er meerdere delen, dan komt er "en" tussen: binnen één zoekvraag
 * moeten ze namelijk allemaal kloppen, en dat moet je aan de regel kunnen zien.
 *
 * Bij een afdeling zonder lade staat er nadrukkelijk "hele afdeling" bij: dat is
 * een veel bredere zoekvraag dan één lade, en dat hoor je te zien zonder te
 * moeten weten hoe de indeling in elkaar zit.
 */
export function zoekvraagTekst(zoekvraag) {
    const delen = [];
    if (zoekvraag.merk) delen.push(`Merk: ${zoekvraag.merk}`);
    if (zoekvraag.hoofdgroep) {
        delen.push(zoekvraag.subgroep
            ? `Groep: ${zoekvraag.hoofdgroep} › ${zoekvraag.subgroep}`
            : `Groep: ${zoekvraag.hoofdgroep} (hele afdeling)`);
    }
    if (zoekvraag.vrije_tekst) delen.push(`Tekst: ${zoekvraag.vrije_tekst}`);
    return delen.join(' én ');
}
