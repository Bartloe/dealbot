/**
 * =============================================================================
 *  Dealbot — automatisch uitloggen na een lange stilte
 *
 *  Versie      : 1.0
 *  Reden       : Een account bleef ingelogd tot iemand op Uitloggen klikte. Op
 *                een gedeelde of vergeten laptop stond Dealbot daarmee voor
 *                iedereen open. Acht uur zonder enige handeling is nu genoeg om
 *                de sessie te beëindigen.
 *  Datum       : 05-08-2026 00:30
 *
 *  Onderdelen:
 *    sessieVerlopen()      - is het te lang stil geweest?
 *    meldActiviteit()      - zet de klok terug op nu
 *    wisActiviteit()       - vergeet het moment (bij uitloggen)
 *    bewaakSessie()        - houdt de klok bij en grijpt in als de tijd om is
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
