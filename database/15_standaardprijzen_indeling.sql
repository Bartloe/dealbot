-- =============================================================================
--  Dealbot — de standaardprijzen-pagina op onze eigen indeling
--
--  Versie      : 1.0
--  Reden       : De keuzelijst op de standaardprijzen-pagina toonde de
--                groepsnamen van de winkel zelf. Bij Vomar heet vochtig
--                toiletpapier daar "Toiletpapier Vochtig" en stond het dus als
--                losse groep náást "Toiletpapier", terwijl het bij ons gewoon in
--                de lade Huishouden / Toiletpapier hoort. Zoeken op een lade
--                leverde daardoor niet alles op wat erin ligt.
--
--                Sinds de standaardprijzen worden ingedeeld kan die lijst
--                dezelfde afdelingen en laden tonen als de rest van Dealbot.
--                Anders dan op het profielscherm blijven lege laden hier weg:
--                op deze pagina valt niets te wachten op een aanbieding, dus een
--                lade zonder producten is alleen maar ruis.
--  Datum       : 05-08-2026 12:20
--
--  Onderdelen:
--    standaardprijs_indeling()  - onze afdelingen en laden, met hun aantallen
--    standaardprijs_groepen()   - vervalt; de pagina gebruikt nu de indeling
--
--  Volgorde: na 14_groepenlijst_hersteld.sql. Opnieuw uit te voeren zonder schade.
--  Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Onze indeling, met het aantal producten dat er nú in ligt.
--
-- Drie soorten regel komen eruit:
--
--   1. De afdeling zelf (subgroep leeg, volgorde 0), met het totaal van alles
--      wat eronder hangt — ook de producten waarvan alleen de afdeling bekend is.
--   2. Elke lade met producten erin.
--   3. Eén regel met een lege afdeling: de producten die nog nergens onder
--      hangen. Die horen vindbaar te blijven, anders verdwijnt een achtste van
--      het assortiment stilletjes uit beeld.
--
-- Als functie omdat de database hooguit duizend regels per keer teruggeeft: de
-- pagina zou anders zesduizend producten moeten ophalen om te kunnen tellen.
-- -----------------------------------------------------------------------------
create or replace function public.standaardprijs_indeling()
returns table (
    hoofdgroep text,
    subgroep   text,
    volgorde   integer,
    aantal     bigint
)
language sql
stable
security invoker
set search_path = public
as $$
    with telling as (
        select s.hoofdgroep as hoofd, s.subgroep as sub, count(*)::bigint as aantal
          from public.standaardprijzen s
         group by s.hoofdgroep, s.subgroep
    )

    -- 1. De afdeling zelf, met het totaal van al zijn laden.
    select t.hoofd,
           null::text,
           0,
           sum(t.aantal)::bigint
      from telling t
     where t.hoofd is not null
     group by t.hoofd

    union all

    -- 2. De laden waar werkelijk iets in ligt, in de volgorde van onze indeling.
    select g.hoofdgroep,
           g.subgroep,
           g.volgorde,
           t.aantal
      from public.eigen_groepen g
      join telling t on t.hoofd = g.hoofdgroep and t.sub = g.subgroep

    union all

    -- 3. De restbak: nog niet ingedeeld.
    select null::text,
           null::text,
           0,
           t.aantal
      from telling t
     where t.hoofd is null

    order by 1 nulls last, 3, 2;
$$;

grant execute on function public.standaardprijs_indeling() to authenticated, service_role;

comment on function public.standaardprijs_indeling() is
    'Onze eigen indeling met het aantal standaardprijzen dat er nu onder hangt. '
    'Een lege subgroep is de regel van de afdeling zelf; een lege hoofdgroep is '
    'de restbak met producten die nog nergens onder hangen. Voedt de keuzelijst '
    'van de standaardprijzen-pagina.';


-- -----------------------------------------------------------------------------
-- De oude keuzelijst op de groepsnamen van de winkel zelf vervalt. Die
-- groepsnamen blijven gewoon bij elk product staan — de pagina laat ze zien als
-- verfijning binnen een lade — maar ze zijn niet langer de ingang.
-- -----------------------------------------------------------------------------
drop function if exists public.standaardprijs_groepen();
