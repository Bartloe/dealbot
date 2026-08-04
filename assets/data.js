/**
 * =============================================================================
 *  Dealbot — verkeer met de database vanuit de website
 *
 *  Versie      : 1.7
 *  Reden       : Een zoekvraag gaat voortaan over onze eigen indeling in plaats
 *                van over de groepsnaam van één winkel. De keuzelijst komt
 *                daarmee uit één bron — 28 afdelingen met hun laden — zodat
 *                "Koffiebonen" in één keer alle winkels dekt.
 *  Datum       : 04-08-2026 10:35
 *
 *  Onderdelen:
 *    meldAan()               - maakt een nieuw account met e-mail + pincode
 *    logIn()                 - logt in met e-mailadres + pincode
 *    logUit()                - beëindigt de sessie
 *    haalGebruiker()         - geeft de ingelogde gebruiker, of niets
 *    haalAanbiedingen()      - de aanbiedingen die bij het profiel passen
 *    haalEigenIndeling()     - onze afdelingen en laden, met hun aantallen
 *    haalLaatsteRun()        - wanneer er voor het laatst is opgehaald
 *    haalWinkels()           - de winkels waaruit Dealbot ophaalt
 *    telAanbiedingen()       - hoeveel een winkel er deze week heeft liggen
 *    haalWinkelAanbiedingen()- alles wat er deze week bij één winkel ligt
 *    haalZoekvragen()        - de zoekvragen van de ingelogde gebruiker
 *    voegZoekvragenToe()     - slaat een of meer nieuwe zoekvragen op
 *    verwijderZoekvraag()    - wist een zoekvraag
 *    haalPrijsgroepen()      - de groepen op de standaardprijzen-pagina
 *    zoekStandaardprijzen()  - de gewone winkelprijzen binnen groep of zoekterm
 * =============================================================================
 */

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import { SUPABASE_URL, SUPABASE_SLEUTEL } from './config.js';

const db = createClient(SUPABASE_URL, SUPABASE_SLEUTEL);

/** Een fout die aan de gebruiker getoond mag worden, in gewone taal. */
export class DealbotFout extends Error {}

export const PINCODE_LENGTE = 4;

/**
 * Zet de pincode om in een wachtwoord voor de database.
 *
 * Dit is géén beveiliging: het is opvulling, omdat de database een wachtwoord
 * van minimaal zes tekens eist en een pincode er vier heeft. De formule moet
 * bij aanmelden en inloggen exact hetzelfde zijn, anders kan niemand meer
 * binnenkomen.
 */
function wachtwoordVanPincode(pincode) {
    return `dealbot-pin-${pincode}`;
}

/** Controleert e-mailadres en pincode vóór er contact met de database is. */
function controleerInvoer(email, pincode) {
    if (!email || !email.includes('@')) {
        throw new DealbotFout('Vul een geldig e-mailadres in.');
    }
    if (!new RegExp(`^\\d{${PINCODE_LENGTE}}$`).test(pincode || '')) {
        throw new DealbotFout(`De pincode bestaat uit ${PINCODE_LENGTE} cijfers.`);
    }
}

/**
 * Vertaalt een melding van de database naar gewone taal.
 *
 * De database praat Engels en technisch; de gebruiker moet begrijpen wat er
 * mis is en wat hij eraan kan doen.
 */
function inGewoneTaal(melding) {
    const tekst = (melding || '').toLowerCase();

    if (tekst.includes('invalid login credentials')) {
        return 'Het e-mailadres of de pincode klopt niet.';
    }
    if (tekst.includes('already registered') || tekst.includes('already been registered')) {
        return 'Dit e-mailadres is al bekend. Log gewoon in met je pincode.';
    }
    if (tekst.includes('email not confirmed')) {
        return 'Dit account is nog niet bevestigd. Kijk in je mailbox.';
    }
    if (tekst.includes('password should be') || tekst.includes('weak password')) {
        return 'De pincode wordt door de database geweigerd. Meld dit even.';
    }
    if (tekst.includes('rate limit') || tekst.includes('too many')) {
        return 'Er zijn te veel pogingen achter elkaar gedaan. Probeer het over een minuut nog eens.';
    }
    if (tekst.includes('failed to fetch') || tekst.includes('networkerror')) {
        return 'Geen verbinding met de database. Controleer je internetverbinding.';
    }
    return `Er ging iets mis: ${melding}`;
}

