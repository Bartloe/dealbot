-- =============================================================================
--  Dealbot — eigenschapgroepen, en de restbak leeghalen
--
--  Versie      : 1.0
--  Reden       : Bijna 2500 producten stonden nergens. Niet omdat we niet wisten
--                waar ze hoorden, maar door een regel die te streng was: bij een
--                grove winkelgroep telde een product pas mee als de productnaam
--                zelf bewees waar het hoorde. "Knorr Good noodles kip" in de
--                groep "Soepen" bewijst niets, dus verdween het — terwijl de
--                winkel allang gezegd had dat het soep is. Dat was 93% van de
--                hele restbak.
--
--                Voortaan valt zo'n product terug op de afdeling van de groep:
--                geen lade, wél vindbaar. Daarvoor moest er één ding bij, want
--                terugvallen mag niet altijd. De groepsnaam "Glutenvrij" noemt
--                geen afdeling — glutenvrij brood, pasta en bier liggen door de
--                hele winkel — dus terugvallen zou daar de hele groep op één hoop
--                gooien. Zulke groepen heten nu eigenschapgroepen: geen afdeling,
--                alleen de productnaam beslist.
--
--                Het oude vlaggetje "gemengd" gooide die twee op één hoop en
--                verdwijnt daarom.
--  Datum       : 06-08-2026 01:30
--
--  Onderdelen:
--    Stap 1 - het vlaggetje hernoemen naar wat het nu betekent
--    Stap 2 - de 267 groepen die "gemengd" waren opnieuw laten beoordelen
--
--  Volgorde: na 17_ophalen_starten.sql. Opnieuw uit te voeren zonder schade.
--
--  LET OP — na dit bestand moet "python scripts/indeel.py" draaien. Stap 2 haalt
--  de oude oordelen weg; pas dat script vraagt de AI om nieuwe (ongeveer vijf
--  AI-vragen) en deelt daarna alles opnieuw in.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Stap 1 — het vlaggetje hernoemen.
--
-- "gemengd" betekende: in deze groep ligt van alles door elkaar. Dat gold zowel
-- voor "Soepen" (grof, maar de afdeling staat vast) als voor "Glutenvrij" (geen
-- afdeling te noemen), en juist dat verschil is nu de hele kern. De nieuwe naam
-- dekt alleen het tweede geval.
-- -----------------------------------------------------------------------------
do $$
begin
    if exists (
        select 1 from information_schema.columns
         where table_schema = 'public'
           and table_name   = 'groep_koppelingen'
           and column_name  = 'gemengd'
    ) then
        alter table public.groep_koppelingen
            rename column gemengd to eigenschapgroep;
    end if;
end $$;

alter table public.groep_koppelingen
    add column if not exists eigenschapgroep boolean not null default false;

comment on column public.groep_koppelingen.eigenschapgroep is
    'De groepsnaam noemt geen afdeling maar een eigenschap, gelegenheid of vorm '
    '("Glutenvrij", "Kerst", "Wit"). Die producten liggen door de hele winkel, '
    'dus er valt geen afdeling over te zeggen en beslist de productnaam. De '
    'hoofdgroep is bij zo''n regel dan ook leeg — dat betekent hier iets anders '
    'dan bij een groep die helemaal niet bij ons hoort.';

comment on table public.groep_koppelingen is
    'Vertaalboekje van winkelgroep naar onze eigen indeling. Een lege subgroep '
    'betekent: de winkelgroep is te grof, de productnaam mag hem aanvullen en '
    'anders blijft de afdeling staan. Een lege hoofdgroep betekent "hoort niet '
    'bij ons", tenzij eigenschapgroep aan staat.';


-- -----------------------------------------------------------------------------
-- Stap 2 — de oude "gemengde" oordelen weghalen.
--
-- Die 267 groepen zijn met de oude vraagstelling beoordeeld, waarin er maar één
-- soort "past niet precies" bestond. Hun antwoord kan nu twee kanten op: "Soepen"
-- wordt een gewone grove groep met een afdeling, "Glutenvrij" wordt een
-- eigenschapgroep zonder. Dat kunnen we niet raden, dus gaan ze opnieuw langs de
-- AI. Weghalen is genoeg: elke groepsnaam die niet in het boekje staat wordt
-- vanzelf opnieuw gevraagd.
--
-- Wat een mens met de hand heeft rechtgezet blijft staan. Die oordelen zijn
-- betrouwbaarder dan wat de AI ervan maakt, en een verbetering met de hand hoort
-- niet zomaar te verdwijnen. Wel gaat het vlaggetje daar uit: het stond voor de
-- oude betekenis, en zo'n regel heeft een afdeling — dan is terugvallen op die
-- afdeling het juiste gedrag. Op dit moment bestaan er geen handmatige regels,
-- dus dit is er voor later.
-- -----------------------------------------------------------------------------
delete from public.groep_koppelingen
 where eigenschapgroep is true
   and herkomst <> 'hand';

update public.groep_koppelingen
   set eigenschapgroep = false
 where eigenschapgroep is true;
