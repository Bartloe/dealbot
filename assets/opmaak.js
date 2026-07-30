/**
 * =============================================================================
 *  Dealbot — aanbiedingen leesbaar maken
 *
 *  Versie      : 1.1
 *  Reden       : Een zoekvraag toont voortaan "Productgroep" in plaats van
 *                "Variant", en zet er "én" tussen: binnen één zoekvraag moeten
 *                alle ingevulde velden kloppen, en dat was op het scherm niet
 *                te zien.
 *  Datum       : 31-07-2026 01:12
 *
 *  Onderdelen:
 *    euro()               - bedrag als € 1,29
 *    kiloprijsTekst()     - "€ 2,58 per kilo" of "kiloprijs onbekend"
 *    geldigheidTekst()    - "geldig t/m 3 augustus"
 *    productTitel()       - merk en productnaam netjes achter elkaar
 *    groepeerPerProduct() - aanbiedingen van hetzelfde product bij elkaar
 *    zoekvraagTekst()     - een zoekvraag in één leesbare regel
 * =============================================================================
 */

const BEDRAG = new Intl.NumberFormat('nl-NL', {
    style: 'currency',
    currency: 'EUR',
});

const DATUM = new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'long' });

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

/**
 * Een zoekvraag als één regel, bijvoorbeeld:
 * Merk: Lavazza · Productgroep: Koffiebonen · Tekst: oro
 *
 * Staan er meerdere delen, dan komt er "en" tussen: binnen één zoekvraag
 * moeten ze namelijk allemaal kloppen, en dat moet je aan de regel kunnen zien.
 */
export function zoekvraagTekst(zoekvraag) {
    const delen = [];
    if (zoekvraag.merk) delen.push(`Merk: ${zoekvraag.merk}`);
    if (zoekvraag.productgroep) delen.push(`Productgroep: ${zoekvraag.productgroep}`);
    if (zoekvraag.vrije_tekst) delen.push(`Tekst: ${zoekvraag.vrije_tekst}`);
    return delen.join(' én ');
}
