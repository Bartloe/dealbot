-- =============================================================================
--  Dealbot — het profiel zoekt voortaan op onze eigen indeling
--
--  Versie      : 1.0
--  Reden       : Een zoekvraag ging tot nu toe over de groepsnaam van één
--                winkel. Wie koffiebonen wilde volgen moest daardoor bij elke
--                keten apart de juiste naam aanvinken — "Koffiebonen" (Albert
--                Heijn), "lokaal Koffiebonen" (Jumbo), "Koffie & cacao" (Dirk)
--                — en bij Vomar kon het helemaal niet, want die folder levert
--                geen groep.
--
--                Nu de eigen indeling gevuld is (28 afdelingen, 252 laden) kan
--                de zoekvraag daar bovenop: één keer "Koffiebonen" aanvinken en
--                alle winkels tegelijk zien. De groepsnaam van de winkel zelf
--                blijft gewoon op de aanbieding staan; die is nog steeds de
--                bron van de vertaling en op de winkelpagina de logische.
--  Datum       : 04-08-2026 10:20
--
--  Onderdelen:
--    zoekvragen         - hoofdgroep + subgroep erbij, winkelgroep eruit
--    mijn_aanbiedingen()- matcht op onze eigen indeling
--    eigen_indeling()   - de keuzelijst van het profielscherm, met aantallen
--    productgroepen()   - vervalt: de keuzelijst per winkel bestaat niet meer
--
--  Let op: de bestaande zoekvragen worden gewist. Ze wijzen naar groepsnamen
--  van winkels die als zoekingang verdwijnen; omzetten zou raden zijn en dit is
--  nog de testfase.
--
--  Volgorde: na 09_geen_plek_onthouden.sql. Opnieuw uit te voeren zonder schade.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Stap 1 — de zoekvragen leegmaken.
--
-- Moet vóór stap 2, want de nieuwe regel "een zoekvraag moet ergens over gaan"
-- zou anders struikelen over een oude zoekvraag die alleen een winkelgroep had.
-- -----------------------------------------------------------------------------
delete from public.zoekvragen;


-- -----------------------------------------------------------------------------
-- Stap 2 — de zoekvraag gaat over onze eigen indeling.
--
-- Twee velden: de afdeling en, als de gebruiker het preciezer wil, de lade
-- daarbinnen. Alleen een afdeling betekent "alles wat hieronder hangt" —
-- inclusief de aanbiedingen waarvan we de afdeling wel weten maar de lade niet.
-- -----------------------------------------------------------------------------
alter table public.zoekvragen
    add column if not exists hoofdgroep text,
    add column if not exists subgroep   text;

alter table public.zoekvragen drop column if exists productgroep;

alter table public.zoekvragen drop constraint if exists zoekvraag_niet_leeg;
alter table public.zoekvragen add constraint zoekvraag_niet_leeg check (
    coalesce(nullif(btrim(merk),        ''), '') <> '' or
    coalesce(nullif(btrim(hoofdgroep),  ''), '') <> '' or
    coalesce(nullif(btrim(vrije_tekst), ''), '') <> ''
);

-- Een lade zonder afdeling is geen zoekvraag maar een halve: dezelfde ladenaam
-- kan onder twee afdelingen hangen, dus zonder afdeling is niet te zeggen welke
-- bedoeld wordt.
alter table public.zoekvragen drop constraint if exists zoekvraag_subgroep_hoort_bij_hoofdgroep;
alter table public.zoekvragen add constraint zoekvraag_subgroep_hoort_bij_hoofdgroep check (
    nullif(btrim(subgroep), '') is null
    or nullif(btrim(hoofdgroep), '') is not null
);

comment on column public.zoekvragen.hoofdgroep is
    'Afdeling uit onze eigen indeling. Zonder subgroep betekent dit: alles wat '
    'onder deze afdeling hangt, bij alle winkels.';
comment on column public.zoekvragen.subgroep is
    'Lade binnen de afdeling. Leeg = de hele afdeling.';


-- -----------------------------------------------------------------------------
-- Stap 3 — het matchen.
--
-- De productgroep van de winkel is als zoekingang vervallen; daarvoor in de
-- plaats komt onze eigen indeling, die bij alle winkels dezelfde woorden
-- gebruikt. Merk en vrije tekst blijven ongewijzigd: die kijken in het merk en
-- de productnaam.
-- -----------------------------------------------------------------------------
drop function if exists public.mijn_aanbiedingen();

