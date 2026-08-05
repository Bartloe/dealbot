-- =============================================================================
--  Dealbot — de groepenlijst van het profielscherm werkt weer
--
--  Versie      : 1.0
--  Reden       : Sinds 12_gebruikersbeheer.sql gaf het profielscherm bij het
--                eerste zoekveld de melding "De productgroepen konden niet
--                worden opgehaald". In dat script kreeg eigen_indeling() de
--                controle op een geblokkeerd account erbij en werd hij daarvoor
--                omgezet van een gewone query naar een programmaatje. Die
--                striktere vorm struikelt over het totaal van een afdeling: het
--                optellen van hele getallen levert een kommagetal op, terwijl de
--                functie een heel getal belooft. Postgres weigerde daarop het
--                hele antwoord, dus kwam er geen enkele afdeling terug.
--
--                De optelling wordt nu teruggezet naar een heel getal. Verder
--                verandert er niets: dezelfde afdelingen, dezelfde laden,
--                dezelfde aantallen en dezelfde controle op een blokkade.
--  Datum       : 05-08-2026 11:35
--
--  Onderdelen:
--    eigen_indeling()  - het totaal per afdeling weer als heel getal
--
--  Volgorde: na 13_picnic.sql. Opnieuw uit te voeren zonder schade.
--  Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================

create or replace function public.eigen_indeling()
returns table (
    hoofdgroep text,
    subgroep   text,
    volgorde   integer,
    aantal     bigint
)
language plpgsql
stable
security definer
set search_path = public
as $$
begin
    if not public.mag_meedoen() then
        raise exception 'Je account is geblokkeerd.' using errcode = '42501';
    end if;

    return query
    with telling as (
        select a.hoofdgroep as hoofd, a.subgroep as sub, count(*)::bigint as aantal
          from public.aanbiedingen a
         where a.hoofdgroep is not null
         group by a.hoofdgroep, a.subgroep
    )
    -- De afdeling zelf; volgorde 0 zet hem boven zijn eigen laden. Het optellen
    -- van de laden levert een kommagetal op, vandaar dat het er expliciet weer
    -- als heel getal uit komt.
    select g.hoofdgroep,
           null::text,
           0,
           coalesce((select sum(t.aantal) from telling t where t.hoofd = g.hoofdgroep), 0)::bigint
      from (select distinct eg.hoofdgroep from public.eigen_groepen eg) g

    union all

    select g.hoofdgroep,
           g.subgroep,
           g.volgorde,
           coalesce((select t.aantal from telling t
                      where t.hoofd = g.hoofdgroep and t.sub = g.subgroep), 0)::bigint
      from public.eigen_groepen g

    order by 1, 3, 2;
end;
$$;

grant execute on function public.eigen_indeling() to authenticated, service_role;

comment on function public.eigen_indeling() is
    'Onze eigen indeling met het aantal aanbiedingen dat er nu onder hangt. Een '
    'lege subgroep is de regel van de afdeling zelf, met het totaal van de hele '
    'afdeling. Voedt de keuzelijst op het profielscherm.';
