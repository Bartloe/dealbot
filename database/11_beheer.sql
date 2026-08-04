-- =============================================================================
--  Dealbot — de beheerpagina: wie is beheerder, en wat mag hij zien
--
--  Versie      : 1.0
--  Reden       : Tot nu toe was er geen plek waar te zien is hoe het ophalen
--                van vanochtend is gegaan. Bij een storing bleef de site er
--                gewoon uitzien alsof alles klopte, alleen met oudere prijzen.
--                Deze uitbreiding maakt één account beheerder en geeft dat
--                account twee overzichten: hoe de laatste ronde per winkel is
--                gegaan, en hoe compleet de gegevens zijn die eruit kwamen.
--  Datum       : 04-08-2026 22:05
--
--  Onderdelen:
--    profielen.beheerder - het vlaggetje dat één account beheerder maakt
--    is_beheerder()      - vraagt of de ingelogde gebruiker beheerder is
--    scan_logs.soort     - onderscheidt aanbiedingen, assortiment en folder
--    beheer_runstatus()  - de laatste ronde per winkel, met storing en aantal
--    beheer_kwaliteit()  - hoeveel er per winkel binnenkwam, en wat er ontbreekt
--
--  Let op: onderaan staat het e-mailadres dat beheerder wordt. Log je met een
--  ander adres in bij Dealbot, pas dan díe regel aan vóór het uitvoeren.
--
--  Volgorde: na 10_indeling_in_profiel.sql. Opnieuw uit te voeren zonder schade.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Stap 1 — het beheerdersvlaggetje.
--
-- Beheerder zijn is een eigenschap van het account, niet van de pagina. De
-- website is openbaar: wie de beheerpagina weet te vinden krijgt hem te zien,
-- maar zonder dit vlaggetje weigert de database elk antwoord. Het slot zit dus
-- op de kluis en niet op het bordje ervoor.
-- -----------------------------------------------------------------------------
alter table public.profielen
    add column if not exists beheerder boolean not null default false;

comment on column public.profielen.beheerder is
    'Alleen dit account mag de beheerpagina gebruiken. Niet via de website te '
    'wijzigen; alleen met de hand in de database.';


-- Een gebruiker mag zijn eigen profiel bijwerken — dat is nodig voor zijn naam.
-- Zonder deze beperking zou hij zichzelf ook beheerder kunnen maken, want de
-- toegangsregels gelden per regel en niet per veld. Daarom staat het wijzigen
-- vanaf de website nu uitsluitend open voor de weergavenaam.
revoke update on public.profielen from authenticated;
grant update (weergavenaam) on public.profielen to authenticated;


-- -----------------------------------------------------------------------------
-- Stap 2 — de vraag "ben ik beheerder?".
--
-- De website gebruikt hem om de menuknop wel of niet te tonen; de functies
-- hieronder gebruiken hem als slot. Draait met de rechten van de eigenaar,
-- zodat het antwoord niet afhangt van wat de gebruiker zelf mag lezen.
-- -----------------------------------------------------------------------------
create or replace function public.is_beheerder()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select coalesce(
        (select p.beheerder from public.profielen p where p.id = auth.uid()),
        false
    );
$$;

grant execute on function public.is_beheerder() to authenticated, service_role;

comment on function public.is_beheerder() is
    'Geeft terug of de ingelogde gebruiker beheerder is. Voor iedereen aan te '
    'roepen; het antwoord gaat alleen over jezelf.';


-- -----------------------------------------------------------------------------
-- Stap 3 — wat voor soort ronde het logboek beschrijft.
--
-- Vomar levert twee heel verschillende dingen onder hetzelfde winkelnummer: de
-- gewone schapprijzen uit zijn webwinkel en de aanbiedingen uit de folder die
-- door een AI wordt voorgelezen. In het logboek waren die niet uit elkaar te
-- houden, waardoor een geslaagde prijzenronde een mislukte folder kon maskeren.
--
-- Bestaande regels krijgen 'aanbiedingen'; dat klopt voor de vier ketens die
-- elke ochtend draaien, en de oude Vomar-regels zijn geschiedenis die verder
-- nergens voor gebruikt wordt.
-- -----------------------------------------------------------------------------
alter table public.scan_logs
    add column if not exists soort text not null default 'aanbiedingen';

