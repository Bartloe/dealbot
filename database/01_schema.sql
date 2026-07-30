-- =============================================================================
--  Dealbot — database-inrichting (Supabase / PostgreSQL)
--
--  Versie      : 1.1
--  Reden       : Dirk toegevoegd als derde winkel waaruit wordt opgehaald.
--                Vomar staat er alvast bij maar staat uit: die publiceert zijn
--                aanbiedingen alleen als folder, en die is niet uit te lezen.
--  Datum       : 31-07-2026 00:12
--
--  Onderdelen:
--    profielen    - weergavenaam per gebruiker, gekoppeld aan het inlogaccount
--    winkels      - de supermarkten waaruit aanbiedingen worden opgehaald
--    zoekvragen   - wat een gebruiker in de gaten wil houden (merk/variant/tekst)
--    aanbiedingen - de actuele aanbiedingen, inclusief berekende kilo-/literprijs
--    scan_logs    - per ophaalronde het resultaat, om storingen te kunnen zien
--
--  Dit script is opnieuw uit te voeren zonder schade (alles is "if not exists").
-- =============================================================================

create extension if not exists pg_trgm;


-- -----------------------------------------------------------------------------
-- Profielen — het inloggen zelf regelt Supabase; hier staat alleen de naam.
-- -----------------------------------------------------------------------------
create table if not exists public.profielen (
    id             uuid primary key references auth.users (id) on delete cascade,
    weergavenaam   text not null default '',
    aangemaakt_op  timestamptz not null default now()
);

comment on table public.profielen is
    'Weergavenaam per gebruiker. E-mailadres en pincode beheert Supabase zelf.';


-- Bij het aanmelden van een nieuw account meteen een profiel aanmaken, zodat er
-- nooit een gebruiker zonder profiel bestaat.
create or replace function public.maak_profiel_bij_nieuwe_gebruiker()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profielen (id, weergavenaam)
    values (new.id, coalesce(new.raw_user_meta_data ->> 'weergavenaam', ''))
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists trg_nieuwe_gebruiker on auth.users;
create trigger trg_nieuwe_gebruiker
    after insert on auth.users
    for each row execute function public.maak_profiel_bij_nieuwe_gebruiker();


-- -----------------------------------------------------------------------------
-- Winkels — vaste lijst, wordt in fase 2 uitgebreid.
-- -----------------------------------------------------------------------------
create table if not exists public.winkels (
    id      smallint primary key,
    code    text not null unique,
    naam    text not null,
    actief  boolean not null default true
);

insert into public.winkels (id, code, naam, actief) values
    (1, 'ah',        'Albert Heijn', true),
    (2, 'jumbo',     'Jumbo',        true),
    (3, 'nettorama', 'Nettorama',    false),
    (4, 'dirk',      'Dirk',         true),
    (5, 'vomar',     'Vomar',        false)
on conflict (id) do update
    set code = excluded.code,
        naam = excluded.naam;


-- -----------------------------------------------------------------------------
-- Zoekvragen — per gebruiker. Ingevulde velden moeten allemaal kloppen (EN-logica);
-- lege velden tellen niet mee. Hoofdletters worden genegeerd bij het vergelijken.
-- -----------------------------------------------------------------------------
create table if not exists public.zoekvragen (
    id             bigint generated always as identity primary key,
    gebruiker_id   uuid not null references auth.users (id) on delete cascade,
    merk           text,
    variant        text,
    vrije_tekst    text,
    aangemaakt_op  timestamptz not null default now(),

    -- Minimaal één van de drie dimensies moet ingevuld zijn, anders matcht alles.
    constraint zoekvraag_niet_leeg check (
        coalesce(nullif(btrim(merk),        ''), '') <> '' or
        coalesce(nullif(btrim(variant),     ''), '') <> '' or
        coalesce(nullif(btrim(vrije_tekst), ''), '') <> ''
    )
);

create index if not exists idx_zoekvragen_gebruiker
    on public.zoekvragen (gebruiker_id);


