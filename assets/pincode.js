/**
 * =============================================================================
 *  Dealbot — een nieuwe pincode kiezen
 *
 *  Versie      : 1.0
 *  Reden       : Wie zijn pincode kwijt was, kon nergens meer heen: de
 *                beheerder kende hem ook niet. Voortaan vraagt de gebruiker
 *                zelf een mail aan en kiest hij via de link daarin een nieuwe.
 *                Dezelfde als de oude mag ook.
 *  Datum       : 05-08-2026 01:10
 *
 *  Onderdelen:
 *    bouwPagina()   - controleert de link uit de mail en toont het formulier
 *    foutInLink()   - haalt een eventuele klacht uit het webadres
 *
 *  Deze pagina hoort bij de link uit de herstelmail. Wie hem zomaar opent heeft
 *  geen geldige sleutel en krijgt netjes te horen dat hij een mail moet
 *  aanvragen.
 * =============================================================================
 */

import { wachtOpHerstelsessie, zetNieuwePincode, DealbotFout, PINCODE_LENGTE } from './data.js';
import { meldActiviteit } from './sessie.js';

const wachten = document.getElementById('wachten');
const formulier = document.getElementById('pincodeformulier');
const melding = document.getElementById('melding');
const linkmelding = document.getElementById('linkmelding');

function toonMelding(veld, tekst, soort = 'fout') {
    veld.textContent = tekst;
    veld.className = `melding ${soort}`;
    veld.hidden = !tekst;
}

/**
 * De klacht die de database achter het hekje in het webadres kan zetten.
 *
 * Een verlopen link komt daar bijvoorbeeld als "otp_expired" terug; dat is
 * bruikbaarder dan wachten tot de sleutel niet blijkt te werken.
 */
function foutInLink() {
    const hekje = window.location.hash.replace(/^#/, '');
    const zoekdeel = new URLSearchParams(hekje || window.location.search.replace(/^\?/, ''));
    const soort = zoekdeel.get('error') || zoekdeel.get('error_code');
    if (!soort) {
        return '';
    }
    const uitleg = (zoekdeel.get('error_description') || '').toLowerCase();
    if (soort.includes('expired') || uitleg.includes('expired')) {
        return 'Deze link is verlopen. Vraag op het inlogscherm een nieuwe mail aan.';
    }
    return 'Deze link werkt niet (meer). Vraag op het inlogscherm een nieuwe mail aan.';
}

async function bouwPagina() {
    const klacht = foutInLink();
    if (klacht) {
        wachten.hidden = true;
        toonMelding(linkmelding, klacht);
        return;
    }

    const geldig = await wachtOpHerstelsessie();
    wachten.hidden = true;

    if (!geldig) {
        toonMelding(linkmelding,
            'We konden je link niet controleren. Vraag op het inlogscherm een nieuwe mail aan.');
        return;
    }

    formulier.hidden = false;
    document.getElementById('pincode').focus();
}

formulier.addEventListener('submit', async (gebeurtenis) => {
    gebeurtenis.preventDefault();
    toonMelding(melding, '');

    const pincode = document.getElementById('pincode').value;
    const herhaling = document.getElementById('herhaling').value;

    if (pincode !== herhaling) {
        toonMelding(melding, 'De twee pincodes zijn niet hetzelfde.');
        return;
    }

    const knop = document.getElementById('opslaan');
    knop.disabled = true;
    knop.textContent = 'Even geduld…';

    try {
        await zetNieuwePincode(pincode);
        // De link heeft de gebruiker meteen ingelogd; de klok van de stilte
        // begint hier, anders zou een oud moment hem meteen weer uitloggen.
        meldActiviteit(true);
        formulier.hidden = true;
        toonMelding(linkmelding,
            'Je nieuwe pincode is opgeslagen. Je bent meteen ingelogd.', 'goed');
        window.setTimeout(() => { window.location.href = 'index.html'; }, 2000);
    } catch (fout) {
        const tekst = fout instanceof DealbotFout
            ? fout.message
            : `Het opslaan lukte niet. Kies ${PINCODE_LENGTE} cijfers en probeer het nog eens.`;
        if (!(fout instanceof DealbotFout)) {
            console.error('Dealbot — nieuwe pincode opslaan mislukt:', fout);
        }
        toonMelding(melding, tekst);
        knop.disabled = false;
        knop.textContent = 'Pincode opslaan';
    }
});

bouwPagina();