alter table public.scan_logs drop constraint if exists scan_log_soort_bekend;
alter table public.scan_logs add constraint scan_log_soort_bekend
    check (soort in ('aanbiedingen', 'assortiment', 'folder'));

comment on column public.scan_logs.soort is
    'aanbiedingen = de weekaanbiedingen van de winkel, assortiment = de gewone '
    'schapprijzen, folder = de weekfolder die door een AI is voorgelezen.';

create index if not exists idx_scan_logs_winkel_soort
    on public.scan_logs (winkel_id, soort, gestart_op desc);


-- -----------------------------------------------------------------------------
-- Stap 4 — hoe de laatste ronde per winkel is gegaan.
--
-- Eén regel per winkel per soort ronde: wanneer, gelukt of mislukt, hoeveel er
-- binnenkwam en bij een storing de melding. Een winkel die nog nooit heeft
-- gedraaid blijft in de lijst staan met lege velden — juist dát wil je zien.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_runstatus()
returns table (
    winkel_id  smallint,
    winkel     text,
    actief     boolean,
    soort      text,
    gestart_op timestamptz,
    klaar_op   timestamptz,
    status     text,
    aantal     integer,
    melding    text
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
    with laatste as (
        select distinct on (l.winkel_id, l.soort)
               l.winkel_id, l.soort, l.gestart_op, l.klaar_op,
               l.status, l.aantal, l.melding
          from public.scan_logs l
         where l.winkel_id is not null
         order by l.winkel_id, l.soort, l.gestart_op desc
    )
    select w.id, w.naam, w.actief,
           s.soort, s.gestart_op, s.klaar_op, s.status, s.aantal, s.melding
      from public.winkels w
      left join laatste s on s.winkel_id = w.id
     order by w.id, s.soort;
end;
$$;

grant execute on function public.beheer_runstatus() to authenticated;

comment on function public.beheer_runstatus() is
    'De laatste ophaalronde per winkel en per soort, met status, aantal en '
    'storingsmelding. Alleen voor de beheerder.';


-- -----------------------------------------------------------------------------
-- Stap 5 — hoe compleet de gegevens zijn die binnenkwamen.
--
-- Twee dingen ontbreken wel eens en dat is precies wat op de site opvalt: een
-- aanbieding zonder kiloprijs is niet te vergelijken, en een aanbieding zonder
-- plek in onze eigen indeling is via het profiel niet te vinden. Hier staan ze
-- per winkel geteld, zodat in één blik te zien is waar het schuurt.
--
-- Geteld wordt alles wat er nú in de database staat, niet alleen wat vandaag
-- geldig is: het gaat om de oogst van de laatste ronde.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_kwaliteit()
returns table (
    winkel_id            smallint,
    winkel               text,
    actief               boolean,
    aanbiedingen         bigint,
    zonder_kiloprijs     bigint,
    zonder_indeling      bigint,
    standaardprijzen     bigint,
    prijzen_zonder_kilo  bigint
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
           coalesce(p.zonder_kilo, 0)
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
     order by w.id;
end;
$$;

grant execute on function public.beheer_kwaliteit() to authenticated;

comment on function public.beheer_kwaliteit() is
    'Per winkel hoeveel aanbiedingen en standaardprijzen er staan, en hoeveel '
    'daarvan geen kiloprijs of geen plek in onze indeling hebben. Alleen voor '
    'de beheerder.';


-- -----------------------------------------------------------------------------
-- Stap 6 — de beheerder aanwijzen.
--
-- Hieronder staat het e-mailadres waarmee de beheerder in Dealbot inlogt. Is dat
-- een ander adres, pas dan deze regel aan; zonder treffer verandert er niets en
-- blijft de beheerpagina voor iedereen dicht.
-- -----------------------------------------------------------------------------
update public.profielen p
   set beheerder = true
  from auth.users u
 where u.id = p.id
   and lower(u.email) = lower('alias01@hotmail.nl');