/** Voert een aanroep uit en zet elke storing om in een begrijpelijke fout. */
async function probeer(omschrijving, aanroep) {
    let antwoord;
    try {
        antwoord = await aanroep();
    } catch (fout) {
        console.error(`Dealbot — ${omschrijving} mislukt:`, fout);
        throw new DealbotFout(inGewoneTaal(fout.message));
    }

    if (antwoord.error) {
        console.error(`Dealbot — ${omschrijving} mislukt:`, antwoord.error);
        throw new DealbotFout(inGewoneTaal(antwoord.error.message));
    }

    console.info(`Dealbot — ${omschrijving} gelukt.`);
    return antwoord.data;
}

// -- inloggen ----------------------------------------------------------------

/**
 * Maakt een nieuw account aan.
 *
 * Geeft terug of de gebruiker meteen binnen is. Staat de bevestigingsmail in
 * de database aangezet, dan is dat niet zo en moet hij eerst zijn mail lezen.
 */
export async function meldAan(email, pincode, weergavenaam) {
    controleerInvoer(email, pincode);

    const data = await probeer('aanmelden', () => db.auth.signUp({
        email: email.trim(),
        password: wachtwoordVanPincode(pincode),
        options: { data: { weergavenaam: (weergavenaam || '').trim() } },
    }));

    return { meteenIngelogd: Boolean(data.session) };
}

export async function logIn(email, pincode) {
    controleerInvoer(email, pincode);

    await probeer('inloggen', () => db.auth.signInWithPassword({
        email: email.trim(),
        password: wachtwoordVanPincode(pincode),
    }));
}

export async function logUit() {
    await probeer('uitloggen', () => db.auth.signOut());
}

/** Geeft de ingelogde gebruiker terug, of null als er niemand ingelogd is. */
export async function haalGebruiker() {
    try {
        const { data, error } = await db.auth.getSession();
        if (error) {
            console.error('Dealbot — sessie ophalen mislukt:', error);
            return null;
        }
        return data.session ? data.session.user : null;
    } catch (fout) {
        console.error('Dealbot — sessie ophalen mislukt:', fout);
        return null;
    }
}

// -- aanbiedingen ------------------------------------------------------------

/**
 * De actuele aanbiedingen die passen bij de zoekvragen van de ingelogde
 * gebruiker. De database doet het matchen en sorteren; hier komt de kant-en-
 * klare lijst binnen, van goedkoop naar duur per product.
 */
export async function haalAanbiedingen() {
    const data = await probeer('aanbiedingen ophalen', () => db.rpc('mijn_aanbiedingen'));
    return data || [];
}

/**
 * Onze eigen indeling: de afdelingen met hun laden, en hoeveel aanbiedingen er
 * op dit moment onder hangen.
 *
 * Hiermee vult het profielscherm zijn keuzelijst. De lijst staat los van wat er
 * deze week toevallig in de bonus ligt: een lade waar nu niets in zit, blijft
 * gewoon te kiezen. Een regel zonder subgroep is de afdeling zelf, met het
 * totaal van alles wat eronder hangt.
 */
export async function haalEigenIndeling() {
    const data = await probeer('onze indeling ophalen', () => db.rpc('eigen_indeling'));
    return data || [];
}

/**
 * Wanneer er voor het laatst met succes is opgehaald, en of de poging daarna
 * is mislukt.
 *
 * Het logboek bevat één regel per winkel per ronde; het gaat hier om het meest
 * recente moment. Een mislukking na dat moment is de moeite van het melden
 * waard: de lijst is dan ouder dan je zou verwachten.
 */
export async function haalLaatsteRun() {
    const gelukt = await probeer('laatste ophaalronde opzoeken', () => db
        .from('scan_logs')
        .select('klaar_op')
        .eq('status', 'gelukt')
        .not('klaar_op', 'is', null)
        .order('klaar_op', { ascending: false })
        .limit(1));

    const mislukt = await probeer('laatste storing opzoeken', () => db
        .from('scan_logs')
        .select('gestart_op')
        .eq('status', 'mislukt')
        .order('gestart_op', { ascending: false })
        .limit(1));

    const laatsteGelukt = gelukt && gelukt.length > 0 ? gelukt[0].klaar_op : null;
    const laatsteMislukt = mislukt && mislukt.length > 0 ? mislukt[0].gestart_op : null;

    return {
        gelukt: laatsteGelukt,
        // Alleen een storing van ná de laatste geslaagde ronde is nog actueel.
        storing: laatsteMislukt && (!laatsteGelukt || laatsteMislukt > laatsteGelukt)
            ? laatsteMislukt
            : null,
    };
}

// -- winkels -----------------------------------------------------------------

// De database geeft hooguit duizend regels per keer terug en de grootste winkel
// heeft er ruim twaalfhonderd, dus wordt er blok voor blok opgehaald. Het
// maximum is een noodrem tegen eindeloos doorvragen bij een fout aan de andere
// kant; geen enkele winkel komt in de buurt.
const AANBIEDINGEN_BLOK = 1000;
const AANBIEDINGEN_MAXIMUM = 20000;

