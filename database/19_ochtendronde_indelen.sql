-- =============================================================================
--  Dealbot — de beheerpagina meldt onvertaalde winkelgroepen
--
--  Versie      : 1.0
--  Reden       : De ochtendronde deelt voortaan zelf in, maar zonder ooit een
--                AI-vraag te stellen: hij past alleen het vertaalboekje toe dat
--                er al is. Dat houdt de ronde voorspelbaar en houdt de
--                Gemini-sleutels vrij voor de folderlezer.
--
--                Daarmee ontstaat één blinde vlek: brengt een winkel nieuwe
--                groepsnamen mee — en een nieuwe keten brengt er in één klap
--                honderden — dan blijven die onvertaald, en hangen hun producten
--                nergens onder. De ronde zwijgt daarover, want hij mag niet
--                vertalen.
--
--                Deze telling maakt dat zichtbaar: per winkel hoeveel van zijn
--                groepsnamen nog buiten het boekje vallen. Staat er een getal,
--                dan is dat het sein om het vertalen met de hand te starten
--                (`python scripts/indeel.py`).
--  Datum       : 06-08-2026 15:20
--
--  Onderdelen:
--    beheer_kwaliteit()  - kolom onvertaalde_groepen erbij
--
--  Volgorde: na 18_eigenschapgroepen.sql. Opnieuw uit te voeren zonder schade.
--  Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- De kwaliteitscijfers, met de onvertaalde groepsnamen erbij.
--
-- Vergeleken wordt de volledige groepenlijst van de winkel
-- (bekende_productgroepen, het hele assortiment) met het vertaalboekje
-- (groep_koppelingen). Hoofdletters tellen daarbij niet mee: het indeelscript
-- vergelijkt ook zonder, dus anders zou hier iets als onvertaald gelden wat het
-- script wél terugvindt.
--
-- Een winkel die alleen een folder levert heeft geen groepenlijst en komt dus
-- op nul uit. Dat is juist: bij Vomar valt er niets te vertalen, daar beslist
-- de productnaam.
--
-- Het aantal ligt bewust náást "zonder indeling": die eerste zegt wat er stuk
-- is (producten zonder plek), deze zegt waaróm en wat eraan te doen is.
-- -----------------------------------------------------------------------------
drop function if exists public.beheer_kwaliteit();

create function public.beheer_kwaliteit()
returns table (
    winkel_id            smallint,
    winkel               text,
    actief               boolean,
    aanbiedingen         bigint,
    zonder_kiloprijs     bigint,
    zonder_indeling      bigint,
    standaardprijzen     bigint,
    prijzen_zonder_kilo  bigint,
    onvertaalde_groepen  bigint
)
language plpgsql
stable
security definer
set search_path = public
as $$
begin
    if not public.is_beheerder() then
        raise exception 'Alleen de beheerder mag dit opvragen.' using errcode = '42501';
    end if;

    return query
    select w.id,
           w.naam,
           w.actief,
           coalesce(a.totaal, 0),
           coalesce(a.zonder_kilo, 0),
           coalesce(a.zonder_groep, 0),
           coalesce(p.totaal, 0),
           coalesce(p.zonder_kilo, 0),
           coalesce(g.open_groepen, 0)
      from public.winkels w
      left join (
          select ab.winkel_id,
                 count(*)::bigint as totaal,
                 count(*) filter (
                     where ab.prijs_per_eenheid is null or ab.prijs_per_eenheid <= 0
                 )::bigint as zonder_kilo,
                 count(*) filter (where ab.hoofdgroep is null)::bigint as zonder_groep
            from public.aanbiedingen ab
           group by ab.winkel_id
      ) a on a.winkel_id = w.id
      left join (
          select sp.winkel_id,
                 count(*)::bigint as totaal,
                 count(*) filter (
                     where sp.prijs_per_eenheid is null or sp.prijs_per_eenheid <= 0
                 )::bigint as zonder_kilo
            from public.standaardprijzen sp
           group by sp.winkel_id
      ) p on p.winkel_id = w.id
      left join (
          select bp.winkel_id, count(*)::bigint as open_groepen
            from public.bekende_productgroepen bp
           where not exists (
               select 1
                 from public.groep_koppelingen gk
                where gk.winkel_id = bp.winkel_id
                  and lower(btrim(gk.productgroep)) = lower(btrim(bp.productgroep))
           )
           group by bp.winkel_id
      ) g on g.winkel_id = w.id
     order by w.id;
end;
$$;

grant execute on function public.beheer_kwaliteit() to authenticated;

comment on function public.beheer_kwaliteit() is
    'Per winkel hoeveel aanbiedingen en standaardprijzen er staan, hoeveel '
    'daarvan geen kiloprijs of geen plek in onze indeling hebben, en hoeveel '
    'groepsnamen van die winkel nog niet vertaald zijn. Alleen voor de beheerder.';
