-- =============================================================================
--  Dealbot — de groepenlijst volgt voortaan de winkelindeling
--
--  Versie      : 1.0
--  Reden       : De productgroep van Albert Heijn kwam van het schaplabel op het
--                product, en daar staat het merk in: "Lavazza koffiebonen". Zo
--                ontstonden 1791 groepen en was er geen manier om koffiebonen van
--                álle merken te vinden. Vanaf nu is de groep de lade uit de
--                winkelindeling ("Koffiebonen"), waarvan er 313 zijn. Het merk
--                heeft zijn eigen zoekveld, dus er gaat niets verloren.
--
--                Dat vraagt twee dingen van de database. De oude merkgroepen
--                moeten weg, en de groepenlijst moet voortaan ook kúnnen
--                opschonen: hij groeide tot nu toe alleen maar aan.
--  Datum       : 01-08-2026 21:45
--
--  Onderdelen:
--    zoekvragen                 - een zoekvraag op een merkschap gaat naar vrije tekst
--    opruimen                   - de oude groepen van Albert Heijn verdwijnen
--    vervang_productgroepen()   - vervangt de indeling van één winkel, met een rem
--    onthoud_productgroepen()   - vervalt; de nieuwe functie neemt het over
--
--  Volgorde: eerst dit script uitvoeren, daarna een ophaalronde draaien. Tussen
--  die twee momenten is de keuzelijst van Albert Heijn leeg.
--
--  Dit script is opnieuw uit te voeren zonder schade.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Stap 1 — bestaande zoekvragen op een merkschap redden.
--
-- Wie "Lavazza koffiebonen" had aangevinkt, zou vanaf nu niets meer vinden: die
-- groep bestaat straks niet meer. Zo'n zoekvraag verhuist daarom naar vrije
-- tekst, want die zoekt in merk en productnaam en levert vrijwel dezelfde
-- treffers. Stond er al vrije tekst in, dan blijft die staan en vervalt alleen
-- de groep — anders zou de zoekvraag strenger worden dan ooit bedoeld.
--
-- Groepen die ook bij een andere winkel bestaan blijven met rust: die zoekvraag
-- werkt daar gewoon door.
-- -----------------------------------------------------------------------------
update public.zoekvragen z
   set vrije_tekst  = coalesce(nullif(btrim(z.vrije_tekst), ''), z.productgroep),
       productgroep = null
 where nullif(btrim(z.productgroep), '') is not null
   and exists (
       select 1 from public.bekende_productgroepen g
        where g.winkel_id = 1
          and lower(g.productgroep) = lower(btrim(z.productgroep))
   )
   and not exists (
       select 1 from public.bekende_productgroepen g
        where g.winkel_id <> 1
          and lower(g.productgroep) = lower(btrim(z.productgroep))
   );


-- -----------------------------------------------------------------------------
-- Stap 2 — de oude indeling van Albert Heijn opruimen.
--
-- De eerstvolgende ophaalronde zet de 313 laden er meteen weer in. Dit kan niet
-- door de ronde zelf gedaan worden: die zou de oude namen naast de nieuwe laten
-- staan, en dan hield de keuzelijst 2100 regels over.
-- -----------------------------------------------------------------------------
delete from public.bekende_productgroepen where winkel_id = 1;


-- -----------------------------------------------------------------------------
-- Stap 3 — de indeling van een winkel vervangen in plaats van aanvullen.
--
-- Aanvullen was goed zolang de lijst uit de aanbiedingen kwam: wat deze week
-- niet in de bonus lag, mocht niet verdwijnen. Nu de lijst uit het hele
-- assortiment komt, is het omgekeerde waar: een groep die de winkel niet meer
-- gebruikt, hoort ook uit de keuzelijst te verdwijnen.
--
-- Met één rem erop. Levert een half mislukte ronde maar een handjevol groepen
-- op, dan wordt er niets weggegooid en alleen aangevuld. De grens ligt op de
-- helft van wat er stond, en op minstens tien groepen — Dirk heeft er maar
-- zeventien, dus een vaste ondergrens mag niet hoog liggen.
--
-- "eerst_gezien" blijft staan voor groepen die gewoon terugkomen; dat is de
-- enige plek waar te zien is hoe lang Dealbot een groep al kent.
-- -----------------------------------------------------------------------------
create or replace function public.vervang_productgroepen(
    p_winkel_id smallint,
    p_groepen   text[]
)
returns table (toegevoegd integer, verwijderd integer, behouden integer)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_nieuw     integer;
    v_bestaand  integer;
    v_opruimen  boolean;
begin
    create temporary table nieuwe_groepen on commit drop as
    select distinct btrim(groep) as productgroep
      from unnest(coalesce(p_groepen, '{}')) as groep
     where nullif(btrim(groep), '') is not null;

    select count(*) into v_nieuw from nieuwe_groepen;
    select count(*) into v_bestaand
      from public.bekende_productgroepen
     where winkel_id = p_winkel_id;

    v_opruimen := v_nieuw >= greatest(10, v_bestaand / 2);

    if not v_opruimen then
        raise warning
            'Winkel %: maar % groepen binnengekregen tegen % in de lijst; '
            'er wordt niets verwijderd.', p_winkel_id, v_nieuw, v_bestaand;
    end if;

    with weg as (
        delete from public.bekende_productgroepen g
         where g.winkel_id = p_winkel_id
           and v_opruimen
           and not exists (
               select 1 from nieuwe_groepen n where n.productgroep = g.productgroep
           )
        returning 1
    )
    select count(*) into verwijderd from weg;

    with erbij as (
        insert into public.bekende_productgroepen (winkel_id, productgroep)
        select p_winkel_id, n.productgroep from nieuwe_groepen n
        on conflict (winkel_id, productgroep) do update
            set laatst_gezien = now()
        returning (xmax = 0) as is_nieuw
    )
    select count(*) filter (where is_nieuw),
           count(*) filter (where not is_nieuw)
      into toegevoegd, behouden
      from erbij;

    drop table nieuwe_groepen;
    return next;
end;
$$;

-- Alleen het ophaalscript (met de geheime sleutel) hoort deze lijst te vullen.
revoke execute on function public.vervang_productgroepen(smallint, text[]) from public;
revoke execute on function public.vervang_productgroepen(smallint, text[]) from anon, authenticated;
grant  execute on function public.vervang_productgroepen(smallint, text[]) to service_role;

comment on function public.vervang_productgroepen(smallint, text[]) is
    'Zet de winkelindeling van één winkel in de groepenlijst: nieuwe groepen '
    'komen erbij, vervallen groepen gaan eruit. Bij een verdacht korte lijst '
    'wordt er niets verwijderd, zodat een half mislukte ronde geen schade doet.';


-- -----------------------------------------------------------------------------
-- Stap 4 — de oude functie opruimen; die wordt niet meer aangeroepen.
-- -----------------------------------------------------------------------------
drop function if exists public.onthoud_productgroepen(smallint, text[]);