// De datum in Nederlandse tijd, als 2026-08-03. Nodig om te bepalen wat er
// vandaag geldig is: een gebruiker op vakantie hoort dezelfde week te zien als
// iemand die in de winkel staat.
const DAGDELEN = new Intl.DateTimeFormat('nl-NL', {
    timeZone: 'Europe/Amsterdam',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
});

function vandaag() {
    const delen = {};
    for (const deel of DAGDELEN.formatToParts(new Date())) {
        delen[deel.type] = deel.value;
    }
    return `${delen.year}-${delen.month}-${delen.day}`;
}

/**
 * Beperkt een vraag tot de aanbiedingen die vandaag gelden.
 *
 * Niet elke aanbieding heeft datums — bij sommige winkels ontbreken ze. Die
 * blijven staan: ze zijn opgehaald in de ronde van vanochtend en horen dus bij
 * deze week. Wat wél een periode heeft, moet er vandaag binnen vallen; zo
 * verdwijnen de weekendacties uit de folder zodra het weekend voorbij is.
 */
function alleenDezeWeek(vraag) {
    const dag = vandaag();
    return vraag
        .or(`geldig_van.is.null,geldig_van.lte.${dag}`)
        .or(`geldig_tot.is.null,geldig_tot.gte.${dag}`);
}

/** De winkels waaruit Dealbot ophaalt, in vaste volgorde. */
export async function haalWinkels() {
    const data = await probeer('winkels ophalen', () => db
        .from('winkels')
        .select('id, code, naam')
        .eq('actief', true)
        .order('id', { ascending: true }));
    return data || [];
}

/**
 * Hoeveel aanbiedingen een winkel deze week heeft liggen.
 *
 * Alleen het aantal, niet de aanbiedingen zelf: de keuzestrook bovenaan de
 * pagina laat daarmee zien waar iets te halen valt zonder alles op te halen.
 * Lukt het tellen niet, dan komt er null terug — het aantal is bijzaak en mag
 * de pagina niet tegenhouden.
 */
export async function telAanbiedingen(winkelId) {
    try {
        const vraag = alleenDezeWeek(db
            .from('aanbiedingen')
            .select('id', { count: 'exact', head: true })
            .eq('winkel_id', winkelId));

        const { count, error } = await vraag;
        if (error) {
            console.error(`Dealbot — aanbiedingen tellen van winkel ${winkelId} mislukt:`, error);
            return null;
        }
        return count;
    } catch (fout) {
        console.error(`Dealbot — aanbiedingen tellen van winkel ${winkelId} mislukt:`, fout);
        return null;
    }
}

/**
 * Alles wat er deze week bij één winkel ligt, op volgorde van productgroep.
 *
 * Binnen een groep staat het goedkoopste per kilo vooraan; wat geen kiloprijs
 * heeft, zakt naar onderen in plaats van te verdwijnen. Het nummer sluit de
 * rij, zodat de volgorde tussen twee blokken door niet kan verspringen — anders
 * zou een aanbieding dubbel of helemaal niet binnenkomen.
 */
export async function haalWinkelAanbiedingen(winkelId) {
    const alles = [];

    for (let begin = 0; begin < AANBIEDINGEN_MAXIMUM; begin += AANBIEDINGEN_BLOK) {
        const blok = await probeer('aanbiedingen van de winkel ophalen', () => alleenDezeWeek(db
            .from('aanbiedingen')
            .select('id, product_naam, merk, productgroep, actie_tekst, prijs, normale_prijs, '
                + 'inhoud_waarde, inhoud_eenheid, prijs_per_eenheid, eenheid_norm, '
                + 'geldig_van, geldig_tot, product_url, afbeelding_url')
            .eq('winkel_id', winkelId))
            .order('productgroep', { ascending: true, nullsFirst: false })
            .order('prijs_per_eenheid', { ascending: true, nullsFirst: false })
            .order('id', { ascending: true })
            .range(begin, begin + AANBIEDINGEN_BLOK - 1));

        alles.push(...(blok || []));

        if (!blok || blok.length < AANBIEDINGEN_BLOK) {
            return alles;
        }
    }

    return alles;
}

// -- standaardprijzen --------------------------------------------------------

// Hooguit zoveel producten per zoekopdracht op het scherm. De grootste groep
// telt er een paar honderd; deze grens is er voor het geval iemand op "a" zoekt.
const PRIJZEN_MAXIMUM = 300;

