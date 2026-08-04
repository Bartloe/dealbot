/**
 * =============================================================================
 *  Dealbot — het inlogscherm
 *
 *  Versie      : 1.1
 *  Reden       : De beheerpagina erbij. De knop ernaartoe hoort alleen in de
 *                balk van de beheerder te staan, dus wordt na het inloggen
 *                gevraagd of dit account dat is.
 *  Datum       : 04-08-2026 22:25
 *
 *  Onderdelen:
 *    beveiligPagina() - geeft de ingelogde gebruiker, of toont het inlogscherm
 *    toonBeheerknop() - zet de beheerknop in de balk als je beheerder bent
 *    koppelUitloggen() - laat de uitlogknop werken
 * =============================================================================
 */

import {
    logIn, meldAan, logUit, haalGebruiker, benIkBeheerder, DealbotFout, PINCODE_LENGTE,
} from './data.js';

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
        houder.hidden = true;
        document.querySelectorAll('[data-na-inloggen]').forEach((deel) => {
            deel.hidden = false;
        });
        // Los van de pagina zelf: de knop mag gerust een fractie later komen.
        toonBeheerknop();
        return gebruiker;
    }

    houder.innerHTML = SCHERM;
    houder.hidden = false;
    bouwInlogscherm();
    return null;
}

/**
 * Zet de knop naar de beheerpagina in de balk, maar alleen bij de beheerder.
 *
 * Voor alle anderen bestaat die knop niet. Wie het adres tóch intikt komt niet
 * verder: de database geeft de beheergegevens alleen aan het beheerdersaccount.
 */
async function toonBeheerknop() {
    const knop = document.getElementById('beheerlink');
    if (!knop) {
        return;
    }
    if (await benIkBeheerder()) {
        knop.hidden = false;
    }
}

/** Koppelt het inlogformulier: inloggen, aanmelden en het wisselen daartussen. */
function bouwInlogscherm() {
    const formulier = document.getElementById('inlogformulier');
    const knop = document.getElementById('inlogknop');
    const schakelaar = document.getElementById('schakelaar');
    const naamveld = document.getElementById('naamveld');
    const melding = document.getElementById('inlogmelding');

    let aanmelden = false;

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
            window.location.reload();
        }
    });
}
