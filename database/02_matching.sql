-- =============================================================================
--  Dealbot — het matchen van aanbiedingen op zoekvragen
--
--  Versie      : 1.0
--  Reden       : De startpagina moet in één keer de aanbiedingen kunnen ophalen
--                die bij het profiel van de ingelogde gebruiker passen, al
--                gegroepeerd en gesorteerd van goedkoop naar duur.
--  Datum       : 27-07-2026 21:04
--
--  Onderdelen:
--    mijn_aanbiedingen() - geeft de aanbiedingen terug die matchen met de
--                          zoekvragen van de ingelogde gebruiker
--
--  Matchregels:
--    - Per zoekvraag moeten álle ingevulde velden kloppen (EN-logica).
--    - Een veld matcht als de tekst ergens in de aanbieding voorkomt.
--    - Hoofdletters worden genegeerd, zodat "oro" matcht met "Oro".
--    - Aanbiedingen zonder bekende kiloprijs komen onderaan, niet bovenaan.
-- =============================================================================

create or replace function public.mijn_aanbiedingen()
returns table (
    id                bigint,
    winkel            text,
    product_naam      text,
    merk              text,
    variant           text,
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
        a.variant,
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

          and (
              nullif(btrim(z.variant), '') is null
              or a.zoektekst like '%' || lower(btrim(z.variant)) || '%'
          )

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
