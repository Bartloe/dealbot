-- =============================================================================
--  Dealbot — onze eigen productindeling van twee lagen
--
--  Versie      : 1.0
--  Reden       : Elke keten deelt zijn assortiment anders in. Samen leverde dat
--                2606 losse groepsnamen op, en met één zoekvraag vond je nooit
--                alle winkels: Albert Heijn zegt "Koffiebonen", Jumbo zegt
--                "lokaal Koffiebonen", Dirk gooit alles op één hoop en de
--                voorgelezen Vomar-folder levert helemaal geen groep.
--
--                Hier komt daarom één eigen indeling te staan — hoofdgroep en
--                subgroep, in onze eigen woorden — met een vertaalboekje dat
--                elke winkelgroep daaronder hangt. De groep van de winkel zelf
--                blijft gewoon staan: die is de bron van de vertaling en op de
--                winkelpagina (bladeren door één winkel) juist de logische.
--  Datum       : 03-08-2026 22:40
--
--  Onderdelen:
--    eigen_groepen      - onze indeling: hoofdgroep met subgroep
--    groep_koppelingen  - vertaalboekje: winkelgroep -> onze groep
--    aanbiedingen       - twee velden erbij: hoofdgroep en subgroep
--    eigen_groep_telling() - hoeveel aanbiedingen er nu onder elke groep hangen
--
--  Dit script is opnieuw uit te voeren zonder schade (alles is "if not exists").
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Onze eigen indeling.
--
-- Elke regel is één subgroep met de hoofdgroep waar hij onder hangt. Het skelet
-- is één keer overgenomen van de winkelindeling van Albert Heijn (29 afdelingen
-- met 313 laden) en daarna van ons: het verandert niet mee als Albert Heijn
-- morgen iets hernoemt.
--
-- De lijst wordt door het indeelscript gevuld vanuit indeling.py, zodat de
-- website en het ophaalscript altijd dezelfde indeling gebruiken.
-- -----------------------------------------------------------------------------
create table if not exists public.eigen_groepen (
    id          integer generated always as identity primary key,
    hoofdgroep  text not null,
    subgroep    text not null,
    volgorde    integer not null default 0,

    constraint eigen_groep_uniek unique (hoofdgroep, subgroep)
);

create index if not exists idx_eigen_groepen_hoofd
    on public.eigen_groepen (hoofdgroep, volgorde);

comment on table public.eigen_groepen is
    'Onze eigen productindeling van twee lagen. Losstaand van de indeling die '
    'de winkels zelf hanteren.';


-- -----------------------------------------------------------------------------
-- Het vertaalboekje: de groepsnaam van een winkel onder onze indeling.
--
-- Bewust per groep en niet per product: er zijn 2606 winkelgroepen tegenover
-- tienduizenden producten, een groep vertalen dekt er dus duizenden in één klap,
-- en volgende week gelden dezelfde groepen nog gewoon.
--
-- De subgroep mag leeg zijn. Dat is het eerlijke antwoord bij een winkelgroep
-- die grover is dan onze indeling: in Dirks "Koffie & cacao" zitten bonen én
-- cacaopoeder door elkaar, dus daar valt alleen de hoofdgroep met zekerheid
-- over te zeggen. Het ophaalscript vult de subgroep dan aan met wat er in de
-- productnaam staat.
--
-- "herkomst" zegt wie de koppeling gelegd heeft: de AI, of een mens die hem
-- daarna heeft verbeterd. Een verbetering met de hand wordt niet overschreven.
-- -----------------------------------------------------------------------------
create table if not exists public.groep_koppelingen (
    id            bigint generated always as identity primary key,
    winkel_id     smallint not null references public.winkels (id) on delete cascade,

    -- De groepsnaam precies zoals de winkel hem levert.
    productgroep  text not null,

    hoofdgroep    text not null,
    subgroep      text,

    -- Een gemengde groep bevat van alles door elkaar, waarvan een deel van ons
    -- is: "IJskoffie en milkshakes" bijvoorbeeld. Daar telt een product pas mee
    -- als zijn eigen naam laat zien dat het erbij hoort. Zonder dit onderscheid
    -- moet je kiezen tussen de hele groep binnenlaten (dan komen er milkshakes
    -- bij de koffie) of de hele groep weren (dan verdwijnt de ijskoffie).
    gemengd       boolean not null default false,

    herkomst      text not null default 'ai',   -- 'ai' of 'hand'
    aangemaakt_op timestamptz not null default now(),
    gewijzigd_op  timestamptz not null default now(),

    constraint koppeling_uniek unique (winkel_id, productgroep)
);

