/**
 * =============================================================================
 *  Dealbot — het inlogscherm
 *
 *  Versie      : 1.5
 *  Reden       : Na een automatische uitlog stond het inlogscherm helemaal leeg.
 *                Het e-mailadres staat nu al ingevuld en de cursor springt naar
 *                de pincode: alleen die vier cijfers en je bent weer binnen.
 *  Datum       : 06-08-2026 16:05
 *
 *  Onderdelen:
 *    beveiligPagina()   - geeft de ingelogde gebruiker, of toont het inlogscherm
 *    beeindigSessie()   - logt uit en zegt waarom
 *    toonInlogscherm()  - zet het inlogscherm in beeld, met eventueel een melding
 *    koppelUitloggen()  - laat de uitlogknop werken
 * =============================================================================
 */

import {
    logIn, meldAan, logUit, haalGebruiker, haalToegang, vraagHerstelmail,
    DealbotFout, PINCODE_LENGTE,
} from './data.js';
import {
    sessieVerlopen, bewaakSessie, meldActiviteit, wisActiviteit,
    onthoudAdres, laatsteAdres, vergeetAdres, STILTE_UREN,
} from './sessie.js';

const SCHERM = `
<div class="inlogkaart">
    <h1>Dealbot</h1>
    <p class="ondertitel">Jouw aanbiedingen, bij elkaar.</p>

    <form id="inlogformulier" novalidate>
        <label>
            E-mailadres
            <input type="email" id="email" autocomplete="email" required>
        </label>

        <label id="naamveld" hidden>
            Je naam
            <input type="text" id="weergavenaam" autocomplete="name">
        </label>

        <label>
            Pincode (${PINCODE_LENGTE} cijfers)
            <input type="password" id="pincode" inputmode="numeric" pattern="\\d*"
                   maxlength="${PINCODE_LENGTE}" autocomplete="current-password" required>
        </label>

        <p class="melding" id="inlogmelding" role="alert" hidden></p>

        <button type="submit" id="inlogknop">Inloggen</button>
    </form>

    <button type="button" class="schakelaar" id="schakelaar">
        Nog geen account? Meld je aan
    </button>

    <button type="button" class="schakelaar zacht" id="pincodevergeten">
        Pincode vergeten?
    </button>
</div>
`;

/**
 * Zorgt dat de pagina alleen voor ingelogde mensen opengaat.
 *
 * Is er niemand ingelogd, dan komt het inlogscherm in beeld en geeft deze
 * functie niets terug; de pagina hoort dan te stoppen met opbouwen.
 */
export async function beveiligPagina() {
    const gebruiker = await haalGebruiker();
    const houder = document.getElementById('inlogscherm');

    if (gebruiker) {
        // Is het langer dan acht uur stil geweest, dan eindigt de sessie hier —
        // nog vóór er iets aan de database gevraagd wordt.
        if (sessieVerlopen()) {
            await beeindigSessie(houder,
                `Je bent automatisch uitgelogd omdat je ${STILTE_UREN} uur niets `
                + 'hebt gedaan. Log opnieuw in.');
            return null;
        }

        const toegang = await haalToegang();

        // Een account dat op slot staat komt er niet in. De database geeft hem
        // toch niets meer; dit scherm zegt hem waaróm zijn lijst leeg is.
        if (toegang.geblokkeerd) {
            console.info('Dealbot — dit account staat op slot; sessie beëindigd.');
            await beeindigSessie(houder,
                'Dit account is geblokkeerd. Neem contact op met de beheerder.');
            return null;
        }

        houder.hidden = true;
        document.querySelectorAll('[data-na-inloggen]').forEach((deel) => {
            deel.hidden = false;
        });

        if (toegang.beheerder) {
            const knop = document.getElementById('beheerlink');
            if (knop) {
                knop.hidden = false;
            }
        }

        // Vanaf hier telt de stilte. Blijft de pagina uren onaangeroerd open
        // staan, dan valt hij vanzelf terug op het inlogscherm.
        bewaakSessie(() => beeindigSessie(document.getElementById('inlogscherm'),
            `Je bent automatisch uitgelogd omdat je ${STILTE_UREN} uur niets hebt gedaan.`));

        return gebruiker;
    }

    toonInlogscherm(houder);
    return null;
}

/** Beëindigt de sessie en zet het inlogscherm in beeld met de reden erbij. */
async function beeindigSessie(houder, tekst) {
    try {
        await logUit();
    } catch (fout) {
        console.error('Dealbot — uitloggen mislukt:', fout);
    }
    wisActiviteit();
    toonInlogscherm(houder, tekst);
}

