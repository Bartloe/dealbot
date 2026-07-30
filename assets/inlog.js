/**
 * =============================================================================
 *  Dealbot — het inlogscherm
 *
 *  Versie      : 1.0
 *  Reden       : Zonder inloggen mag niemand aanbiedingen of zoekvragen zien.
 *                Elke pagina gebruikt hetzelfde scherm, dus staat het één keer
 *                hier en niet in elke pagina apart.
 *  Datum       : 30-07-2026 23:07
 *
 *  Onderdelen:
 *    beveiligPagina() - geeft de ingelogde gebruiker, of toont het inlogscherm
 *    koppelUitloggen() - laat de uitlogknop werken
 * =============================================================================
 */

import { logIn, meldAan, logUit, haalGebruiker, DealbotFout, PINCODE_LENGTE } from './data.js';

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
        return gebruiker;
    }

    houder.innerHTML = SCHERM;
    houder.hidden = false;
    bouwInlogscherm();
    return null;
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