-- -----------------------------------------------------------------------------
-- Aanbiedingen — wordt elke ochtend ververst. Er wordt geen historie bewaard.
-- -----------------------------------------------------------------------------
create table if not exists public.aanbiedingen (
    id                bigint generated always as identity primary key,
    winkel_id         smallint not null references public.winkels (id),

    -- Herkenning bij de bron, zodat we een aanbieding kunnen bijwerken in plaats
    -- van dubbel toevoegen binnen dezelfde ophaalronde.
    bron_id           text not null,

    product_naam      text not null,
    merk              text,
    variant           text,
    actie_tekst       text,             -- bijv. "2e halve prijs", "25% korting"

    prijs             numeric(10, 2),   -- actieprijs; leeg bij "1+1 gratis"-achtige acties
    normale_prijs     numeric(10, 2),

    inhoud_waarde     numeric(12, 3),   -- bijv. 500 bij "500 gram"
    inhoud_eenheid    text,             -- 'g', 'kg', 'ml', 'l', 'stuk'
    prijs_per_eenheid numeric(12, 4),   -- omgerekend naar kilo/liter; leeg = onbekend
    eenheid_norm      text,             -- 'kg', 'l' of 'stuk'

    -- Sleutel om hetzelfde product bij verschillende winkels te groeperen.
    -- Zonder EAN-code is dit een benadering op basis van merk + productnaam.
    product_sleutel   text not null,

    geldig_van        date,
    geldig_tot        date,
    product_url       text,
    afbeelding_url    text,
    opgehaald_op      timestamptz not null default now(),

    -- Alles waarop een zoekvraag mag matchen, in kleine letters.
    zoektekst text generated always as (
        lower(
            coalesce(merk, '')         || ' ' ||
            coalesce(product_naam, '') || ' ' ||
            coalesce(variant, '')
        )
    ) stored,

    constraint aanbieding_uniek_per_winkel unique (winkel_id, bron_id)
);

create index if not exists idx_aanbiedingen_zoektekst
    on public.aanbiedingen using gin (zoektekst gin_trgm_ops);

create index if not exists idx_aanbiedingen_merk
    on public.aanbiedingen (lower(merk));

create index if not exists idx_aanbiedingen_sleutel
    on public.aanbiedingen (product_sleutel);

comment on column public.aanbiedingen.prijs_per_eenheid is
    'Prijs per kilo of liter. Leeg als de inhoud niet af te leiden is; die '
    'aanbiedingen horen onderaan de lijst met de melding "kiloprijs onbekend".';


-- -----------------------------------------------------------------------------
-- Scan-logboek — één regel per winkel per ophaalronde, zodat zichtbaar is of
-- het ophalen 's ochtends gelukt is en hoeveel er is binnengekomen.
-- -----------------------------------------------------------------------------
create table if not exists public.scan_logs (
    id            bigint generated always as identity primary key,
    winkel_id     smallint references public.winkels (id),
    gestart_op    timestamptz not null default now(),
    klaar_op      timestamptz,
    status        text not null default 'bezig',   -- 'bezig', 'gelukt', 'mislukt'
    aantal        integer not null default 0,
    melding       text
);

create index if not exists idx_scan_logs_gestart
    on public.scan_logs (gestart_op desc);


-- =============================================================================
--  Toegangsregels — wie mag wat zien en wijzigen.
--
--  Het ophaalscript draait met de geheime servicesleutel en omzeilt deze regels;
--  de website draait met de openbare sleutel en valt er wél onder.
-- =============================================================================

alter table public.profielen    enable row level security;
alter table public.zoekvragen   enable row level security;
alter table public.aanbiedingen enable row level security;
alter table public.winkels      enable row level security;
alter table public.scan_logs    enable row level security;

-- Je eigen profiel: zien en aanpassen.
drop policy if exists "eigen profiel lezen" on public.profielen;
create policy "eigen profiel lezen" on public.profielen
    for select to authenticated using (id = auth.uid());

drop policy if exists "eigen profiel bijwerken" on public.profielen;
create policy "eigen profiel bijwerken" on public.profielen
    for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- Je eigen zoekvragen: zien, toevoegen, aanpassen en verwijderen.
drop policy if exists "eigen zoekvragen lezen" on public.zoekvragen;
create policy "eigen zoekvragen lezen" on public.zoekvragen
    for select to authenticated using (gebruiker_id = auth.uid());

drop policy if exists "eigen zoekvragen toevoegen" on public.zoekvragen;
create policy "eigen zoekvragen toevoegen" on public.zoekvragen
    for insert to authenticated with check (gebruiker_id = auth.uid());

drop policy if exists "eigen zoekvragen bijwerken" on public.zoekvragen;
create policy "eigen zoekvragen bijwerken" on public.zoekvragen
    for update to authenticated using (gebruiker_id = auth.uid()) with check (gebruiker_id = auth.uid());

drop policy if exists "eigen zoekvragen verwijderen" on public.zoekvragen;
create policy "eigen zoekvragen verwijderen" on public.zoekvragen
    for delete to authenticated using (gebruiker_id = auth.uid());

-- Aanbiedingen, winkels en het logboek: iedereen die is ingelogd mag ze lezen,
-- niemand mag ze via de website wijzigen.
drop policy if exists "aanbiedingen lezen" on public.aanbiedingen;
create policy "aanbiedingen lezen" on public.aanbiedingen
    for select to authenticated using (true);

drop policy if exists "winkels lezen" on public.winkels;
create policy "winkels lezen" on public.winkels
    for select to authenticated using (true);

drop policy if exists "scan logs lezen" on public.scan_logs;
create policy "scan logs lezen" on public.scan_logs
    for select to authenticated using (true);
