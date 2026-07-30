/**
 * =============================================================================
 *  Dealbot — instellingen van de website
 *
 *  Versie      : 1.0
 *  Reden       : Het adres van de database staat op één plek, zodat het bij een
 *                verhuizing maar op één plaats aangepast hoeft te worden.
 *  Datum       : 30-07-2026 23:07
 *
 *  Onderdelen:
 *    SUPABASE_URL     - het adres van de database
 *    SUPABASE_SLEUTEL - de openbare sleutel; deze mag in de website staan
 * =============================================================================
 */

// Deze sleutel is bewust openbaar. Hij geeft alleen toegang tot wat de
// toegangsregels in de database toestaan: je eigen profiel en je eigen
// zoekvragen. De geheime servicesleutel hoort hier nooit te staan.
export const SUPABASE_URL = 'https://topoilymzwfbpdfagzvh.supabase.co';
export const SUPABASE_SLEUTEL = 'sb_publishable_fDak0sxCbD5OedzgeTqTVQ_OvJ7Yh7Z';
