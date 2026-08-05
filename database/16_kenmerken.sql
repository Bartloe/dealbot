-- =============================================================================
--  Dealbot — kenmerken: een derde laag onder de lade
--
--  Versie      : 1.0
--  Reden       : Onze indeling heeft één lade Huishouden / Toiletpapier, met
--                het droge en het vochtige door elkaar. Wie alleen het vochtige
--                wil volgen kon dat nergens kiezen. Datzelfde speelt bij koffie
--                (bonen, pads, capsules), melk (vol, halfvol, lactosevrij) en
--                bij tientallen andere laden.
--
--                De laden nog fijner maken lost dat niet op: dan groeit de
--                indeling eindeloos en moet iemand hem met de hand blijven
--                bijhouden. Maar de winkels hebben die fijne indeling al
--                gemaakt — Vomar zegt "Toiletpapier Vochtig", Albert Heijn
--                "Toiletpapier - vochtig". Dat detail gooiden we weg zodra de
--                winkelgroep onder onze lade werd gehangen.
--
--                Vanaf nu wordt het bewaard als "kenmerk": één woord in ónze
--                taal, dat bij alle winkels hetzelfde is. Het is een derde,
--                optionele laag: afdeling > lade > kenmerk. Wie geen kenmerk
--                kiest, volgt de hele lade zoals voorheen.
--  Datum       : 05-08-2026 14:35
--
--  Onderdelen:
--    groep_koppelingen  - kenmerk erbij: wat het vertaalboekje overhoudt
--    aanbiedingen       - kenmerk erbij, naast hoofdgroep en subgroep
--    standaardprijzen   - kenmerk erbij, langs dezelfde weg
--    zoekvragen         - kenmerk erbij; alleen zinvol binnen een lade
--    mijn_aanbiedingen()- matcht ook op het kenmerk
--    kenmerken()        - de keuzelijst: welke kenmerken zitten in welke lade
--
--  Volgorde: na 15_standaardprijzen_indeling.sql. Opnieuw uit te voeren zonder
--  schade. Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Stap 1 — het vertaalboekje houdt het kenmerk over.
--
-- Het boekje vertaalde "Toiletpapier Vochtig" naar Huishouden / Toiletpapier en
-- liet het woord "vochtig" vallen. Dat woord komt hier terecht. Omdat dezelfde
-- vertaler ook de namen van de andere ketens langskrijgt, komen "Toiletpapier -
-- vochtig" en "vochtig toiletpapier" op datzelfde ene kenmerk uit.
--
-- Leeg is het normale geval: een winkelgroep die precies één lade dekt heeft
-- niets te verbijzonderen.
-- -----------------------------------------------------------------------------
alter table public.groep_koppelingen
    add column if not exists kenmerk text;

comment on column public.groep_koppelingen.kenmerk is
    'Wat deze winkelgroep binnen de lade verbijzondert, in onze eigen woorden '
    'en in kleine letters ("vochtig", "pads"). Leeg = de groep dekt de lade.';


-- -----------------------------------------------------------------------------
-- Stap 2 — het kenmerk bij het product zelf.
--
-- Op beide tabellen, want ze hangen onder dezelfde indeling en de website
-- gebruikt ze allebei: de aanbiedingen voor je profiel, de standaardprijzen om
-- te vergelijken.
--
-- Het veld mag leeg zijn en is dat meestal ook. Leeg betekent hier "geen
-- verbijzondering bekend" en nadrukkelijk niet "hoort er niet bij": het product
-- ligt gewoon in de lade.
-- -----------------------------------------------------------------------------
alter table public.aanbiedingen
    add column if not exists kenmerk text;

alter table public.standaardprijzen
    add column if not exists kenmerk text;

-- Zoeken gebeurt altijd binnen een lade, dus het kenmerk staat achteraan in de
-- sleutel. Zonder deze index moet de telling voor de keuzelijst over de hele
-- tabel.
create index if not exists idx_aanbiedingen_kenmerk
    on public.aanbiedingen (hoofdgroep, subgroep, kenmerk);

create index if not exists idx_standaardprijzen_kenmerk
    on public.standaardprijzen (hoofdgroep, subgroep, kenmerk);

comment on column public.aanbiedingen.kenmerk is
    'Verbijzondering binnen de lade, in onze eigen woorden. Leeg = niet bekend.';