/** Zet het inlogscherm in beeld, eventueel met een melding erboven. */
function toonInlogscherm(houder, tekst = '') {
    houder.innerHTML = SCHERM;
    houder.hidden = false;
    document.querySelectorAll('[data-na-inloggen]').forEach((deel) => {
        deel.hidden = true;
    });
    bouwInlogscherm();

    if (tekst) {
        const melding = document.getElementById('inlogmelding');
        melding.textContent = tekst;
        melding.className = 'melding fout';
        melding.hidden = false;
    }
}

/** Koppelt het inlogformulier: inloggen, aanmelden en het wisselen daartussen. */
function bouwInlogscherm() {
    const formulier = document.getElementById('inlogformulier');
    const knop = document.getElementById('inlogknop');
    const schakelaar = document.getElementById('schakelaar');
    const naamveld = document.getElementById('naamveld');
    const melding = document.getElementById('inlogmelding');
    const emailveld = document.getElementById('email');
    const pincodeveld = document.getElementById('pincode');

    let aanmelden = false;

    // Het adres van de vorige keer staat er al in; alleen de pincode ontbreekt
    // nog, dus daar begint de cursor ook. Is er geen adres bekend, dan blijft
    // het bij het gewone lege scherm.
    const bekend = laatsteAdres();
    if (bekend) {
        emailveld.value = bekend;
        pincodeveld.focus();
    }

    const toon = (tekst, soort = 'fout') => {
        melding.textContent = tekst;
        melding.className = `melding ${soort}`;
        melding.hidden = !tekst;
    };

    schakelaar.addEventListener('click', () => {
        aanmelden = !aanmelden;
        naamveld.hidden = !aanmelden;
        knop.textContent = aanmelden ? 'Account aanmaken' : 'Inloggen';
        schakelaar.textContent = aanmelden
            ? 'Heb je al een account? Log in'
            : 'Nog geen account? Meld je aan';
        toon('');
    });

    // Pincode vergeten: één mail met een link waarmee je zelf een nieuwe kiest.
    // Of het adres bij ons bekend is, zeggen we bewust niet — anders kun je met
    // deze knop uitproberen wie er een account heeft.
    const vergeten = document.getElementById('pincodevergeten');
    vergeten.addEventListener('click', async () => {
        const email = document.getElementById('email').value;
        vergeten.disabled = true;
        toon('');

        try {
            await vraagHerstelmail(email);
            toon('Is dit adres bij ons bekend, dan staat er een mail voor je klaar. '
                + 'Daarin zit een link om een nieuwe pincode te kiezen.', 'goed');
        } catch (fout) {
            const tekst = fout instanceof DealbotFout
                ? fout.message
                : 'Het versturen lukte niet. Probeer het over een minuutje nog eens.';
            if (!(fout instanceof DealbotFout)) {
                console.error('Dealbot — herstelmail aanvragen mislukt:', fout);
            }
            toon(tekst);
        } finally {
            vergeten.disabled = false;
        }
    });

    formulier.addEventListener('submit', async (gebeurtenis) => {
        gebeurtenis.preventDefault();
        toon('');
        knop.disabled = true;
        knop.textContent = 'Even geduld…';

        const email = document.getElementById('email').value;
        const pincode = document.getElementById('pincode').value;
        const naam = document.getElementById('weergavenaam').value;

        try {
            if (aanmelden) {
                const { meteenIngelogd } = await meldAan(email, pincode, naam);
                if (!meteenIngelogd) {
                    toon('Je account is aangemaakt. Bevestig eerst de mail die je hebt gekregen.', 'goed');
                    return;
                }
            } else {
                await logIn(email, pincode);
            }
            // De klok van de stilte begint hier opnieuw; anders zou een oud
            // moment van de vorige gebruiker meteen weer uitloggen.
            meldActiviteit(true);
            onthoudAdres(email);
            // Opnieuw laden is de eenvoudigste manier om de pagina met de
            // gegevens van de zojuist ingelogde gebruiker op te bouwen.
            window.location.reload();
        } catch (fout) {
            const tekst = fout instanceof DealbotFout
                ? fout.message
                : 'Er ging iets mis bij het inloggen. Probeer het nog eens.';
            if (!(fout instanceof DealbotFout)) {
                console.error('Dealbot — onverwachte fout bij inloggen:', fout);
            }
            toon(tekst);
        } finally {
            knop.disabled = false;
            knop.textContent = aanmelden ? 'Account aanmaken' : 'Inloggen';
        }
    });
}

/** Laat de uitlogknop in de bovenbalk werken. */
export function koppelUitloggen() {
    const knop = document.getElementById('uitloggen');
    if (!knop) {
        return;
    }

    knop.addEventListener('click', async () => {
        knop.disabled = true;
        try {
            await logUit();
        } catch (fout) {
            console.error('Dealbot — uitloggen mislukt:', fout);
        } finally {
            wisActiviteit();
            // Zelf uitloggen betekent: laat niets van mij achter, ook het
            // e-mailadres niet.
            vergeetAdres();
            window.location.reload();
        }
    });
}
