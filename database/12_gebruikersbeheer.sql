-- =============================================================================
--  Dealbot — gebruikersbeheer: wie is er, en wie mag er niet meer in
--
--  Versie      : 1.0
--  Reden       : Aanmelden staat vrij open: iedereen met een e-mailadres kan
--                een account maken. Tot nu toe was er geen manier om te zien
--                wie dat gedaan heeft, en al helemaal niet om iemand er weer
--                uit te zetten. De beheerder krijgt daarom een overzicht van de
--                accounts, en twee manieren om in te grijpen: een account op
--                slot zetten (terug te draaien) of het helemaal verwijderen.
--                Daarnaast een lijst geweerde e-mailadressen, zodat opnieuw
--                aanmelden met hetzelfde adres niet lukt.
--  Datum       : 04-08-2026 23:10
--
--  Onderdelen:
--    profielen.geblokkeerd     - het account staat op slot
--    mag_meedoen()             - ingelogd én niet geblokkeerd
--    mijn_toegang()            - wat de website van mij moet weten, in één vraag
--    toegangsregels            - alle leesrechten lopen nu via mag_meedoen()
--    geweerde_adressen         - adressen die geen account meer mogen maken
--    beheer_gebruikers()       - het overzicht van accounts
--    beheer_blokkeer()         - een account op slot of weer open
--    beheer_verwijder_gebruiker() - een account met alles erin en eraan wissen
--
--  Volgorde: na 11_beheer.sql. Opnieuw uit te voeren zonder schade.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Stap 1 — het slot op een account.
--
-- Bewust een eigen vlaggetje en niet het slot van Supabase zelf: dat laatste
-- zit in de keuken van de leverancier en kan bij een verhuizing of update anders
-- gaan werken. Een geblokkeerde gebruiker kan hierdoor nog wél inloggen, maar
-- krijgt niets meer te zien — de website gooit hem er meteen weer uit en de
-- database geeft hem geen enkele regel meer.
-- -----------------------------------------------------------------------------
alter table public.profielen
    add column if not exists geblokkeerd boolean not null default false;

comment on column public.profielen.geblokkeerd is
    'Het account staat op slot: inloggen levert niets meer op. Terug te draaien '
    'door de beheerder; alleen via de beheerpagina te wijzigen.';

-- Net als het beheerdersvlaggetje mag niemand dit van zichzelf omzetten. Het
-- wijzigen vanaf de website blijft beperkt tot de weergavenaam.
revoke update on public.profielen from authenticated;
grant update (weergavenaam) on public.profielen to authenticated;


-- -----------------------------------------------------------------------------
-- Stap 2 — de vraag "mag ik hier zijn?".
--
-- Eén plek waar het antwoord vandaan komt, zodat een blokkade overal tegelijk
-- werkt en niet per ongeluk ergens vergeten wordt.
-- -----------------------------------------------------------------------------
create or replace function public.mag_meedoen()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.profielen p
         where p.id = auth.uid()
           and not p.geblokkeerd
    );
$$;

grant execute on function public.mag_meedoen() to authenticated, service_role;

comment on function public.mag_meedoen() is
    'Geeft terug of de ingelogde gebruiker mee mag doen: ingelogd en niet '
    'geblokkeerd. Alle leesrechten hangen hieraan.';


-- Wat de website na het inloggen van de database moet weten, in één vraag: mag
-- ik hier zijn, en hoort de beheerknop in de balk? Twee losse vragen zouden
-- twee keer verkeer opleveren bij het openen van elke pagina.
create or replace function public.mijn_toegang()
returns table (beheerder boolean, geblokkeerd boolean)
language sql
stable
security definer
set search_path = public
as $$
    select coalesce(p.beheerder, false),
           coalesce(p.geblokkeerd, false)
      from public.profielen p
     where p.id = auth.uid();
$$;

grant execute on function public.mijn_toegang() to authenticated, service_role;

comment on function public.mijn_toegang() is
    'Voor de website: ben ik beheerder, en sta ik op slot? Geeft niets terug '
    'als er niemand is ingelogd.';


-- -----------------------------------------------------------------------------
-- Stap 3 — alle leesrechten achter datzelfde slot.
--
-- Voorheen stond er "iedereen die is ingelogd mag lezen". Dat wordt nu
-- "iedereen die is ingelogd en niet geblokkeerd is". Zonder deze stap zou een
-- geblokkeerde gebruiker die de website omzeilt gewoon alles kunnen ophalen.
--
-- Zijn eigen profiel blijft hij zien: daar hangt de melding aan dat zijn account
-- op slot staat.
-- -----------------------------------------------------------------------------
drop policy if exists "aanbiedingen lezen" on public.aanbiedingen;
create policy "aanbiedingen lezen" on public.aanbiedingen
    for select to authenticated using (public.mag_meedoen());

