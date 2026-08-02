/**
 * =============================================================================
 *  Dealbot — verkeer met de database vanuit de website
 *
 *  Versie      : 1.5
 *  Reden       : De standaardprijzen-pagina is erbij gekomen. Die haalt niet
 *                alles in één keer op — er staan ruim zesduizend producten in —
 *                maar vraagt gericht om één productgroep of om een zoekterm.
 *  Datum       : 02-08-2026 13:10
 *
 *  Onderdelen:
 *    meldAan()               - maakt een nieuw account met e-mail + pincode
 *    logIn()                 - logt in met e-mailadres + pincode
 *    logUit()                - beëindigt de sessie
 *    haalGebruiker()         - geeft de ingelogde gebruiker, of niets
 *    haalAanbiedingen()      - de aanbiedingen die bij het profiel passen
 *    haalProductgroepen()    - de groepen waaruit een zoekvraag kan kiezen
 *    haalLaatsteRun()        - wanneer er voor het laatst is opgehaald
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

// De productgroepen komen in blokken binnen; zie haalProductgroepen(). Het
// maximum is een noodrem, zodat een fout aan de andere kant nooit tot eindeloos
// doorvragen leidt.
const GROEPEN_BLOK = 1000;
const GROEPEN_MAXIMUM = 20000;

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
 * Alle productgroepen die Dealbot ooit bij een winkel heeft gezien, met het
 * aantal aanbiedingen dat er nú in zit. Hiermee vult het profielscherm zijn
 * keuzelijst: ook een groep die deze week leeg is, blijft te kiezen.
 */
export async function haalProductgroepen() {
    const groepen = [];
    const gezien = new Set();

    // De database geeft hooguit duizend regels per keer terug, en de winkels
    // hebben er samen bijna vierduizend. Dus halen we ze blok voor blok op tot
    // er niets nieuws meer komt; anders zou de keuzelijst stilletjes
    // onvolledig zijn. Levert een volgend blok alleen bekende groepen op, dan
    // houdt de database geen rekening met het blok en stoppen we ermee: liever
    // een lijst die eerder ophoudt dan dezelfde groepen eindeloos herhaald.
    for (let begin = 0; begin < GROEPEN_MAXIMUM; begin += GROEPEN_BLOK) {
        const blok = await probeer('productgroepen ophalen', () => db
            .rpc('productgroepen')
            .range(begin, begin + GROEPEN_BLOK - 1));

        let nieuw = 0;
        for (const groep of blok || []) {
            const sleutel = `${groep.winkel_id}|${groep.productgroep}`;
            if (!gezien.has(sleutel)) {
                gezien.add(sleutel);
                groepen.push(groep);
                nieuw += 1;
            }
        }

        if (!blok || blok.length < GROEPEN_BLOK || nieuw === 0) {
            return groepen;
        }
    }

    return groepen;
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
            .select('id, product_naam, merk, afdeling, productgroep, prijs, '
                + 'inhoud_waarde, inhoud_eenheid, prijs_per_eenheid, eenheid_norm, '
                + 'ean, product_url, afbeelding_url');

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
        .select('id, merk, productgroep, vrije_tekst, aangemaakt_op')
        .order('aangemaakt_op', { ascending: true }));
    return data || [];
}

/**
 * Slaat een of meer zoekvragen in één keer op.
 *
 * Meer dan één tegelijk is nodig omdat je bij de productgroepen meerdere
 * groepen kunt aanvinken — ook van verschillende winkels. Elke aangevinkte
 * groep wordt een eigen zoekvraag; ze staan naast elkaar en tellen bij elkaar op.
 *
 * Elke zoekvraag moet minstens één gevuld veld hebben, anders zou hij op álle
 * aanbiedingen matchen.
 */
export async function voegZoekvragenToe(zoekvragen) {
    const schoon = (waarde) => {
        const tekst = (waarde || '').trim();
        return tekst === '' ? null : tekst;
    };

    const rijen = (zoekvragen || []).map((zoekvraag) => ({
        merk: schoon(zoekvraag.merk),
        productgroep: schoon(zoekvraag.productgroep),
        vrije_tekst: schoon(zoekvraag.vrije_tekst),
    }));

    if (rijen.length === 0 || rijen.some((r) => !r.merk && !r.productgroep && !r.vrije_tekst)) {
        throw new DealbotFout('Vul minstens één veld in of kies een productgroep.');
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
