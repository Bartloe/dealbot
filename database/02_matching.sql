-- =============================================================================
--  Dealbot — het matchen van aanbiedingen op zoekvragen
--
--  Versie      : 2.0
--  Reden       : De drie zoekvelden kijken voortaan elk naar hun eigen stuk van
--                de aanbieding. Vrije tekst zocht ook in de productgroep, en dus
--                gaf "koffie" een krat Amstel (Dirks groep heet "Dranken, sap,
--                koffie & thee"). De productgroep heeft nu een eigen ingang met
--                een keuzelijst, en matcht precies in plaats van "bevat".
--  Datum       : 31-07-2026 01:12
--
--  Onderdelen:
--    mijn_aanbiedingen() - de aanbiedingen die bij het profiel van de ingelogde
--                          gebruiker passen, al gegroepeerd en gesorteerd
--    productgroepen()    - de groepen die deze week in de aanbiedingen zitten,
--                          voor de keuzelijst op het profielscherm
--
--  Matchregels:
--    - Merk         : komt de tekst voor in het merk of in de productnaam?
--    - Productgroep : is het exact deze groep? (komt uit de keuzelijst)
--    - Vrije tekst  : komt de tekst voor in het merk of in de productnaam?
--    - Per zoekvraag moeten álle ingevulde velden kloppen (EN-logica); losse
--      zoekvragen tellen bij elkaar op.
--    - Hoofdletters worden genegeerd, zodat "oro" matcht met "Oro".
--    - Aanbiedingen zonder bekende kiloprijs komen onderaan, niet bovenaan.
-- =============================================================================

-- De teruggegeven kolommen zijn veranderd, dus de oude versie moet eerst weg.
drop function if exists public.mijn_aanbiedingen();

create function public.mijn_aanbiedingen()
returns table (
    id                bigint,
    winkel            text,
    product_naam      text,
    merk              text,
    productgroep      text,
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

          -- Productgroep: precies deze groep. De gebruiker kiest hem uit een
          -- lijst met bestaande groepen, dus "bevat" is hier niet nodig — en
          -- juist ongewenst: "koffie" zit ook in "Dranken, sap, koffie & thee".
          and (
              nullif(btrim(z.productgroep), '') is null
              or lower(coalesce(a.productgroep, '')) = lower(btrim(z.productgroep))
          )

          -- Vrije tekst: alleen in merk en productnaam (dat is wat zoektekst
          -- bevat), nadrukkelijk niet in de productgroep.
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
-- De keuzelijst met productgroepen.
--
-- Elke winkel hanteert zijn eigen indeling: Albert Heijn deelt fijn in
-- ("Toiletpapier - vochtig"), Jumbo en Dirk grof ("Zuivel, boter en eieren").
-- Daarom staat de winkelnaam erbij en wordt er per winkel gegroepeerd op het
-- scherm. Het aantal helpt kiezen: een groep met drie aanbiedingen is iets
-- anders dan een groep met driehonderd.
--
-- De lijst komt rechtstreeks uit de aanbiedingen van deze week, dus er staat
-- nooit een groep in die niets oplevert.
-- -----------------------------------------------------------------------------
drop function if exists public.productgroepen();

create function public.productgroepen()
returns table (
    winkel_id    smallint,
    winkel       text,
    productgroep text,
    aantal       bigint
)
language sql
stable
security invoker
set search_path = public
as $$
    select
        a.winkel_id,
        w.naam,
        a.productgroep,
        count(*)
    from public.aanbiedingen a
    join public.winkels w on w.id = a.winkel_id
    where nullif(btrim(a.productgroep), '') is not null
    group by a.winkel_id, w.naam, a.productgroep
    order by w.naam, a.productgroep;
$$;

comment on function public.productgroepen() is
    'De productgroepen die op dit moment in de aanbiedingen voorkomen, per '
    'winkel en met het aantal aanbiedingen erbij. Voedt de keuzelijst op het '
    'profielscherm.';