create function public.mijn_aanbiedingen()
returns table (
    id                bigint,
    winkel            text,
    product_naam      text,
    merk              text,
    productgroep      text,
    hoofdgroep        text,
    subgroep          text,
    actie_tekst       text,
    prijs             numeric,
    normale_prijs     numeric,
    inhoud_waarde     numeric,
    inhoud_eenheid    text,
    prijs_per_eenheid numeric,
    eenheid_norm      text,
    product_sleutel   text,
    geldig_van        date,
    geldig_tot        date,
    product_url       text,
    afbeelding_url    text
)
language sql
stable
security invoker
set search_path = public
as $$
    select
        a.id,
        w.naam,
        a.product_naam,
        a.merk,
        a.productgroep,
        a.hoofdgroep,
        a.subgroep,
        a.actie_tekst,
        a.prijs,
        a.normale_prijs,
        a.inhoud_waarde,
        a.inhoud_eenheid,
        a.prijs_per_eenheid,
        a.eenheid_norm,
        a.product_sleutel,
        a.geldig_van,
        a.geldig_tot,
        a.product_url,
        a.afbeelding_url
    from public.aanbiedingen a
    join public.winkels w on w.id = a.winkel_id
    where exists (
        select 1
        from public.zoekvragen z
        where z.gebruiker_id = auth.uid()

          -- Merk: zoeken in het merkveld én in de productnaam, omdat niet elke
          -- winkel het merk apart aanlevert.
          and (
              nullif(btrim(z.merk), '') is null
              or lower(coalesce(a.merk, '') || ' ' || a.product_naam)
                 like '%' || lower(btrim(z.merk)) || '%'
          )

          -- Onze eigen indeling. Precies deze afdeling, en als er een lade bij
          -- gekozen is ook precies die lade. Alleen een afdeling laat dus ook
          -- de aanbiedingen door waarvan de lade onbekend is gebleven.
          and (
              nullif(btrim(z.hoofdgroep), '') is null
              or (
                  a.hoofdgroep = btrim(z.hoofdgroep)
                  and (
                      nullif(btrim(z.subgroep), '') is null
                      or a.subgroep = btrim(z.subgroep)
                  )
              )
          )

          -- Vrije tekst: alleen in merk en productnaam (dat is wat zoektekst
          -- bevat), nadrukkelijk niet in de groep.
          and (
              nullif(btrim(z.vrije_tekst), '') is null
              or a.zoektekst like '%' || lower(btrim(z.vrije_tekst)) || '%'
          )
    )
    -- Zelfde product bij elkaar, daarbinnen goedkoop naar duur.
    -- Is de kiloprijs onbekend, dan zakt de aanbieding naar onderen.
    order by a.product_sleutel,
             a.prijs_per_eenheid asc nulls last,
             a.prijs             asc nulls last;
$$;

comment on function public.mijn_aanbiedingen() is
    'Aanbiedingen die passen bij de zoekvragen van de ingelogde gebruiker, '
    'gegroepeerd per product en gesorteerd van goedkoop naar duur op kiloprijs. '
    'Aanbiedingen zonder bekende kiloprijs komen onderaan.';


-- -----------------------------------------------------------------------------
-- Stap 4 — de keuzelijst van het profielscherm.
--
-- Geeft de héle indeling terug, ook de laden waar deze week niets in ligt: juist
-- daar is een zoekvraag nuttig, want die blijft klaarstaan tot er iets van in de
-- bonus komt.
--
-- Per afdeling komt er één regel zonder subgroep bij, met het totaal van de hele
-- afdeling. Dat is precies de regel die de gebruiker aanvinkt als hij "alles van
-- deze afdeling" wil, en het totaal telt ook de aanbiedingen mee waarvan alleen
-- de afdeling bekend is.
--
-- Als functie, omdat de website hooguit 1000 regels per keer terugkrijgt en een
-- telling over tienduizenden aanbiedingen daar niet in past. De uitkomst zelf is
-- klein: 28 afdelingen met samen ruim 250 laden.
-- -----------------------------------------------------------------------------
drop function if exists public.eigen_groep_telling();
drop function if exists public.eigen_indeling();

create function public.eigen_indeling()
returns table (
    hoofdgroep text,
    subgroep   text,
    volgorde   integer,
    aantal     bigint
)
language sql
stable
security definer
set search_path = public
as $$
    with telling as (
        select a.hoofdgroep as hoofd, a.subgroep as sub, count(*)::bigint as aantal
          from public.aanbiedingen a
         where a.hoofdgroep is not null
         group by a.hoofdgroep, a.subgroep
    )
    -- De afdeling zelf; volgorde 0 zet hem boven zijn eigen laden.
    select g.hoofdgroep,
           null::text,
           0,
           coalesce((select sum(t.aantal) from telling t where t.hoofd = g.hoofdgroep), 0)
      from (select distinct hoofdgroep from public.eigen_groepen) g

    union all

    select g.hoofdgroep,
           g.subgroep,
           g.volgorde,
           coalesce((select t.aantal from telling t
                      where t.hoofd = g.hoofdgroep and t.sub = g.subgroep), 0)
      from public.eigen_groepen g

    order by 1, 3, 2;
$$;

grant execute on function public.eigen_indeling() to authenticated, service_role;

comment on function public.eigen_indeling() is
    'Onze eigen indeling met het aantal aanbiedingen dat er nu onder hangt. Een '
    'lege subgroep is de regel van de afdeling zelf, met het totaal van de hele '
    'afdeling. Voedt de keuzelijst op het profielscherm.';


-- -----------------------------------------------------------------------------
-- Stap 5 — de oude keuzelijst per winkel opruimen.
--
-- Die gaf 3962 groepsnamen terug met de winkel erachter. Sinds het profielscherm
-- op onze eigen indeling zoekt, vraagt niemand hem meer op.
-- -----------------------------------------------------------------------------
drop function if exists public.productgroepen();
