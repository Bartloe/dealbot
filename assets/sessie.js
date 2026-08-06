/**
 * =============================================================================
 *  Dealbot — automatisch uitloggen na een lange stilte
 *
 *  Versie      : 1.1
 *  Reden       : Wie automatisch werd uitgelogd moest zijn e-mailadres opnieuw
 *                intypen. Dat adres wordt nu onthouden en staat bij terugkomst
 *                al ingevuld; alleen de pincode is nog nodig. Op de uitlogknop
 *                drukken wist het adres wél — dat doe je juist om de laptop
 *                schoon achter te laten.
 *  Datum       : 06-08-2026 16:05
 *
 *  Onderdelen:
 *    sessieVerlopen()      - is het te lang stil geweest?
 *    meldActiviteit()      - zet de klok terug op nu
 *    wisActiviteit()       - vergeet het moment (bij uitloggen)
 *    bewaakSessie()        - houdt de klok bij en grijpt in als de tijd om is
 *    onthoudAdres()        - bewaart het e-mailadres waarmee is ingelogd
 *    laatsteAdres()        - dat adres, om het inlogscherm mee voor te vullen
 *    vergeetAdres()        - vergeet het adres (bij handmatig uitloggen)
 *
 *  De klok loopt in de browser, niet in de database. Dat is precies genoeg voor
 *  het doel: iemand die de laptop laat staan, vindt bij terugkomst het
 *  inlogscherm. Wie wél bezig is wordt nooit midden in het kijken uitgegooid.
 * =============================================================================
 */

/** Zo lang mag het stil blijven voordat de sessie eindigt. */
export const STILTE_UREN = 8;

const STILTE_MS = STILTE_UREN * 60 * 60 * 1000;
const SLEUTEL = 'dealbot-laatste-activiteit';
const ADRESSLEUTEL = 'dealbot-laatste-adres';

// Hoe vaak er hooguit naar de opslag geschreven wordt. Zonder deze rem zou elke
// muisbeweging een schrijfactie zijn, terwijl een minuut ruim nauwkeurig genoeg
// is voor een grens van acht uur.
const SCHRIJFRUST_MS = 60 * 1000;

// Hoe vaak er gekeken wordt of de tijd om is terwijl de pagina openstaat.
const KIJKRONDE_MS = 60 * 1000;

// De handelingen die als "ik ben er nog" tellen.
const TEKENEN_VAN_LEVEN = ['click', 'keydown', 'scroll', 'touchstart'];

let laatstGeschreven = 0;

/** Leest het opgeslagen moment; geeft 0 als er niets (bruikbaars) staat. */
function laatsteMoment() {
    try {
        const waarde = Number(window.localStorage.getItem(SLEUTEL));
        return Number.isFinite(waarde) ? waarde : 0;
    } catch (fout) {
        // Staat de opslag uit, dan vervalt het automatisch uitloggen. Vervelend,
        // maar geen reden om de hele pagina te laten struikelen.
        console.warn('Dealbot — de browser bewaart geen gegevens:', fout);
        return 0;
    }
}

/**
 * Of het te lang stil is geweest.
 *
 * Is er nog geen moment bekend — de eerste pagina na het inloggen — dan is de
 * sessie niet verlopen; het moment wordt dan gewoon gezet.
 */
export function sessieVerlopen() {
    const moment = laatsteMoment();
    return moment > 0 && Date.now() - moment > STILTE_MS;
}

/** Zet de klok terug op nu, hooguit één keer per minuut. */
export function meldActiviteit(altijd = false) {
    const nu = Date.now();
    if (!altijd && nu - laatstGeschreven < SCHRIJFRUST_MS) {
        return;
    }
    laatstGeschreven = nu;
    try {
        window.localStorage.setItem(SLEUTEL, String(nu));
    } catch (fout) {
        console.warn('Dealbot — het moment van de laatste handeling is niet bewaard:', fout);
    }
}

/** Vergeet het moment. Hoort bij uitloggen, zodat de volgende gebruiker vers begint. */
export function wisActiviteit() {
    laatstGeschreven = 0;
    try {
        window.localStorage.removeItem(SLEUTEL);
    } catch (fout) {
        console.warn('Dealbot — het moment van de laatste handeling is niet gewist:', fout);
    }
}

/**
 * Bewaart het e-mailadres waarmee is ingelogd.
 *
 * Alleen het adres, nooit de pincode: die hoort na een automatische uitlog
 * opnieuw ingetypt te worden, anders is het uitloggen zinloos.
 */
export function onthoudAdres(email) {
    const adres = (email || '').trim();
    if (!adres) {
        return;
    }
    try {
        window.localStorage.setItem(ADRESSLEUTEL, adres);
    } catch (fout) {
        console.warn('Dealbot — het e-mailadres is niet bewaard:', fout);
    }
}

/** Het laatst gebruikte e-mailadres, of een lege tekst als er niets bekend is. */
export function laatsteAdres() {
    try {
        return window.localStorage.getItem(ADRESSLEUTEL) || '';
    } catch (fout) {
        console.warn('Dealbot — het e-mailadres is niet op te halen:', fout);
        return '';
    }
}

/**
 * Vergeet het adres. Hoort bij de uitlogknop en niet bij het automatisch
 * uitloggen: wie zelf uitlogt wil de laptop schoon achterlaten, wie na een
 * lange stilte terugkomt is gewoon dezelfde persoon.
 */
export function vergeetAdres() {
    try {
        window.localStorage.removeItem(ADRESSLEUTEL);
    } catch (fout) {
        console.warn('Dealbot — het e-mailadres is niet gewist:', fout);
    }
}

/**
 * Houdt bij of er nog iemand aan het werk is en grijpt in als de tijd om is.
 *
 * De pagina kan uren openstaan zonder dat er iets gebeurt; daarom wordt er ook
 * gekeken zonder dat de gebruiker iets doet. Komt hij terug uit de slaapstand,
 * dan valt de controle bij het eerste teken van leven meteen goed of fout uit.
 */
export function bewaakSessie(bijVerlopen) {
    meldActiviteit(true);

    for (const teken of TEKENEN_VAN_LEVEN) {
        window.addEventListener(teken, () => meldActiviteit(), { passive: true });
    }

    const kijk = () => {
        if (sessieVerlopen()) {
            window.clearInterval(rondje);
            console.info(`Dealbot — ${STILTE_UREN} uur geen activiteit; de sessie wordt beëindigd.`);
            bijVerlopen();
        }
    };

    const rondje = window.setInterval(kijk, KIJKRONDE_MS);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            kijk();
        }
    });
}
