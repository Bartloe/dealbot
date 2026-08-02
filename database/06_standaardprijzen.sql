-- =============================================================================
--  Dealbot — standaardprijzen (gewone winkelprijzen, geen aanbiedingen)
--
--  Versie      : 1.0
--  Reden       : Vomar publiceert geen aanbiedingen maar wél zijn hele
--                assortiment met de gewone winkelprijs, het merk, de inhoud en
--                bij élk product een streepjescode. Daarmee kan de
--                standaardprijzen-pagina eindelijk gevuld worden: wat kost iets
--                als er even geen aanbieding is?
--  Datum       : 02-08-2026 12:05
--
--  Onderdelen:
--    standaardprijzen           - één regel per product per winkel
--    standaardprijs_groepen()   - de groepen met hun aantallen, voor de pagina
--    winkel 5 (Vomar) aanzetten - stond uit omdat er geen aanbiedingen zijn
--
--  Dit script is opnieuw uit te voeren zonder schade (alles is "if not exists").
--  Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Standaardprijzen — het gewone schap, niet de bonus.
--
-- Bewust een eigen tabel en niet een vlaggetje bij de aanbiedingen: deze regels
-- hebben geen actietekst en geen einddatum, ze worden anders ververst (het hele
-- assortiment in één keer) en ze mogen niet meetellen in de aanbiedingenlijst.
-- -----------------------------------------------------------------------------
create table if not exists public.standaardprijzen (
    id                bigint generated always as identity primary key,
    winkel_id         smallint not null references public.winkels (id),

    -- Het artikelnummer bij de winkel, zodat een product wordt bijgewerkt in
    -- plaats van dubbel toegevoegd.
    bron_id           text not null,

    product_naam      text not null,
    merk              text,

    -- De indeling van de winkel, twee lagen. Vomar deelt drie lagen diep in:
    -- de onderste ("Koffiebonen") is de productgroep, de bovenste
    -- ("Frisdrank, sappen, koffie & thee") staat erbij zodat de pagina er een
    -- overzicht mee kan maken.
    afdeling          text,
    productgroep      text,

    prijs             numeric(10, 2),   -- de gewone schapprijs

    inhoud_waarde     numeric(12, 3),   -- bijv. 500 bij "500 gram"
    inhoud_eenheid    text,             -- 'g', 'kg', 'ml', 'l', 'stuk'
    prijs_per_eenheid numeric(12, 4),   -- omgerekend naar kilo/liter; leeg = onbekend
    eenheid_norm      text,             -- 'kg', 'l' of 'stuk'

    -- De streepjescode. Hiermee is hetzelfde product bij verschillende ketens
    -- aan elkaar te knopen, veel betrouwbaarder dan op naam raden. Niet uniek:
    -- dezelfde code kan bij meerdere winkels voorkomen, en dat is juist de
    -- bedoeling.
    ean               text,

    -- Dezelfde benadering op merk + productnaam als bij de aanbiedingen, zodat
    -- een standaardprijs ook te koppelen is aan een winkel die geen EAN geeft.
    product_sleutel   text not null,

    product_url       text,
    afbeelding_url    text,
    opgehaald_op      timestamptz not null default now(),

    -- Waar de vrije tekst op zoekt: merk en productnaam, in kleine letters.
    -- De productgroep zit hier bewust niet in, om dezelfde reden als bij de
    -- aanbiedingen: anders vindt "koffie" ook een pak thee.
    zoektekst text generated always as (
        lower(coalesce(merk, '') || ' ' || coalesce(product_naam, ''))
    ) stored,

    constraint standaardprijs_uniek_per_winkel unique (winkel_id, bron_id)
);

create index if not exists idx_standaardprijzen_zoektekst
    on public.standaardprijzen using gin (zoektekst gin_trgm_ops);

create index if not exists idx_standaardprijzen_groep
    on public.standaardprijzen (productgroep);

create index if not exists idx_standaardprijzen_ean
    on public.standaardprijzen (ean);

create index if not exists idx_standaardprijzen_sleutel
    on public.standaardprijzen (product_sleutel);

comment on table public.standaardprijzen is
    'De gewone winkelprijs per product, los van de weekaanbiedingen. Gevuld '
    'vanuit winkels die hun hele assortiment publiceren.';

comment on column public.standaardprijzen.ean is
    'Streepjescode. Bedoeld om hetzelfde product bij verschillende ketens aan '
    'elkaar te knopen; daarom bewust niet uniek.';


-- -----------------------------------------------------------------------------
-- De groepen voor het keuzemenu van de standaardprijzen-pagina.
--
-- Aparte functie omdat de database hooguit duizend regels per keer teruggeeft:
-- de pagina zou anders zelf zesduizend producten moeten ophalen om te kunnen
-- tellen hoeveel er in elke groep zitten.
-- -----------------------------------------------------------------------------
create or replace function public.standaardprijs_groepen()
returns table (afdeling text, productgroep text, aantal bigint)
language sql
stable
security invoker
set search_path = public
as $$
    select s.afdeling,
           s.productgroep,
           count(*) as aantal
      from public.standaardprijzen s
     where s.productgroep is not null
     group by s.afdeling, s.productgroep
     order by s.afdeling nulls last, s.productgroep;
$$;

comment on function public.standaardprijs_groepen() is
    'De productgroepen met hun aantal, voor het keuzemenu van de '
    'standaardprijzen-pagina.';


-- -----------------------------------------------------------------------------
-- Winkel 5 (Vomar) aanzetten.
--
-- Vomar stond uit omdat zijn aanbiedingen alleen in een digitale folder staan
-- en daar niet betrouwbaar uit te lezen zijn. Dat blijft zo: hij levert alleen
-- standaardprijzen, geen aanbiedingen. Het ophaalscript weet dat.
-- -----------------------------------------------------------------------------
update public.winkels set actief = true where id = 5;


-- -----------------------------------------------------------------------------
-- Toegangsregels — iedereen die is ingelogd mag lezen, niemand mag wijzigen.
-- Het ophaalscript gebruikt de servicesleutel en valt hier buiten.
-- -----------------------------------------------------------------------------
alter table public.standaardprijzen enable row level security;

drop policy if exists "standaardprijzen lezen" on public.standaardprijzen;
create policy "standaardprijzen lezen" on public.standaardprijzen
    for select to authenticated using (true);
