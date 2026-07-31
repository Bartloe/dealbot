-- =============================================================================
--  Dealbot — een blijvende lijst van productgroepen
--
--  Versie      : 1.0
--  Reden       : De keuzelijst op het profielscherm werd gevuld met alleen de
--                groepen die deze week in de aanbiedingen zaten. Daardoor kon je
--                geen zoekvraag zetten op iets dat nu niet in de bonus is —
--                terwijl een zoekvraag juist bedoeld is om te wáchten tot dat
--                gebeurt. "Koffiebonen" was niet te kiezen om precies die reden.
--                Vanaf nu onthoudt Dealbot elke groep die hij ooit is
--                tegengekomen, en staat erbij hoeveel er op dit moment in zit.
--  Datum       : 31-07-2026 11:31
--
--  Onderdelen:
--    bekende_productgroepen    - alle groepen die ooit zijn langsgekomen
--    onthoud_productgroepen()  - vult die lijst aan tijdens de ophaalronde
--    productgroepen()          - voedt de keuzelijst; put nu uit de vaste lijst
--
--  Dit script is opnieuw uit te voeren zonder schade.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- De vaste lijst.
--
-- De aanbiedingen zelf worden elke ochtend vervangen; deze lijst juist niet. Hij
-- groeit alleen maar aan. "laatst_gezien" laat zien hoe actueel een groep is:
-- een groep die maanden niet is langsgekomen, bestaat bij die winkel misschien
-- niet meer.
-- -----------------------------------------------------------------------------
create table if not exists public.bekende_productgroepen (
    winkel_id     smallint    not null references public.winkels (id),
    productgroep  text        not null,
    eerst_gezien  timestamptz not null default now(),
    laatst_gezien timestamptz not null default now(),

    primary key (winkel_id, productgroep)
);

comment on table public.bekende_productgroepen is
    'Elke productgroep die ooit in de aanbiedingen van een winkel is gezien. '
    'Voedt de keuzelijst op het profielscherm, zodat je ook kunt wachten op een '
    'groep die deze week niet in de bonus is.';


-- -----------------------------------------------------------------------------
-- Bijhouden tijdens de ophaalronde.
--
-- Het ophaalscript geeft na elke winkel de gevonden groepen door. Bestaat een
-- groep al, dan blijft "eerst_gezien" staan en schuift alleen "laatst_gezien"
-- op; dat is precies het verschil dat we willen kunnen zien.
-- -----------------------------------------------------------------------------
create or replace function public.onthoud_productgroepen(
    p_winkel_id smallint,
    p_groepen   text[]
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    aantal integer;
begin
    insert into public.bekende_productgroepen (winkel_id, productgroep)
    select p_winkel_id, btrim(groep)
      from unnest(p_groepen) as groep
     where nullif(btrim(groep), '') is not null
     group by btrim(groep)
    on conflict (winkel_id, productgroep) do update
        set laatst_gezien = now();

    get diagnostics aantal = row_count;
    return aantal;
end;
$$;

-- Alleen het ophaalscript (met de geheime sleutel) hoort deze lijst te vullen.
-- De website mag hem uitsluitend lezen.
revoke execute on function public.onthoud_productgroepen(smallint, text[]) from public;
revoke execute on function public.onthoud_productgroepen(smallint, text[]) from anon, authenticated;
grant  execute on function public.onthoud_productgroepen(smallint, text[]) to service_role;

comment on function public.onthoud_productgroepen(smallint, text[]) is
    'Vult de vaste groepenlijst aan met de groepen van één ophaalronde. Nieuwe '
    'groepen komen erbij, bestaande krijgen een nieuw moment van laatst gezien.';


-- -----------------------------------------------------------------------------
-- De keuzelijst zelf.
--
-- Put uit de vaste lijst en telt erbij hoeveel aanbiedingen er op dít moment in
-- de groep zitten. Nul is een geldig antwoord en verbergt de groep niet: het
-- scherm zegt dan "nu niets", en de zoekvraag blijft klaarstaan tot het weer
-- zover is.
-- -----------------------------------------------------------------------------
drop function if exists public.productgroepen();

create function public.productgroepen()
returns table (
    winkel_id     smallint,
    winkel        text,
    productgroep  text,
    aantal        bigint,
    laatst_gezien date
)
language sql
stable
security invoker
set search_path = public
as $$
    select
        g.winkel_id,
        w.naam,
        g.productgroep,
        count(a.id),
        g.laatst_gezien::date
    from public.bekende_productgroepen g
    join public.winkels w on w.id = g.winkel_id
    left join public.aanbiedingen a
           on a.winkel_id = g.winkel_id
          and lower(a.productgroep) = lower(g.productgroep)
    group by g.winkel_id, w.naam, g.productgroep, g.laatst_gezien
    order by w.naam, g.productgroep;
$$;

comment on function public.productgroepen() is
    'Alle productgroepen die Dealbot ooit bij een winkel heeft gezien, met het '
    'aantal aanbiedingen dat er op dit moment in zit en wanneer de groep voor '
    'het laatst langskwam. Voedt de keuzelijst op het profielscherm.';


-- -----------------------------------------------------------------------------
-- Toegangsregels — lezen mag iedereen die is ingelogd, wijzigen niemand.
-- -----------------------------------------------------------------------------
alter table public.bekende_productgroepen enable row level security;

drop policy if exists "productgroepen lezen" on public.bekende_productgroepen;
create policy "productgroepen lezen" on public.bekende_productgroepen
    for select to authenticated using (true);


-- -----------------------------------------------------------------------------
-- Eenmalig bijvullen met wat er nu in de aanbiedingen staat, zodat de lijst
-- meteen gevuld is en niet pas na de eerstvolgende ophaalronde.
-- -----------------------------------------------------------------------------
insert into public.bekende_productgroepen (winkel_id, productgroep)
select a.winkel_id, btrim(a.productgroep)
  from public.aanbiedingen a
 where nullif(btrim(a.productgroep), '') is not null
 group by a.winkel_id, btrim(a.productgroep)
on conflict (winkel_id, productgroep) do nothing;