comment on column public.standaardprijzen.kenmerk is
    'Verbijzondering binnen de lade, in onze eigen woorden. Leeg = niet bekend.';


-- -----------------------------------------------------------------------------
-- Stap 3 — de zoekvraag mag op een kenmerk staan.
--
-- Alleen binnen een lade. Een kenmerk zonder lade is betekenisloos: "vochtig"
-- bestaat bij het toiletpapier én bij de doekjes, en "capsules" bij de koffie én
-- bij het wasmiddel. Zonder de lade erbij zou zo'n zoekvraag halve supermarkten
-- binnenhalen.
--
-- Bestaande zoekvragen blijven gewoon staan: geen kenmerk betekent de hele lade,
-- precies wat ze nu al doen.
-- -----------------------------------------------------------------------------
alter table public.zoekvragen
    add column if not exists kenmerk text;

alter table public.zoekvragen drop constraint if exists zoekvraag_kenmerk_hoort_bij_subgroep;
alter table public.zoekvragen add constraint zoekvraag_kenmerk_hoort_bij_subgroep check (
    nullif(btrim(kenmerk), '') is null
    or nullif(btrim(subgroep), '') is not null
);

comment on column public.zoekvragen.kenmerk is
    'Verbijzondering binnen de lade. Leeg = de hele lade, zoals voorheen.';


-- -----------------------------------------------------------------------------
-- Stap 4 — het matchen.
--
-- Eén regel erbij, in dezelfde vorm als de andere: is het veld leeg, dan stelt
-- het geen eis. Zo blijft een zoekvraag op de hele lade doen wat hij deed.
-- -----------------------------------------------------------------------------
drop function if exists public.mijn_aanbiedingen();

create function public.mijn_aanbiedingen()
returns table (
    id                bigint,
    winkel            text,
    product_naam      text,
    merk              text,
    productgroep      text,
    hoofdgroep        text,
    subgroep          text,
    kenmerk           text,
    actie_tekst       text,
    prijs             numeric,
    normale_prijs     numeric,
    inhoud_waarde     numeric,
    inhoud_eenheid    text,
    prijs_per_eenheid numeric,
    eenheid_norm      text,
    product_sleutel   text,
    geldig_van        date,
    geldig_tot        date,
    product_url       text,
    afbeelding_url    text
)
language sql
stable
security invoker
set search_path = public
as $$
    select
        a.id,
        w.naam,
        a.product_naam,
        a.merk,
        a.productgroep,
        a.hoofdgroep,
        a.subgroep,
        a.kenmerk,
        a.actie_tekst,
        a.prijs,
        a.normale_prijs,
        a.inhoud_waarde,
        a.inhoud_eenheid,
        a.prijs_per_eenheid,
        a.eenheid_norm,
        a.product_sleutel,
        a.geldig_van,
        a.geldig_tot,
        a.product_url,
        a.afbeelding_url
    from public.aanbiedingen a
    join public.winkels w on w.id = a.winkel_id
    where exists (
        select 1
        from public.zoekvragen z
        where z.gebruiker_id = auth.uid()

          -- Merk: zoeken in het merkveld én in de productnaam, omdat niet elke
          -- winkel het merk apart aanlevert.
          and (
              nullif(btrim(z.merk), '') is null
              or lower(coalesce(a.merk, '') || ' ' || a.product_naam)
                 like '%' || lower(btrim(z.merk)) || '%'
          )

          -- Onze eigen indeling. Precies deze afdeling, en als er een lade bij
          -- gekozen is ook precies die lade. Alleen een afdeling laat dus ook
          -- de aanbiedingen door waarvan de lade onbekend is gebleven.
          and (
              nullif(btrim(z.hoofdgroep), '') is null
              or (
                  a.hoofdgroep = btrim(z.hoofdgroep)
                  and (
                      nullif(btrim(z.subgroep), '') is null
                      or a.subgroep = btrim(z.subgroep)
                  )
              )
          )

          -- Het kenmerk binnen de lade. Een aanbieding zonder kenmerk valt hier
          -- buiten, en dat hoort ook: wie "vochtig" volgt wil niet alsnog het
          -- droge toiletpapier zien waarvan we het niet zeker weten.
          and (
              nullif(btrim(z.kenmerk), '') is null
              or a.kenmerk = btrim(z.kenmerk)
          )

          -- Vrije tekst: alleen in merk en productnaam (dat is wat zoektekst
          -- bevat), nadrukkelijk niet in de groep.
          and (
              nullif(btrim(z.vrije_tekst), '') is null
              or a.zoektekst like '%' || lower(btrim(z.vrije_tekst)) || '%'
          )
    )
    -- Zelfde product bij elkaar, daarbinnen goedkoop naar duur.
    -- Is de kiloprijs onbekend, dan zakt de aanbieding naar onderen.
    order by a.product_sleutel,
             a.prijs_per_eenheid asc nulls last,
             a.prijs             asc nulls last;
