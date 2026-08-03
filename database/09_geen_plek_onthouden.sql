-- =============================================================================
--  Dealbot — ook onthouden welke winkelgroepen er níet bij horen
--
--  Versie      : 1.0
--  Reden       : Het vertaalboekje bewaarde alleen de treffers. Elke keer dat
--                het indeelscript draaide, ging dus de hele stapel afgewezen
--                groepsnamen opnieuw langs de AI — 2606 groepen waarvan het
--                antwoord al bekend was. Dat kost tientallen AI-vragen per
--                ronde, en die zijn per dag beperkt.
--
--                Een lege hoofdgroep betekent voortaan: "deze winkelgroep is
--                bekeken en hoort nergens bij onze indeling." Daarmee is één
--                vraag per groepsnaam werkelijk één vraag, voorgoed.
--  Datum       : 03-08-2026 23:40
--
--  Onderdelen:
--    groep_koppelingen.hoofdgroep - mag leeg zijn: bekeken, hoort er niet bij
--
--  Volgorde: na 08_eigen_indeling.sql. Opnieuw uit te voeren zonder schade.
-- =============================================================================

alter table public.groep_koppelingen
    alter column hoofdgroep drop not null;

comment on column public.groep_koppelingen.hoofdgroep is
    'Onze hoofdgroep. Leeg betekent niet "onbekend" maar "bekeken en hoort er '
    'niet bij" — zo wordt dezelfde groepsnaam nooit twee keer aan de AI '
    'gevraagd. Een groepsnaam die nog nooit bekeken is, heeft hier helemaal '
    'geen regel staan.';

comment on table public.groep_koppelingen is
    'Vertaalboekje van winkelgroep naar onze eigen indeling, inclusief de '
    'groepen waarvan is vastgesteld dat ze er niet bij horen. Een lege '
    'subgroep bij een gevulde hoofdgroep betekent: de winkelgroep is te grof, '
    'de productnaam moet het aanvullen.';
