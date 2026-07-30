-- =============================================================================
--  Dealbot — herindeling van de zoekvelden
--
--  Versie      : 1.0
--  Reden       : "Variant" bleek in de praktijk de productgroep van de winkel te
--                bevatten, en vrije tekst zocht daar ook in. Daardoor kwam een
--                krat Amstel boven bij de zoekvraag "koffie": bij Dirk heet de
--                groep "Dranken, sap, koffie & thee". Vanaf nu zijn Merk,
--                Productgroep en Vrije tekst drie onafhankelijke ingangen.
--  Datum       : 31-07-2026 01:12
--
--  Onderdelen:
--    hernoemen        - kolom "variant" heet voortaan "productgroep"
--    zoektekst        - zoekt nog uitsluitend in merk en productnaam
--    oude zoekvragen  - een oude variant die geen echte groep is, verhuist
--                       naar vrije tekst in plaats van te verdwijnen
--
--  Volgorde: eerst dit script uitvoeren, daarna 02_matching.sql opnieuw. Dat
--  tweede script gebruikt de nieuwe veldnamen en werkt pas als ze bestaan.
--
--  Dit script is bedoeld voor een database die al draait en is opnieuw uit te
--  voeren zonder schade. Voor een lege database volstaat 01_schema.sql.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Stap 1 — de zoektekst tijdelijk weghalen.
--
-- Dit is een berekende kolom die de productgroep meenam; die berekening moet
-- veranderen en dat kan alleen door de kolom opnieuw op te bouwen. De inhoud
-- gaat niet verloren: hij wordt afgeleid uit velden die blijven staan.
-- -----------------------------------------------------------------------------
alter table public.aanbiedingen drop column if exists zoektekst;


-- -----------------------------------------------------------------------------
-- Stap 2 — het veld bij zijn echte naam noemen.
-- -----------------------------------------------------------------------------
do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'aanbiedingen'
          and column_name = 'variant'
    ) then
        alter table public.aanbiedingen rename column variant to productgroep;
    end if;

    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'zoekvragen'
          and column_name = 'variant'
    ) then
        alter table public.zoekvragen rename column variant to productgroep;
    end if;
end
$$;


-- -----------------------------------------------------------------------------
-- Stap 3 — de zoektekst opnieuw opbouwen, nu zónder de productgroep.
--
-- Hier zit de kern van de oplossing: vrije tekst kijkt voortaan alleen naar het
-- merk en de productnaam. De productgroep heeft zijn eigen ingang gekregen.
-- -----------------------------------------------------------------------------
alter table public.aanbiedingen
    add column zoektekst text generated always as (
        lower(coalesce(merk, '') || ' ' || coalesce(product_naam, ''))
    ) stored;

create index if not exists idx_aanbiedingen_zoektekst
    on public.aanbiedingen using gin (zoektekst gin_trgm_ops);

create index if not exists idx_aanbiedingen_productgroep
    on public.aanbiedingen (winkel_id, productgroep);

comment on column public.aanbiedingen.zoektekst is
    'Merk en productnaam in kleine letters; waar de vrije tekst op zoekt. De '
    'productgroep zit hier bewust niet in: die heeft een eigen zoekveld.';


-- -----------------------------------------------------------------------------
-- Stap 4 — de regel dat een zoekvraag niet leeg mag zijn, op de nieuwe naam.
-- -----------------------------------------------------------------------------
alter table public.zoekvragen drop constraint if exists zoekvraag_niet_leeg;
alter table public.zoekvragen add constraint zoekvraag_niet_leeg check (
    coalesce(nullif(btrim(merk),         ''), '') <> '' or
    coalesce(nullif(btrim(productgroep), ''), '') <> '' or
    coalesce(nullif(btrim(vrije_tekst),  ''), '') <> ''
);


-- -----------------------------------------------------------------------------
-- Stap 5 — bestaande zoekvragen goedzetten.
--
-- In het oude scherm typten mensen bij "Variant" een woord als "oro". Dat is
-- geen productgroep en zou vanaf nu nergens meer op matchen. Zulke waarden
-- verhuizen daarom naar vrije tekst; stond daar al iets, dan blijft dat staan
-- en vervalt de oude waarde (anders zou de zoekvraag strenger worden dan de
-- gebruiker ooit bedoeld heeft).
-- -----------------------------------------------------------------------------
update public.zoekvragen z
   set vrije_tekst  = coalesce(nullif(btrim(z.vrije_tekst), ''), z.productgroep),
       productgroep = null
 where nullif(btrim(z.productgroep), '') is not null
   and not exists (
       select 1 from public.aanbiedingen a
        where lower(a.productgroep) = lower(btrim(z.productgroep))
   );
