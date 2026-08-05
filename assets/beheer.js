/**
 * =============================================================================
 *  Dealbot — de beheerpagina
 *
 *  Versie      : 1.2
 *  Reden       : Verwijderen en weren zaten los van elkaar, terwijl je ze bijna
 *                altijd achter elkaar doet — en zodra het account weg is, staat
 *                het e-mailadres nergens meer op het scherm. Het verwijderen
 *                vraagt nu in één keer of het adres ook geweerd moet worden.
 *                Verder komen de knoppen na een klik weer terug, en is te zien
 *                welk account de beheerder is.
 *  Datum       : 05-08-2026 13:58
 *
 *  Onderdelen:
 *    bouwPagina()      - regelt de toegang en haalt de overzichten op
 *    toonRunstatus()   - de laatste ronde per winkel als tabel
 *    toonKwaliteit()   - aantallen per winkel, met wat er ontbreekt
 *    toonGebruikers()  - de accounts, met de knoppen om in te grijpen
 *    vraagVerwijderen()- weg met dit account, en het adres erbij?
 *    maakStaat()       - op slot, actief, en of het de beheerder is
 *    toonGeweerd()     - de e-mailadressen die geen account mogen maken
 *    maakTabel()       - een tabel met kop en regels, zonder opsmuk
 * =============================================================================
 */

import {
    haalToegang,
    haalRunstatus,
    haalKwaliteit,
    haalGebruikers,
    blokkeerGebruiker,
    verwijderGebruiker,
    haalGeweerdeAdressen,
    weerAdres,
    laatAdresToe,
    vraagHerstelmail,
    DealbotFout,
} from './data.js';
import { beveiligPagina, koppelUitloggen } from './inlog.js';
import { momentTekst } from './opmaak.js';

// Wat voor ronde het was, in gewone taal. Vomar levert er twee: zijn gewone
// schapprijzen en zijn folder, en die zijn allebei apart de moeite waard.
const SOORTEN = {
    aanbiedingen: 'Aanbiedingen',
    assortiment: 'Schapprijzen',
    folder: 'Folder (voorgelezen)',
};

const RESULTAAT = {
    gelukt: 'gelukt',
    mislukt: 'mislukt',
    bezig: 'nog bezig',
};

const melding = document.getElementById('melding');
const beheer = document.getElementById('beheer');
const runstatus = document.getElementById('runstatus');
const kwaliteit = document.getElementById('kwaliteit');
const gebruikers = document.getElementById('gebruikers');
const geweerd = document.getElementById('geweerd');

function toonMelding(tekst, soort = 'fout') {
    melding.textContent = tekst;
    melding.className = `melding ${soort}`;
    melding.hidden = !tekst;
}

/** Maakt een element met tekst erin; tekst uit de database gaat nooit als code. */
function maak(soort, klasse, tekst) {
    const element = document.createElement(soort);
    if (klasse) element.className = klasse;
    if (tekst !== undefined && tekst !== null) element.textContent = tekst;
    return element;
}

/**
 * Een tabel met een kopregel en daaronder de gegeven regels.
 *
 * Elke cel is óf een stuk tekst óf een kant-en-klaar element, zodat een regel
 * met een storingsmelding eronder net zo gebouwd wordt als een gewone.
 */
function maakTabel(koppen, regels) {
    const tabel = maak('table', 'beheertabel');

    const kop = document.createElement('thead');
    const koprij = document.createElement('tr');
    for (const tekst of koppen) {
        koprij.append(maak('th', null, tekst));
    }
    kop.append(koprij);
    tabel.append(kop);

    const lijf = document.createElement('tbody');
    for (const regel of regels) {
        const rij = maak('tr', regel.klasse);
        for (const cel of regel.cellen) {
            const vak = maak('td', cel.klasse);
            if (cel.breedte) {
                vak.colSpan = cel.breedte;
            }
            if (cel.element) {
                vak.append(cel.element);
            } else {
                vak.textContent = cel.tekst ?? '';
            }
            rij.append(vak);
        }
        lijf.append(rij);
    }
    tabel.append(lijf);

    return tabel;
}

/** Een getal met daarachter het aandeel van het geheel, als dat iets toevoegt. */
function metAandeel(aantal, totaal) {
    const getal = Number(aantal) || 0;
    const geheel = Number(totaal) || 0;
    if (getal === 0) {
        return '0';
    }
    if (geheel === 0) {
        return String(getal);
    }
    return `${getal} (${Math.round((getal / geheel) * 100)}%)`;
}

