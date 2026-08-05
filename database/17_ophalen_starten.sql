-- =============================================================================
--  Dealbot — het ophalen met één knop starten vanaf de beheerpagina
--
--  Versie      : 1.0
--  Reden       : Wie het ophalen tussendoor wilde laten draaien, moest naar
--                GitHub, daar de juiste werkstroom zoeken en twee keer klikken.
--                Dat is geen knop maar een omweg. Het echte werk (winkels
--                aflopen, folders laten voorlezen) duurt minuten en blijft op
--                GitHub draaien; alleen het startsein verhuist naar de site.
--                De database is daarbij de tussenpersoon: die kent de sleutel
--                van GitHub, de website niet. Zo staat er geen sleutel op een
--                openbare pagina. Meteen goed geregeld: de folder van Vomar is
--                gericht opnieuw te laten voorlezen, ook als hij al gelezen is.
--  Datum       : 05-08-2026 23:55
--
--  Onderdelen:
--    pg_net                    - de database mag zelf een webadres aanroepen
--    ophaal_opdrachten         - wat er met de hand is gestart, en hoe dat ging
--    beheer_start_ophalen()    - geeft GitHub het startsein
--    beheer_ophaalopdrachten() - de laatste startseinen, met hun uitkomst
--
--  Volgorde: na 16_kenmerken.sql. Opnieuw uit te voeren zonder schade.
--
--  LET OP — eenmalig, vóór de knop werkt: de sleutel van GitHub moet in de
--  kluis van de database. Dat is een aparte, versleutelde bewaarplaats; hij is
--  daarna nergens meer af te lezen, ook niet in dit bestand. Zie stap 2.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Stap 1 — de database mag zelf naar buiten bellen.
--
-- Standaard kan de database alleen antwoorden op vragen die binnenkomen. Deze
-- uitbreiding laat hem ook zélf een webadres aanroepen, en dat is precies wat
-- het startsein is: één berichtje naar GitHub. Hij doet dat op de achtergrond
-- en wacht er niet op, zodat de knop op de site meteen reageert.
-- -----------------------------------------------------------------------------
create extension if not exists pg_net;


-- -----------------------------------------------------------------------------
-- Stap 2 — de sleutel van GitHub, in de kluis.
--
-- Eenmalig met de hand te doen, want een sleutel hoort in geen enkel bestand
-- te staan dat op GitHub belandt. Maak op GitHub een fijnmazige toegangssleutel
-- (Settings → Developer settings → Personal access tokens → Fine-grained) die
-- alléén bij de repo dealbot mag, met recht "Actions: Read and write". Zet hem
-- daarna in de kluis door onderstaande regel één keer uit te voeren met de
-- echte sleutel erin:
--
--   select vault.create_secret('github_pat_...', 'github_sleutel',
--                              'Startsein voor het ophalen vanaf de beheerpagina');
--
-- Verloopt de sleutel, dan vervang je hem zo:
--
--   select vault.update_secret(
--       (select id from vault.secrets where name = 'github_sleutel'),
--       'github_pat_de_nieuwe');
--
-- Zonder deze stap doet de knop niets en zegt de beheerpagina dat ook.
-- -----------------------------------------------------------------------------


-- -----------------------------------------------------------------------------
-- Stap 3 — het logboek van de startseinen.
--
-- Los van het gewone logboek (scan_logs): daarin staat hoe het ophalen zélf is
-- gegaan, hier staat alleen of het startsein is aangekomen. Dat verschil telt
-- bij het zoeken naar een storing: een sleutel die verlopen is, ziet er anders
-- uit dan een winkel die dicht zit.
--
-- Er staan geen toegangsregels op, en dat is met opzet: zonder regel mag
-- niemand er rechtstreeks bij. Alles loopt via de twee functies hieronder, en
-- die vragen eerst of je de beheerder bent.
-- -----------------------------------------------------------------------------
create table if not exists public.ophaal_opdrachten (
    id            bigint generated always as identity primary key,
    wat           text        not null,
    opnieuw       boolean     not null default false,
    gestart_op    timestamptz not null default now(),
    door          uuid        references auth.users(id) on delete set null,
    verzoek_id    bigint,
    beantwoord_op timestamptz,
    status_code   integer,
    melding       text
);

alter table public.ophaal_opdrachten enable row level security;

comment on table public.ophaal_opdrachten is
    'Wat er met de hand vanaf de beheerpagina is gestart, en of GitHub het '
    'startsein heeft aangenomen. Alleen via de beheerfuncties te benaderen.';