drop policy if exists "winkels lezen" on public.winkels;
create policy "winkels lezen" on public.winkels
    for select to authenticated using (public.mag_meedoen());

drop policy if exists "scan logs lezen" on public.scan_logs;
create policy "scan logs lezen" on public.scan_logs
    for select to authenticated using (public.mag_meedoen());

drop policy if exists "standaardprijzen lezen" on public.standaardprijzen;
create policy "standaardprijzen lezen" on public.standaardprijzen
    for select to authenticated using (public.mag_meedoen());

drop policy if exists "eigen groepen lezen" on public.eigen_groepen;
create policy "eigen groepen lezen" on public.eigen_groepen
    for select to authenticated using (public.mag_meedoen());

drop policy if exists "koppelingen lezen" on public.groep_koppelingen;
create policy "koppelingen lezen" on public.groep_koppelingen
    for select to authenticated using (public.mag_meedoen());

-- Zoekvragen blijven van de gebruiker zelf, maar een geblokkeerd account komt
-- er niet meer bij — ook niet om ze te wissen.
drop policy if exists "eigen zoekvragen lezen" on public.zoekvragen;
create policy "eigen zoekvragen lezen" on public.zoekvragen
    for select to authenticated using (gebruiker_id = auth.uid() and public.mag_meedoen());

drop policy if exists "eigen zoekvragen toevoegen" on public.zoekvragen;
create policy "eigen zoekvragen toevoegen" on public.zoekvragen
    for insert to authenticated with check (gebruiker_id = auth.uid() and public.mag_meedoen());

drop policy if exists "eigen zoekvragen bijwerken" on public.zoekvragen;
create policy "eigen zoekvragen bijwerken" on public.zoekvragen
    for update to authenticated
    using (gebruiker_id = auth.uid() and public.mag_meedoen())
    with check (gebruiker_id = auth.uid() and public.mag_meedoen());

drop policy if exists "eigen zoekvragen verwijderen" on public.zoekvragen;
create policy "eigen zoekvragen verwijderen" on public.zoekvragen
    for delete to authenticated using (gebruiker_id = auth.uid() and public.mag_meedoen());


-- De keuzelijst van het profielscherm draait met de rechten van de eigenaar en
-- valt daardoor buiten de regels hierboven; die krijgt zijn eigen slot. Verder
-- ongewijzigd ten opzichte van 10_indeling_in_profiel.sql.
create or replace function public.eigen_indeling()
returns table (
    hoofdgroep text,
    subgroep   text,
    volgorde   integer,
    aantal     bigint
)
language plpgsql
stable
security definer
set search_path = public
as $$
begin
    if not public.mag_meedoen() then
        raise exception 'Je account is geblokkeerd.' using errcode = '42501';
    end if;

    return query
    with telling as (
        select a.hoofdgroep as hoofd, a.subgroep as sub, count(*)::bigint as aantal
          from public.aanbiedingen a
         where a.hoofdgroep is not null
         group by a.hoofdgroep, a.subgroep
    )
    select g.hoofdgroep,
           null::text,
           0,
           coalesce((select sum(t.aantal) from telling t where t.hoofd = g.hoofdgroep), 0)
      from (select distinct eg.hoofdgroep from public.eigen_groepen eg) g

    union all

    select g.hoofdgroep,
           g.subgroep,
           g.volgorde,
           coalesce((select t.aantal from telling t
                      where t.hoofd = g.hoofdgroep and t.sub = g.subgroep), 0)
      from public.eigen_groepen g

    order by 1, 3, 2;
end;
$$;

grant execute on function public.eigen_indeling() to authenticated, service_role;


-- -----------------------------------------------------------------------------
-- Stap 4 — geweerde e-mailadressen.
--
-- Blokkeren houdt een bestaand account tegen; deze lijst houdt tegen dat er met
-- hetzelfde adres een nieuw account bij komt. Bewust op adres en niet op
-- IP-nummer: thuisaansluitingen wisselen van nummer en op mobiel internet delen
-- duizenden mensen er één, dus daarmee raak je vooral de verkeerde.
-- -----------------------------------------------------------------------------
create table if not exists public.geweerde_adressen (
    email          text primary key,
    reden          text,
    toegevoegd_op  timestamptz not null default now()
);

comment on table public.geweerde_adressen is
    'E-mailadressen die geen nieuw account mogen aanmaken. Alleen de beheerder '
    'ziet en beheert deze lijst.';

-- Hoofdletters en spaties mogen nooit het verschil maken tussen wel en niet
-- geweerd; daarom gaat elk adres in dezelfde vorm de lijst in.
create or replace function public.net_adres()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.email := lower(btrim(new.email));
    if new.email = '' then
        raise exception 'Vul een e-mailadres in.';
    end if;
    return new;