$$;

comment on function public.mijn_aanbiedingen() is
    'Aanbiedingen die passen bij de zoekvragen van de ingelogde gebruiker, '
    'gegroepeerd per product en gesorteerd van goedkoop naar duur op kiloprijs. '
    'Aanbiedingen zonder bekende kiloprijs komen onderaan.';


-- -----------------------------------------------------------------------------
-- Stap 5 — de keuzelijst met kenmerken.
--
-- Geeft per lade de kenmerken terug die erin voorkomen, met twee tellingen: wat
-- er nu in de bonus ligt en hoeveel producten het in het gewone schap zijn. Dat
-- tweede is de betrouwbaarste maat — het assortiment verandert nauwelijks,
-- terwijl de bonus elke week anders is. Een kenmerk waar deze week toevallig
-- niets van in de aanbieding is, hoort niet uit de keuzelijst te verdwijnen.
--
-- Een kenmerk moet wel érgens over gaan. Komt het in het hele assortiment bij
-- minder dan twee producten voor, dan is het geen keuze maar ruis en blijft het
-- weg. Dat is het enige filter: welke kenmerken er zijn, bepaalt de data zelf.
-- -----------------------------------------------------------------------------
drop function if exists public.kenmerken();

create function public.kenmerken()
returns table (
    hoofdgroep    text,
    subgroep      text,
    kenmerk       text,
    aantal        bigint,
    aantal_schap  bigint
)
language sql
stable
security definer
set search_path = public
as $$
    with uit_de_bonus as (
        select a.hoofdgroep as hoofd, a.subgroep as sub, a.kenmerk as ken,
               count(*)::bigint as aantal
          from public.aanbiedingen a
         where a.hoofdgroep is not null
           and a.subgroep   is not null
           and a.kenmerk    is not null
         group by a.hoofdgroep, a.subgroep, a.kenmerk
    ),
    uit_het_schap as (
        select s.hoofdgroep as hoofd, s.subgroep as sub, s.kenmerk as ken,
               count(*)::bigint as aantal
          from public.standaardprijzen s
         where s.hoofdgroep is not null
           and s.subgroep   is not null
           and s.kenmerk    is not null
         group by s.hoofdgroep, s.subgroep, s.kenmerk
    ),
    samen as (
        select hoofd, sub, ken from uit_de_bonus
        union
        select hoofd, sub, ken from uit_het_schap
    )
    select s.hoofd,
           s.sub,
           s.ken,
           coalesce(b.aantal, 0),
           coalesce(p.aantal, 0)
      from samen s
      left join uit_de_bonus b on b.hoofd = s.hoofd and b.sub = s.sub and b.ken = s.ken
      left join uit_het_schap p on p.hoofd = s.hoofd and p.sub = s.sub and p.ken = s.ken
     where coalesce(p.aantal, 0) + coalesce(b.aantal, 0) >= 2
     -- Het grootste kenmerk voorop, geteld over bonus én schap samen. Op alleen
     -- de bonus sorteren zou de knopjes elke week van plek laten wisselen.
     order by 1, 2, (coalesce(p.aantal, 0) + coalesce(b.aantal, 0)) desc, 3;
$$;

grant execute on function public.kenmerken() to authenticated, service_role;

comment on function public.kenmerken() is
    'De kenmerken per lade, met het aantal aanbiedingen van deze week en het '
    'aantal producten in het gewone schap. Kenmerken die maar bij één product '
    'voorkomen blijven weg. Voedt de knopjes op het profielscherm.';
