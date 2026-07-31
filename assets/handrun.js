/**
 * =============================================================================
 *  Dealbot — de ochtendrun met de hand starten (TIJDELIJK)
 *
 *  Versie      : 1.0
 *  Reden       : Tijdens het testen hoeft niemand tot de volgende ochtend te
 *                wachten op verse aanbiedingen. Het startsein zelf gaat via
 *                GitHub, want de sleutel die de run mag starten hoort niet in
 *                een openbare website thuis.
 *  Datum       : 31-07-2026 09:34
 *
 *  Onderdelen:
 *    koppelVerversen() - laat de knop "Pagina verversen" de pagina herladen,
 *                        zodat de nieuwe aanbiedingen binnenkomen
 *
 *  Weg te halen zodra het testen klaar is: dit bestand, de sectie .handrun in
 *  index.html en het blok .handrun in stijl.css.
 * =============================================================================
 */

function koppelVerversen() {
    const knop = document.getElementById('verversen');
    if (!knop) {
        console.warn('Dealbot — de verversknop staat niet op deze pagina.');
        return;
    }

    knop.addEventListener('click', () => {
        console.info('Dealbot — pagina wordt ververst na een handmatige 07.00-run.');
        window.location.reload();
    });
}

koppelVerversen();