create index if not exists idx_koppelingen_winkelgroep
    on public.groep_koppelingen (winkel_id, lower(productgroep));

comment on table public.groep_koppelingen is
    'Vertaalboekje van winkelgroep naar onze eigen indeling. Een lege subgroep '
    'betekent: de winkelgroep is te grof, de productnaam moet het aanvullen.';


-- -----------------------------------------------------------------------------
-- Twee velden erbij op de aanbieding.
--
-- Ze staan naast de bestaande "productgroep" en vervangen die niet: dat veld
-- blijft de indeling van de winkel zelf, en dat is precies wat je wilt zien als
-- je op de winkelpagina door één folder bladert.
--
-- Beide velden mogen leeg zijn. Dat is de restbak — zichtbaar, zodat we kunnen
-- bijsturen in plaats van dat er stilletjes aanbiedingen uit beeld verdwijnen.
-- -----------------------------------------------------------------------------
alter table public.aanbiedingen
    add column if not exists hoofdgroep text,
    add column if not exists subgroep   text;

create index if not exists idx_aanbiedingen_hoofdgroep
    on public.aanbiedingen (hoofdgroep);

create index if not exists idx_aanbiedingen_subgroep
    on public.aanbiedingen (subgroep);

comment on column public.aanbiedingen.hoofdgroep is
    'Onze eigen hoofdgroep. Leeg = nog niet ingedeeld (de restbak).';
comment on column public.aanbiedingen.subgroep is
    'Onze eigen subgroep. Leeg terwijl de hoofdgroep gevuld is, betekent: we '
    'weten de afdeling wel maar niet de precieze plek.';


-- -----------------------------------------------------------------------------
-- Hetzelfde voor de standaardprijzen, zodat die pagina straks dezelfde
-- indeling kan gebruiken als de aanbiedingen.
-- -----------------------------------------------------------------------------
alter table public.standaardprijzen
    add column if not exists hoofdgroep text,
    add column if not exists subgroep   text;

create index if not exists idx_standaardprijzen_hoofdgroep
    on public.standaardprijzen (hoofdgroep);


-- -----------------------------------------------------------------------------
-- Hoeveel aanbiedingen hangen er nu onder elke groep?
--
-- De keuzelijst op het profielscherm laat dat achter elke groep zien ("nu 34
-- aanbiedingen"), zodat je ziet of een zoekvraag deze week iets oplevert. Als
-- functie, omdat de website hooguit 1000 regels per keer terugkrijgt en een
-- telling over tienduizenden aanbiedingen daar niet in past.
-- -----------------------------------------------------------------------------
create or replace function public.eigen_groep_telling()
returns table (hoofdgroep text, subgroep text, aantal bigint)
language sql
stable
security definer
set search_path = public
as $$
    select a.hoofdgroep, a.subgroep, count(*)::bigint
      from public.aanbiedingen a
     where a.hoofdgroep is not null
     group by a.hoofdgroep, a.subgroep
     order by a.hoofdgroep, a.subgroep;
$$;

grant execute on function public.eigen_groep_telling() to authenticated, service_role;


-- =============================================================================
--  Toegangsregels — de indeling en het vertaalboekje mag iedereen die is
--  ingelogd lezen; vullen doet alleen het ophaalscript met de geheime sleutel.
-- =============================================================================

alter table public.eigen_groepen     enable row level security;
alter table public.groep_koppelingen enable row level security;

drop policy if exists "eigen groepen lezen" on public.eigen_groepen;
create policy "eigen groepen lezen" on public.eigen_groepen
    for select to authenticated using (true);

drop policy if exists "koppelingen lezen" on public.groep_koppelingen;
create policy "koppelingen lezen" on public.groep_koppelingen
    for select to authenticated using (true);