end;
$$;

drop trigger if exists trg_net_adres on public.geweerde_adressen;
create trigger trg_net_adres
    before insert or update on public.geweerde_adressen
    for each row execute function public.net_adres();

alter table public.geweerde_adressen enable row level security;

drop policy if exists "geweerde adressen beheren" on public.geweerde_adressen;
create policy "geweerde adressen beheren" on public.geweerde_adressen
    for all to authenticated
    using (public.is_beheerder())
    with check (public.is_beheerder());


-- Bij het aanmelden meteen de deur dichthouden. Deze trigger bestond al om een
-- profiel aan te maken; hij kijkt nu eerst of het adres geweerd is.
create or replace function public.maak_profiel_bij_nieuwe_gebruiker()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if exists (
        select 1 from public.geweerde_adressen g
         where g.email = lower(btrim(coalesce(new.email, '')))
    ) then
        raise exception 'Dit e-mailadres kan geen account aanmaken.';
    end if;

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
-- Stap 5 — het overzicht van accounts.
--
-- Het e-mailadres en het moment van de laatste inlog houdt Supabase bij in zijn
-- eigen, afgeschermde deel van de database. Deze functie is het loket dat die
-- gegevens uitsluitend aan de beheerder doorgeeft.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_gebruikers()
returns table (
    id              uuid,
    weergavenaam    text,
    email           text,
    aangemaakt_op   timestamptz,
    laatst_ingelogd timestamptz,
    bevestigd       boolean,
    geblokkeerd     boolean,
    beheerder       boolean,
    zoekvragen      bigint,
    ben_ikzelf      boolean
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
    select p.id,
           p.weergavenaam,
           u.email::text,
           p.aangemaakt_op,
           u.last_sign_in_at,
           u.email_confirmed_at is not null,
           p.geblokkeerd,
           p.beheerder,
           coalesce((select count(*) from public.zoekvragen z where z.gebruiker_id = p.id), 0),
           p.id = auth.uid()
      from public.profielen p
      join auth.users u on u.id = p.id
     order by u.created_at;
end;
$$;

grant execute on function public.beheer_gebruikers() to authenticated;

comment on function public.beheer_gebruikers() is
    'Alle accounts met naam, e-mailadres, laatste inlog en aantal zoekvragen. '
    'Alleen voor de beheerder.';


-- -----------------------------------------------------------------------------
-- Stap 6 — een account op slot zetten of weer openen.
--
-- De beheerder kan zichzelf niet buitensluiten: met één beheerder zou daarmee
-- niemand er meer in kunnen om het terug te draaien.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_blokkeer(gebruiker uuid, op_slot boolean)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if not public.is_beheerder() then
        raise exception 'Alleen de beheerder mag dit doen.' using errcode = '42501';
    end if;
    if gebruiker = auth.uid() then
        raise exception 'Je kunt je eigen account niet blokkeren.' using errcode = '42501';
    end if;

    update public.profielen set geblokkeerd = op_slot where id = gebruiker;

    if not found then
        raise exception 'Dit account bestaat niet (meer).';
    end if;
end;
$$;

grant execute on function public.beheer_blokkeer(uuid, boolean) to authenticated;

comment on function public.beheer_blokkeer(uuid, boolean) is
    'Zet een account op slot of weer open. Alleen voor de beheerder, en niet '
    'op zichzelf.';


-- -----------------------------------------------------------------------------
-- Stap 7 — een account helemaal verwijderen.
--
-- Onomkeerbaar: het inlogaccount, het profiel en alle zoekvragen gaan weg. Het
-- e-mailadres komt daarmee weer vrij om zich opnieuw aan te melden; wil je dat
-- niet, zet het dan ook op de lijst met geweerde adressen.
-- -----------------------------------------------------------------------------
create or replace function public.beheer_verwijder_gebruiker(gebruiker uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if not public.is_beheerder() then
        raise exception 'Alleen de beheerder mag dit doen.' using errcode = '42501';
    end if;
    if gebruiker = auth.uid() then
        raise exception 'Je kunt je eigen account niet verwijderen.' using errcode = '42501';
    end if;

    -- Profiel en zoekvragen hangen met "on delete cascade" aan het inlogaccount
    -- en verdwijnen dus vanzelf mee.
    delete from auth.users where id = gebruiker;

    if not found then
        raise exception 'Dit account bestaat niet (meer).';
    end if;
end;
$$;

grant execute on function public.beheer_verwijder_gebruiker(uuid) to authenticated;

comment on function public.beheer_verwijder_gebruiker(uuid) is
    'Verwijdert een account met profiel en zoekvragen. Onomkeerbaar. Alleen '
    'voor de beheerder, en niet op zichzelf.';
