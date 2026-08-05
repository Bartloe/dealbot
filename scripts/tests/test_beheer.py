"""
===============================================================================
 Dealbot — controle op het gebruikersbeheer

 Versie      : 1.1
 Reden       : Het verwijderen vraagt sinds 05-08-2026 of het e-mailadres ook
               geweerd moet worden, en doet dat in één handeling. Die volgorde —
               eerst weren, dan pas verwijderen — hoort ook bewezen te worden,
               inclusief de belofte eronder: met dat adres komt er geen nieuw
               account meer bij.
 Datum       : 05-08-2026 14:05

 Onderdelen:
   het overzicht van accounts  - beheerder wel, gewone gebruiker niet
   op slot zetten              - geblokkeerde krijgt niets meer, ook buitenom
   de grenzen                  - de beheerder kan zichzelf niet buitensluiten
   geweerde adressen           - aanmelden met zo'n adres mislukt
   een account verwijderen     - account en profiel gaan echt weg
   verwijderen én weren        - in één handeling, en het adres blijft dicht

 Let op: dit draait tegen de echte database en heeft de geheime servicesleutel
 uit .env nodig. Alles wat het aanmaakt eindigt op @dealbot-proef.nl en wordt
 aan het eind opgeruimd; bestaande accounts worden niet aangeraakt.

 Uitvoeren met: python scripts/tests/test_beheer.py
===============================================================================
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
for regel in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in regel and not regel.strip().startswith("#"):
        sleutel, waarde = regel.split("=", 1)
        os.environ.setdefault(sleutel.strip(), waarde.strip())

URL = os.environ["SUPABASE_URL"].rstrip("/")
DIENST = os.environ["SUPABASE_SERVICE_KEY"]

# De openbare sleutel komt uit de website zelf, zodat de proef precies dezelfde
# weg loopt als een gewone bezoeker.
CONFIG = (PROJECT / "assets" / "config.js").read_text(encoding="utf-8")
OPENBAAR = re.search(r"SUPABASE_SLEUTEL\s*=\s*'([^']+)'", CONFIG).group(1)

A_MAIL, A_WACHT = "proef.beheerder@dealbot-proef.nl", "dealbot-pin-1234"
B_MAIL, B_WACHT = "proef.gebruiker@dealbot-proef.nl", "dealbot-pin-5678"
GEWEERD = "proef.geweerd@dealbot-proef.nl"
WEG_EN_GEWEERD = "proef.wegenweg@dealbot-proef.nl"

geslaagd, gezakt = [], []


def roep(pad, methode="GET", body=None, sleutel=DIENST, token=None, extra=None):
    data = json.dumps(body).encode() if body is not None else None
    koppen = {
        "apikey": sleutel,
        "Authorization": f"Bearer {token or sleutel}",
        "Content-Type": "application/json",
    }
    koppen.update(extra or {})
    vraag = urllib.request.Request(f"{URL}{pad}", data=data, method=methode, headers=koppen)
    try:
        with urllib.request.urlopen(vraag, timeout=30) as antwoord:
            tekst = antwoord.read().decode()
            return antwoord.status, (json.loads(tekst) if tekst.strip() else None)
    except urllib.error.HTTPError as fout:
        tekst = fout.read().decode()
        try:
            return fout.code, json.loads(tekst)
        except json.JSONDecodeError:
            return fout.code, tekst


def controle(omschrijving, gelukt, toelichting=""):
    (geslaagd if gelukt else gezakt).append(omschrijving)
    teken = "goed" if gelukt else "FOUT"
    print(f"  [{teken}] {omschrijving}{(' — ' + str(toelichting)) if toelichting else ''}")


def maak_account(email, wachtwoord):
    status, gegevens = roep("/auth/v1/admin/users", "POST",
                            {"email": email, "password": wachtwoord, "email_confirm": True})
    if status not in (200, 201):
        print(f"  kon {email} niet aanmaken: {status} {gegevens}")
        return None
    return gegevens["id"]


def log_in(email, wachtwoord):
    status, gegevens = roep("/auth/v1/token?grant_type=password", "POST",
                            {"email": email, "password": wachtwoord}, sleutel=OPENBAAR)
    if status != 200:
        print(f"  inloggen als {email} mislukt: {status} {gegevens}")
        return None
    return gegevens["access_token"]


def ruim_op(ids):
    for nummer in ids:
        if nummer:
            roep(f"/auth/v1/admin/users/{nummer}", "DELETE")
    for adres in (GEWEERD, WEG_EN_GEWEERD):
        roep(f"/rest/v1/geweerde_adressen?email=eq.{adres}", "DELETE")


print("Wegwerp-accounts klaarzetten")
# Restanten van een eerdere proef eerst weg.
_, bestaand = roep("/auth/v1/admin/users?per_page=100")
oude = [g["id"] for g in (bestaand or {}).get("users", [])
        if (g.get("email") or "").endswith("@dealbot-proef.nl")]
ruim_op(oude)

a_id = maak_account(A_MAIL, A_WACHT)
b_id = maak_account(B_MAIL, B_WACHT)
if not a_id or not b_id:
    sys.exit("Kon de proefaccounts niet aanmaken.")

# A wordt beheerder — dat kan alleen met de geheime sleutel, precies zoals bedoeld.
roep(f"/rest/v1/profielen?id=eq.{a_id}", "PATCH", {"beheerder": True})
a_token = log_in(A_MAIL, A_WACHT)
b_token = log_in(B_MAIL, B_WACHT)
if not a_token or not b_token:
    ruim_op([a_id, b_id])
    sys.exit("Kon niet inloggen met de proefaccounts.")

print("\n1. Het overzicht van accounts")
status, lijst = roep("/rest/v1/rpc/beheer_gebruikers", "POST", {}, sleutel=OPENBAAR, token=a_token)
controle("beheerder ziet het overzicht", status == 200 and isinstance(lijst, list),
         f"{len(lijst) if isinstance(lijst, list) else lijst} accounts")
if isinstance(lijst, list):
    ikzelf = [r for r in lijst if r["ben_ikzelf"]]
    controle("eigen regel is als 'jijzelf' gemarkeerd", len(ikzelf) == 1)
    b_regel = [r for r in lijst if r["id"] == b_id]
    controle("e-mail en inlogmoment komen mee",
             bool(b_regel) and b_regel[0]["email"] == B_MAIL and b_regel[0]["laatst_ingelogd"])

status, _ = roep("/rest/v1/rpc/beheer_gebruikers", "POST", {}, sleutel=OPENBAAR, token=b_token)
controle("gewone gebruiker krijgt het overzicht niet", status == 403)

print("\n2. Een account op slot zetten")
status, aanbod_voor = roep("/rest/v1/aanbiedingen?select=id&limit=1", sleutel=OPENBAAR, token=b_token)
controle("gewone gebruiker ziet aanbiedingen", status == 200 and len(aanbod_voor or []) == 1)

status, melding = roep("/rest/v1/rpc/beheer_blokkeer", "POST",
                       {"gebruiker": b_id, "op_slot": True}, sleutel=OPENBAAR, token=a_token)
controle("beheerder kan blokkeren", status in (200, 204), melding or "")

status, aanbod_na = roep("/rest/v1/aanbiedingen?select=id&limit=1", sleutel=OPENBAAR, token=b_token)
controle("geblokkeerde ziet geen aanbiedingen meer", status == 200 and len(aanbod_na or []) == 0)

status, eigen = roep("/rest/v1/rpc/mijn_toegang", "POST", {}, sleutel=OPENBAAR, token=b_token)
controle("geblokkeerde krijgt dat zelf ook te horen",
         status == 200 and eigen and eigen[0]["geblokkeerd"] is True)

status, _ = roep("/rest/v1/rpc/eigen_indeling", "POST", {}, sleutel=OPENBAAR, token=b_token)
controle("geblokkeerde krijgt ook de keuzelijst niet", status == 403)

status, _ = roep("/rest/v1/rpc/beheer_blokkeer", "POST",
                 {"gebruiker": b_id, "op_slot": False}, sleutel=OPENBAAR, token=a_token)
status, aanbod_terug = roep("/rest/v1/aanbiedingen?select=id&limit=1", sleutel=OPENBAAR, token=b_token)
controle("weer openzetten herstelt het", status == 200 and len(aanbod_terug or []) == 1)

print("\n3. De grenzen")
status, melding = roep("/rest/v1/rpc/beheer_blokkeer", "POST",
                       {"gebruiker": a_id, "op_slot": True}, sleutel=OPENBAAR, token=a_token)
controle("beheerder kan zichzelf niet blokkeren", status == 403,
         (melding or {}).get("message") if isinstance(melding, dict) else melding)

status, melding = roep("/rest/v1/rpc/beheer_verwijder_gebruiker", "POST",
                       {"gebruiker": a_id}, sleutel=OPENBAAR, token=a_token)
controle("beheerder kan zichzelf niet verwijderen", status == 403,
         (melding or {}).get("message") if isinstance(melding, dict) else melding)

status, _ = roep("/rest/v1/rpc/beheer_blokkeer", "POST",
                 {"gebruiker": a_id, "op_slot": True}, sleutel=OPENBAAR, token=b_token)
controle("gewone gebruiker kan niemand blokkeren", status == 403)

print("\n4. Geweerde adressen")
status, _ = roep("/rest/v1/geweerde_adressen", "POST",
                 {"email": "  " + GEWEERD.upper() + " ", "reden": "proef"},
                 sleutel=OPENBAAR, token=a_token)
controle("beheerder kan een adres weren", status in (200, 201))

status, lijst = roep("/rest/v1/geweerde_adressen?select=email,reden", sleutel=OPENBAAR, token=a_token)
controle("adres staat er in kleine letters zonder spaties in",
         status == 200 and any(r["email"] == GEWEERD for r in (lijst or [])))

status, lijst_b = roep("/rest/v1/geweerde_adressen?select=email", sleutel=OPENBAAR, token=b_token)
controle("gewone gebruiker ziet de lijst niet", status == 200 and len(lijst_b or []) == 0)

status, melding = roep("/auth/v1/signup", "POST",
                       {"email": GEWEERD, "password": "dealbot-pin-9999"}, sleutel=OPENBAAR)
controle("aanmelden met een geweerd adres mislukt", status >= 400,
         (melding or {}).get("msg") or (melding or {}).get("message") if isinstance(melding, dict) else melding)

status, melding = roep("/auth/v1/signup", "POST",
                       {"email": "proef.gewoon@dealbot-proef.nl", "password": "dealbot-pin-9999"},
                       sleutel=OPENBAAR)
controle("aanmelden met een gewoon adres lukt nog wel", status in (200, 201),
         (melding or {}).get("msg") if isinstance(melding, dict) else "")

print("\n5. Een account verwijderen")
status, _ = roep("/rest/v1/rpc/beheer_verwijder_gebruiker", "POST",
                 {"gebruiker": b_id}, sleutel=OPENBAAR, token=a_token)
controle("beheerder kan een account verwijderen", status in (200, 204))

status, gegevens = roep(f"/auth/v1/admin/users/{b_id}")
controle("het inlogaccount is echt weg", status == 404, status)

status, profiel = roep(f"/rest/v1/profielen?id=eq.{b_id}&select=id")
controle("het profiel is meeverdwenen", status == 200 and len(profiel or []) == 0)

print("\n6. Verwijderen en weren in één handeling")
# De knop op de beheerpagina doet dit in deze volgorde: eerst het adres op de
# lijst, dan pas het account weg. Struikelt het weren, dan staat het account er
# nog en kun je het gewoon opnieuw proberen — andersom zou het adres onvindbaar
# zijn geworden.
c_id = maak_account(WEG_EN_GEWEERD, "dealbot-pin-2468")
controle("er staat een account om te verwijderen", bool(c_id))

status, _ = roep("/rest/v1/geweerde_adressen", "POST",
                 {"email": WEG_EN_GEWEERD, "reden": "Account verwijderd vanaf de beheerpagina"},
                 sleutel=OPENBAAR, token=a_token)
controle("eerst gaat het adres op de lijst", status in (200, 201, 204), status)

status, _ = roep("/rest/v1/rpc/beheer_verwijder_gebruiker", "POST",
                 {"gebruiker": c_id}, sleutel=OPENBAAR, token=a_token)
controle("en daarna is het account weg", status in (200, 204), status)

status, gegevens = roep(f"/auth/v1/admin/users/{c_id}")
controle("het inlogaccount bestaat niet meer", status == 404, status)

status, melding = roep("/auth/v1/signup", "POST",
                       {"email": WEG_EN_GEWEERD, "password": "dealbot-pin-1357"},
                       sleutel=OPENBAAR)
controle("hetzelfde adres kan zich niet opnieuw aanmelden", status >= 400,
         (melding or {}).get("msg") if isinstance(melding, dict) else status)

print("\nOpruimen")
_, alles = roep("/auth/v1/admin/users?per_page=100")
proef = [g["id"] for g in (alles or {}).get("users", [])
         if (g.get("email") or "").endswith("@dealbot-proef.nl")]
ruim_op(proef)
_, over = roep("/auth/v1/admin/users?per_page=100")
namen = [g.get("email") for g in (over or {}).get("users", [])]
controle("alle proefaccounts zijn opgeruimd",
         not any((n or "").endswith("@dealbot-proef.nl") for n in namen), f"over: {namen}")
_, lijst = roep("/rest/v1/geweerde_adressen?select=email")
controle("de proeflijst is leeg", lijst == [], lijst)

print(f"\n{len(geslaagd)} goed, {len(gezakt)} fout")
if gezakt:
    for regel in gezakt:
        print(f"  - {regel}")
    sys.exit(1)
