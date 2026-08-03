-- =============================================================================
--  Dealbot — Lidl erbij als vijfde winkel
--
--  Versie      : 1.0
--  Reden       : Lidl publiceert zijn weekaanbiedingen mét prijs op zijn eigen
--                aanbiedingenpagina. Daarmee is hij een gewone aanbiedingenbron,
--                net als Albert Heijn, Jumbo en Dirk. Alleen het winkelnummer
--                moet nog bestaan; de rest regelt het ophaalscript.
--  Datum       : 03-08-2026 13:15
--
--  Onderdelen:
--    winkel 6 (Lidl)   - toevoegen en meteen aanzetten
--
--  Dit script is opnieuw uit te voeren zonder schade.
--  Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================

insert into public.winkels (id, code, naam, actief) values
    (6, 'lidl', 'Lidl', true)
on conflict (id) do update
    set code   = excluded.code,
        naam   = excluded.naam,
        actief = excluded.actief;