-- -----------------------------------------------------------------------------
-- Stap 4 — het startsein.
--
-- Drie dingen zitten hier bewust in:
--   * alleen de beheerder mag het;
--   * niet vaker dan eens per vijf minuten, want een tweede ronde bovenop een
--     lopende levert niets op en het voorlezen van een folder kost tientallen
--     AI-vragen per keer;
--   * de sleutel komt uit de kluis en gaat nergens anders heen dan naar GitHub.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_start_ophalen(
    wat     text    default 'alles',
    opnieuw boolean default false
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    sleutel text;
    vorige  timestamptz;
    verzoek bigint;
begin
    if not public.is_beheerder() then
        raise exception 'Alleen de beheerder mag dit doen.' using errcode = '42501';
    end if;

    if wat not in ('alles', 'winkels', 'folder') then
        raise exception 'Dit is geen bestaande opdracht: %', wat;
    end if;

    select max(o.gestart_op) into vorige from public.ophaal_opdrachten o;
    if vorige is not null and vorige > now() - interval '5 minutes' then
        raise exception 'Er is net al een ronde gestart. Wacht een paar minuten '
                        'en ververs daarna het overzicht.';
    end if;

    select decrypted_secret into sleutel
      from vault.decrypted_secrets
     where name = 'github_sleutel';

    if sleutel is null or btrim(sleutel) = '' then
        raise exception 'De sleutel voor GitHub staat nog niet in de kluis van de '
                        'database; het ophalen kan daarom niet gestart worden.';
    end if;

    -- De werkstroom staat in de repo Bartloe/dealbot op de tak main. Verhuist
    -- de code ooit, dan is dit het enige regeltje dat mee moet.
    select net.http_post(
        url := 'https://api.github.com/repos/Bartloe/dealbot/actions/workflows/'
               || 'aanbiedingen-ophalen.yml/dispatches',
        body := jsonb_build_object(
            'ref', 'main',
            'inputs', jsonb_build_object(
                'wat', wat,
                -- GitHub verwacht deze keuzes als tekst, niet als ja/nee.
                'opnieuw', case when opnieuw then 'true' else 'false' end
            )
        ),
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || sleutel,
            'Accept', 'application/vnd.github+json',
            'X-GitHub-Api-Version', '2022-11-28',
            'User-Agent', 'dealbot-beheerpagina',
            'Content-Type', 'application/json'
        ),
        timeout_milliseconds := 10000
    ) into verzoek;

    insert into public.ophaal_opdrachten (wat, opnieuw, door, verzoek_id)
    values (wat, opnieuw, auth.uid(), verzoek);
end;
$$;

grant execute on function public.beheer_start_ophalen(text, boolean) to authenticated;

comment on function public.beheer_start_ophalen(text, boolean) is
    'Geeft GitHub het sein om het ophalen te starten: alles, alleen de winkels '
    'of alleen de folder. Alleen voor de beheerder, hooguit eens per vijf minuten.';


-- -----------------------------------------------------------------------------
-- Stap 5 — hoe het startsein is aangekomen.
--
-- Het antwoord van GitHub komt een tel later binnen en wordt na een paar uur
-- weer opgeruimd. Daarom wordt het hier één keer overgeschreven naar het eigen
-- logboek: zo blijft ook morgen nog te zien dat de sleutel geweigerd werd.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_ophaalopdrachten()
returns table (
    gestart_op timestamptz,
    wat        text,
    opnieuw    boolean,
    uitkomst   text,
    melding    text
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not public.is_beheerder() then
        raise exception 'Alleen de beheerder mag dit opvragen.' using errcode = '42501';
    end if;

    update public.ophaal_opdrachten o
       set beantwoord_op = now(),
           status_code   = r.status_code,
           melding       = coalesce(
               r.error_msg,
               case when r.status_code = 204 then null else left(r.content, 300) end
           )
      from net._http_response r
     where r.id = o.verzoek_id
       and o.beantwoord_op is null;

    return query
    select o.gestart_op,
           o.wat,
           o.opnieuw,
           case
               when o.status_code = 204 then 'gelukt'
               when o.beantwoord_op is not null then 'mislukt'
               when o.gestart_op > now() - interval '2 minutes' then 'bezig'
               else 'onbekend'
           end,
           case
               when o.status_code = 204 then 'GitHub heeft het startsein aangenomen.'
               when o.status_code = 401 then 'GitHub weigert de sleutel: hij is verlopen of ongeldig.'
               when o.status_code = 403 then 'De sleutel mag het ophalen niet starten; '
                                            'controleer het recht "Actions: Read and write".'
               when o.status_code = 404 then 'GitHub kent deze werkstroom niet, of de sleutel mag er niet bij.'
               when o.status_code = 422 then 'GitHub kan hier niet starten; staat de werkstroom op de tak main?'
               when o.status_code is not null then 'GitHub antwoordde met code '
                                                   || o.status_code || '.'
               when o.beantwoord_op is not null then coalesce(o.melding, 'Geen contact met GitHub gekregen.')
               when o.gestart_op > now() - interval '2 minutes' then 'Het startsein is onderweg.'
               else 'Het antwoord van GitHub is niet bewaard gebleven.'
           end
      from public.ophaal_opdrachten o
     order by o.gestart_op desc
     limit 5;
end;
$$;

grant execute on function public.beheer_ophaalopdrachten() to authenticated;

comment on function public.beheer_ophaalopdrachten() is
    'De laatste keren dat het ophalen met de hand is gestart, met de uitkomst '
    'van het startsein. Alleen voor de beheerder.';