/**
 * De productgroepen op de standaardprijzen-pagina, met hun afdeling en aantal.
 *
 * Anders dan de groepenlijst van het profielscherm komt deze rechtstreeks uit
 * de producten die er nú zijn: hier valt niets te wachten op een aanbieding, dus
 * een lege groep heeft geen zin.
 */
export async function haalPrijsgroepen() {
    const data = await probeer('productgroepen van de standaardprijzen ophalen',
        () => db.rpc('standaardprijs_groepen'));
    return data || [];
}

/**
 * De gewone winkelprijzen binnen één productgroep, of die op een zoekterm passen.
 *
 * Er staan ruim zesduizend producten in de database; die haalt de pagina bewust
 * niet allemaal op. Zonder groep én zonder zoekterm komt er dus niets terug —
 * de pagina vraagt dan eerst om een keuze.
 *
 * Sorteren gebeurt op kiloprijs, want daar gaat het om bij vergelijken. Wat
 * geen kiloprijs heeft, zakt naar onderen in plaats van te verdwijnen.
 */
export async function zoekStandaardprijzen({ groep = '', tekst = '' } = {}) {
    const groepsnaam = (groep || '').trim();
    const zoekterm = (tekst || '').trim();

    if (!groepsnaam && !zoekterm) {
        return [];
    }

    const data = await probeer('standaardprijzen ophalen', () => {
        let vraag = db
            .from('standaardprijzen')
            .select('id, product_naam, merk, productgroep, prijs, '
                + 'inhoud_waarde, inhoud_eenheid, prijs_per_eenheid, eenheid_norm, '
                + 'product_url, afbeelding_url');

        if (groepsnaam) {
            vraag = vraag.eq('productgroep', groepsnaam);
        }
        if (zoekterm) {
            // De zoektekst bevat merk en productnaam in kleine letters. Procent-
            // en liggend-streepjetekens hebben in een zoekopdracht een eigen
            // betekenis; die halen we eruit zodat ze gewoon als tekst gelden.
            const schoon = zoekterm.toLowerCase().replace(/[%_\\]/g, ' ');
            vraag = vraag.ilike('zoektekst', `%${schoon}%`);
        }

        return vraag
            .order('prijs_per_eenheid', { ascending: true, nullsFirst: false })
            .limit(PRIJZEN_MAXIMUM);
    });

    return data || [];
}

// -- zoekvragen --------------------------------------------------------------

export async function haalZoekvragen() {
    const data = await probeer('zoekvragen ophalen', () => db
        .from('zoekvragen')
        .select('id, merk, hoofdgroep, subgroep, vrije_tekst, aangemaakt_op')
        .order('aangemaakt_op', { ascending: true }));
    return data || [];
}

/**
 * Slaat een of meer zoekvragen in één keer op.
 *
 * Meer dan één tegelijk is nodig omdat je in de indeling meerdere afdelingen en
 * laden tegelijk kunt aanvinken. Elke aangevinkte keuze wordt een eigen
 * zoekvraag; ze staan naast elkaar en tellen bij elkaar op.
 *
 * Elke zoekvraag moet minstens één gevuld veld hebben, anders zou hij op álle
 * aanbiedingen matchen. Een lade zonder afdeling kan niet: dezelfde ladenaam kan
 * onder twee afdelingen hangen.
 */
export async function voegZoekvragenToe(zoekvragen) {
    const schoon = (waarde) => {
        const tekst = (waarde || '').trim();
        return tekst === '' ? null : tekst;
    };

    const rijen = (zoekvragen || []).map((zoekvraag) => ({
        merk: schoon(zoekvraag.merk),
        hoofdgroep: schoon(zoekvraag.hoofdgroep),
        subgroep: schoon(zoekvraag.subgroep),
        vrije_tekst: schoon(zoekvraag.vrije_tekst),
    }));

    if (rijen.length === 0 || rijen.some((r) => !r.merk && !r.hoofdgroep && !r.vrije_tekst)) {
        throw new DealbotFout('Vul minstens één veld in of kies een productgroep.');
    }
    if (rijen.some((r) => r.subgroep && !r.hoofdgroep)) {
        throw new DealbotFout('Er ging iets mis met de gekozen groep. Probeer het opnieuw.');
    }

    const gebruiker = await haalGebruiker();
    if (!gebruiker) {
        throw new DealbotFout('Je bent niet meer ingelogd. Log opnieuw in.');
    }

    const data = await probeer('zoekvragen opslaan', () => db
        .from('zoekvragen')
        .insert(rijen.map((rij) => ({ ...rij, gebruiker_id: gebruiker.id })))
        .select());
    return data || [];
}

export async function verwijderZoekvraag(id) {
    await probeer('zoekvraag verwijderen', () => db
        .from('zoekvragen')
        .delete()
        .eq('id', id));
}