/** De naam van de winkel, met een aantekening als hij uitstaat. */
function winkelnaam(regel) {
    return regel.actief ? regel.winkel : `${regel.winkel} (staat uit)`;
}

/**
 * De laatste ronde per winkel.
 *
 * Een winkel die nog nooit heeft gedraaid blijft in de lijst staan met lege
 * velden: dat je van Nettorama niets ziet is zelf ook een bericht. Ging er iets
 * mis, dan staat de melding uit het logboek eronder — dat is doorgaans genoeg
 * om te weten welke bron dicht zit.
 */
function toonRunstatus(regels) {
    if (regels.length === 0) {
        runstatus.replaceChildren(maak('p', 'leeg-regel', 'Er is nog niets opgehaald.'));
        return;
    }

    const rijen = [];
    for (const regel of regels) {
        const heeftRonde = Boolean(regel.status);
        const resultaat = heeftRonde
            ? (RESULTAAT[regel.status] || regel.status)
            : 'nog nooit gedraaid';

        const wanneer = maak('span', null, momentTekst(regel.klaar_op || regel.gestart_op) || '—');
        const uitkomst = maak('span', regel.status === 'mislukt' ? 'fout-tekst' : null, resultaat);

        rijen.push({
            klasse: regel.actief ? null : 'uit',
            cellen: [
                { tekst: winkelnaam(regel) },
                { tekst: heeftRonde ? (SOORTEN[regel.soort] || regel.soort) : '—' },
                { element: wanneer },
                { element: uitkomst },
                { tekst: heeftRonde ? String(regel.aantal ?? 0) : '—', klasse: 'getal' },
            ],
        });

        if (regel.melding) {
            rijen.push({
                klasse: 'meldingregel',
                cellen: [
                    { tekst: '' },
                    { tekst: regel.melding, klasse: 'storingtekst', breedte: 4 },
                ],
            });
        }
    }

    runstatus.replaceChildren(
        maakTabel(['Winkel', 'Wat', 'Wanneer', 'Resultaat', 'Aantal'], rijen)
    );
}

/**
 * Hoeveel er per winkel staat, en hoeveel daarvan onvolledig is.
 *
 * Winkels waar helemaal niets van in de database staat blijven staan, maar in
 * lichtere letters: die vragen geen aandacht, ze doen alleen niet mee.
 */
function toonKwaliteit(regels) {
    if (regels.length === 0) {
        kwaliteit.replaceChildren(maak('p', 'leeg-regel', 'Er staat nog niets in de database.'));
        return;
    }

    const rijen = regels.map((regel) => {
        const leeg = Number(regel.aanbiedingen) === 0 && Number(regel.standaardprijzen) === 0;
        return {
            klasse: leeg ? 'uit' : null,
            cellen: [
                { tekst: winkelnaam(regel) },
                { tekst: String(regel.aanbiedingen ?? 0), klasse: 'getal' },
                { tekst: metAandeel(regel.zonder_kiloprijs, regel.aanbiedingen), klasse: 'getal' },
                { tekst: metAandeel(regel.zonder_indeling, regel.aanbiedingen), klasse: 'getal' },
                { tekst: String(regel.standaardprijzen ?? 0), klasse: 'getal' },
                { tekst: metAandeel(regel.prijzen_zonder_kilo, regel.standaardprijzen), klasse: 'getal' },
            ],
        };
    });

    kwaliteit.replaceChildren(maakTabel(
        ['Winkel', 'Aanbiedingen', 'zonder kiloprijs', 'zonder indeling',
            'Schapprijzen', 'zonder kiloprijs'],
        rijen
    ));
}

/**
 * Een knop in een tabelregel, die tijdens het werk even op slot gaat.
 *
 * Daarna is hij gewoon weer te gebruiken. Dat is nodig omdat lang niet elke klik
 * de tabel opnieuw opbouwt: wie het verwijderen afbreekt of alleen een mail
 * verstuurt, zou anders naar een blijvend grijze knop kijken.
 *
 * Met een wachttijd meldt de knop eerst kort wat er gebeurd is. Bij de
 * herstelmail houdt dat een tweede mail door dubbelklikken tegen, terwijl
 * opnieuw sturen na een halve minuut gewoon kan.
 */
