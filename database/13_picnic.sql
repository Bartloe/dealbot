-- =============================================================================
--  Dealbot — Picnic erbij als zesde werkende winkel
--
--  Versie      : 1.0
--  Reden       : Picnic heeft geen webwinkel en geen folder: zijn assortiment en
--                zijn wekelijkse acties zitten alleen in zijn app. Die ingang
--                staat pas open na inloggen, dus Dealbot logt elke ochtend in met
--                een eigen Picnic-account. Alleen het winkelnummer moet hier
--                bestaan; de rest regelt het ophaalscript.
--  Datum       : 05-08-2026
--
--  Onderdelen:
--    winkel 7 (Picnic)  - toevoegen en meteen aanzetten
--
--  Dit script is opnieuw uit te voeren zonder schade.
--  Draaien in de SQL-editor van Supabase; er is geen psql op de laptop.
-- =============================================================================

insert into public.winkels (id, code, naam, actief) values
    (7, 'picnic', 'Picnic', true)
on conflict (id) do update
    set code   = excluded.code,
        naam   = excluded.naam,
        actief = excluded.actief;