function maakActie(tekst, klasse, handeling, { gedaanTekst = '', terugNa = 0 } = {}) {
    const knop = maak('button', `actieknop ${klasse}`, tekst);
    knop.type = 'button';
    knop.addEventListener('click', async () => {
        knop.disabled = true;
        try {
            await handeling();
            if (terugNa > 0) {
                knop.textContent = gedaanTekst || tekst;
                window.setTimeout(() => {
                    knop.textContent = tekst;
                    knop.disabled = false;
                }, terugNa);
                return;
            }
        } catch (fout) {
            if (fout instanceof DealbotFout) {
                toonMelding(fout.message);
            } else {
                console.error('Dealbot — bewerking mislukt:', fout);
                toonMelding('Dat lukte niet. Probeer het nog eens.');
            }
        }
        knop.disabled = false;
    });
    return knop;
}

/**
 * Vraagt of dit account echt weg mag, en of het adres geweerd moet worden.
 *
 * Die twee horen bij elkaar: is het account eenmaal weg, dan staat het
 * e-mailadres nergens meer op het scherm en is het weren een kwestie van uit je
 * hoofd overtikken. Annuleren is de standaardkeuze — wie op Enter drukt,
 * verwijdert dus niets.
 */
function vraagVerwijderen(regel) {
    const scherm = document.getElementById('verwijderscherm');
    const vinkje = document.getElementById('ookweren');
    const naam = regel.weergavenaam || regel.email;

    document.getElementById('verwijdertekst').textContent =
        `Het account van ${naam} (${regel.email}) gaat weg, met alle zoekvragen `
        + 'eronder. Dit is niet terug te draaien.';
    vinkje.checked = false;

    return new Promise((klaar) => {
        scherm.addEventListener('close', () => klaar({
            doorgaan: scherm.returnValue === 'ja',
            weren: vinkje.checked,
        }), { once: true });
        scherm.showModal();
    });
}

/**
 * De staat van een account: op slot of actief, en of het de beheerder is.
 *
 * Het beheerdersvlaggetje is alleen in de database te zetten. Het hoort hier wel
 * te staan: anders is aan niets te zien welk account overal bij kan.
 */
function maakStaat(regel) {
    const cel = maak('div', 'staat');
    cel.append(maak('span', regel.geblokkeerd ? 'fout-tekst' : null,
        regel.geblokkeerd ? 'op slot' : 'actief'));
    if (regel.beheerder) {
        cel.append(maak('span', 'aantekening', 'beheerder'));
    }
    return cel;
}

/**
 * De accounts, met per regel de knoppen om in te grijpen.
 *
 * Bij het eigen account staan geen knoppen: met één beheerder zou je jezelf
 * kunnen buitensluiten en dan komt er niemand meer binnen om het terug te
 * draaien. De database weigert het trouwens ook.
 */
function toonGebruikers(regels) {
    if (regels.length === 0) {
        gebruikers.replaceChildren(maak('p', 'leeg-regel', 'Er zijn nog geen accounts.'));
        return;
    }

    const rijen = regels.map((regel) => {
        const knoppen = maak('div', 'rijknoppen');

        // Deze kan wél op het eigen account: je stuurt jezelf gewoon een mail.
        // De knop komt na een halve minuut terug: zo is een dubbele mail door
        // dubbelklikken uitgesloten, maar blijft opnieuw sturen mogelijk als de
        // eerste niet aankwam.
        knoppen.append(maakActie('Herstelmail', 'zacht', async () => {
            await vraagHerstelmail(regel.email);
            toonMelding(`Er is een mail naar ${regel.email} gestuurd om een nieuwe `
                + 'pincode te kiezen.', 'goed');
        }, { gedaanTekst: 'Verstuurd', terugNa: 30000 }));

        if (regel.ben_ikzelf) {
            knoppen.append(maak('span', 'aantekening', 'jijzelf'));
        } else {
            knoppen.append(maakActie(
                regel.geblokkeerd ? 'Weer open' : 'Op slot',
                'zacht',
                async () => {
                    await blokkeerGebruiker(regel.id, !regel.geblokkeerd);
                    await laadOverzichten();
                }
            ));
            knoppen.append(maakActie('Verwijderen', 'gevaar', async () => {
                const keuze = await vraagVerwijderen(regel);
                if (!keuze.doorgaan) {
                    return;
                }
                // Bewust eerst weren en dan pas verwijderen: struikelt het weren,
                // dan staat het account er nog en is de knop opnieuw te gebruiken.
                if (keuze.weren) {
                    await weerAdres(regel.email, 'Account verwijderd vanaf de beheerpagina');
                }
                await verwijderGebruiker(regel.id);
                await laadOverzichten();
            }));
        }

        return {
            klasse: regel.geblokkeerd ? 'uit' : null,
            cellen: [
                { tekst: regel.weergavenaam || '—' },
                { tekst: regel.email },
                { tekst: momentTekst(regel.aangemaakt_op) || '—' },
                { tekst: momentTekst(regel.laatst_ingelogd) || 'nog nooit' },
                { tekst: String(regel.zoekvragen ?? 0), klasse: 'getal' },
                { element: maakStaat(regel) },
                { element: knoppen, klasse: 'acties' },
            ],
        };
    });

    gebruikers.replaceChildren(maakTabel(
        ['Naam', 'E-mail', 'Aangemaakt', 'Laatst ingelogd', 'Zoekvragen', 'Staat', ''],
        rijen
    ));
}

/** De e-mailadressen die geen nieuw account mogen maken. */
function toonGeweerd(regels) {
    if (regels.length === 0) {
        geweerd.replaceChildren(maak('p', 'leeg-regel', 'Er staat nog geen adres op de lijst.'));
        return;
    }

    const rijen = regels.map((regel) => ({
        cellen: [
            { tekst: regel.email },
            { tekst: regel.reden || '—' },
            { tekst: momentTekst(regel.toegevoegd_op) || '—' },
            {
                element: maakActie('Weer toelaten', 'zacht', async () => {
                    await laatAdresToe(regel.email);
                    await laadOverzichten();
                }),
                klasse: 'acties',
            },
        ],
    }));

    geweerd.replaceChildren(maakTabel(['E-mailadres', 'Reden', 'Sinds', ''], rijen));
}

/** Koppelt het formulier waarmee een adres op de lijst komt. */
function koppelWeerformulier() {
    const formulier = document.getElementById('weerformulier');
    const knop = document.getElementById('weerknop');
    const adresveld = document.getElementById('weeradres');
    const redenveld = document.getElementById('weerreden');

    formulier.addEventListener('submit', async (gebeurtenis) => {
        gebeurtenis.preventDefault();
        knop.disabled = true;
        try {
            await weerAdres(adresveld.value, redenveld.value);
            adresveld.value = '';
            redenveld.value = '';
            await laadOverzichten();
        } catch (fout) {
            if (fout instanceof DealbotFout) {
                toonMelding(fout.message);
            } else {
                console.error('Dealbot — adres weren mislukt:', fout);
                toonMelding('Het adres kon niet op de lijst worden gezet.');
            }
        } finally {
            knop.disabled = false;
        }
    });
}

/** Haalt alle overzichten op en zet ze op het scherm. */
async function laadOverzichten() {
    runstatus.replaceChildren(maak('p', 'bezig', 'Overzicht ophalen…'));
    kwaliteit.replaceChildren(maak('p', 'bezig', 'Cijfers ophalen…'));
    gebruikers.replaceChildren(maak('p', 'bezig', 'Accounts ophalen…'));
    geweerd.replaceChildren(maak('p', 'bezig', 'Lijst ophalen…'));

    try {
        const [rondes, cijfers, accounts, adressen] = await Promise.all([
            haalRunstatus(),
            haalKwaliteit(),
            haalGebruikers(),
            haalGeweerdeAdressen(),
        ]);
        console.info(
            `Dealbot — beheer: ${rondes.length} rondes, ${cijfers.length} winkels, `
            + `${accounts.length} accounts en ${adressen.length} geweerde adressen.`
        );
        toonRunstatus(rondes);
        toonKwaliteit(cijfers);
        toonGebruikers(accounts);
        toonGeweerd(adressen);
        toonMelding('');
    } catch (fout) {
        runstatus.replaceChildren();
        kwaliteit.replaceChildren();
        gebruikers.replaceChildren();
        geweerd.replaceChildren();
        if (fout instanceof DealbotFout) {
            toonMelding(fout.message);
        } else {
            console.error('Dealbot — beheerpagina kon niet worden opgebouwd:', fout);
            toonMelding('De beheergegevens konden niet worden opgehaald. Probeer het later nog eens.');
        }
    }
}

async function bouwPagina() {
    const gebruiker = await beveiligPagina();
    if (!gebruiker) {
        return;
    }
    koppelUitloggen();

    // De echte grendel zit in de database; deze controle is er om een gewone
    // gebruiker een fatsoenlijke uitleg te geven in plaats van een foutmelding.
    const toegang = await haalToegang();
    if (!toegang.beheerder) {
        beheer.hidden = true;
        toonMelding('Deze pagina is alleen voor de beheerder.');
        return;
    }

    beheer.hidden = false;
    document.getElementById('verversen').addEventListener('click', laadOverzichten);
    koppelWeerformulier();
    await laadOverzichten();
}

bouwPagina();
