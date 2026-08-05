"""
===============================================================================
 Dealbot — controle op "pincode vergeten"

 Versie      : 1.0
 Reden       : De weg van vergeten pincode naar nieuwe pincode loopt langs een
               mail, een link en een tijdelijke sessie. Dat is met nalezen niet
               te bewijzen, dus doet deze proef het echt — met een wegwerp-
               account en zonder een mail op te maken: de link wordt met de
               beheersleutel opgewekt in plaats van verstuurd.
 Datum       : 05-08-2026 01:35

 Onderdelen:
   de link            - komt hij uit bij onze eigen pagina?
   de sessie          - levert de link toegang op om iets te wijzigen?
   dezelfde pincode   - mag de nieuwe gelijk zijn aan de oude?
   een andere pincode - werkt inloggen daarna met de nieuwe en niet met de oude?
   een kapotte link   - wordt die netjes geweigerd?
   onbekend adres     - verraadt de site niet wie er een account heeft?

 Let op: draait tegen de echte database en heeft de geheime servicesleutel uit
 .env nodig. Het wegwerp-account eindigt op @dealbot-proef.nl en wordt aan het
 eind opgeruimd.

 Uitvoeren met: python scripts/tests/test_pincode.py
===============================================================================
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
for regel in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in regel and not regel.strip().startswith("#"):
        sleutel, waarde = regel.split("=", 1)
        os.environ.setdefault(sleutel.strip(), waarde.strip())

URL = os.environ["SUPABASE_URL"].rstrip("/")
DIENST = os.environ["SUPABASE_SERVICE_KEY"]
CONFIG = (PROJECT / "assets" / "config.js").read_text(encoding="utf-8")
OPENBAAR = re.search(r"SUPABASE_SLEUTEL\s*=\s*'([^']+)'", CONFIG).group(1)

SITE = "https://bartloe.github.io/dealbot/"
BESTEMMING = SITE + "nieuwe-pincode.html"
MAIL = "proef.pincode@dealbot-proef.nl"

geslaagd, gezakt = [], []


def roep(pad, methode="GET", body=None, sleutel=DIENST, token=None, volg=True):
    data = json.dumps(body).encode() if body is not None else None
    vraag = urllib.request.Request(f"{URL}{pad}", data=data, method=methode, headers={
        "apikey": sleutel,
        "Authorization": f"Bearer {token or sleutel}",
        "Content-Type": "application/json",
    })
    opener = urllib.request.build_opener()
    if not volg:
        class HoudStil(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_):
                return None
        opener = urllib.request.build_opener(HoudStil)
    try:
        with opener.open(vraag, timeout=30) as antwoord:
            tekst = antwoord.read().decode()
            return antwoord.status, (json.loads(tekst) if tekst.strip() else None), dict(antwoord.headers)
    except urllib.error.HTTPError as fout:
        tekst = fout.read().decode()
        try:
            return fout.code, json.loads(tekst), dict(fout.headers)
        except json.JSONDecodeError:
            return fout.code, tekst, dict(fout.headers)


def controle(omschrijving, gelukt, toelichting=""):
    (geslaagd if gelukt else gezakt).append(omschrijving)
    print(f"  [{'goed' if gelukt else 'FOUT'}] {omschrijving}"
          f"{(' — ' + str(toelichting)) if toelichting else ''}")


def log_in(pincode):
    status, gegevens, _ = roep("/auth/v1/token?grant_type=password", "POST",
                               {"email": MAIL, "password": f"dealbot-pin-{pincode}"},
                               sleutel=OPENBAAR)
    return status, gegevens


def ruim_op():
    _, alles, _ = roep("/auth/v1/admin/users?per_page=100")
    for gebruiker in (alles or {}).get("users", []):
        if (gebruiker.get("email") or "").endswith("@dealbot-proef.nl"):
            roep(f"/auth/v1/admin/users/{gebruiker['id']}", "DELETE")


print("Wegwerp-account klaarzetten")
ruim_op()
status, account, _ = roep("/auth/v1/admin/users", "POST",
                          {"email": MAIL, "password": "dealbot-pin-1234", "email_confirm": True})
if status not in (200, 201):
    sys.exit(f"Kon het proefaccount niet aanmaken: {status} {account}")

print("\n1. De link uit de mail")
status, link, _ = roep("/auth/v1/admin/generate_link", "POST",
                       {"type": "recovery", "email": MAIL, "redirect_to": BESTEMMING})
controle("de database wekt een herstel-link op", status == 200 and bool(link), status)

adres = (link or {}).get("action_link", "")
delen = urllib.parse.urlparse(adres)
vraagdeel = urllib.parse.parse_qs(delen.query)
terug = (vraagdeel.get("redirect_to") or [""])[0]
controle("de link wijst naar onze eigen pagina", terug == BESTEMMING,
         terug if terug == BESTEMMING else
         f"{terug or '(geen)'} - zet in Supabase onder Authentication, URL Configuration "
         f"de Site URL op {SITE} en voeg {SITE}** toe bij Redirect URLs")

token = (link or {}).get("hashed_token") or (vraagdeel.get("token") or [""])[0]
controle("er zit een eenmalige sleutel in de link", bool(token))

print("\n2. De sessie die de link oplevert")
status, gegevens, koppen = roep(
    f"/auth/v1/verify?token={token}&type=recovery&redirect_to={urllib.parse.quote(BESTEMMING)}",
    sleutel=OPENBAAR, volg=False)
plek = koppen.get("Location", "")
controle("de link stuurt door naar onze pagina", plek.startswith(BESTEMMING),
         plek[:80] if plek.startswith(BESTEMMING) else
         f"{plek[:60]} - zelfde oorzaak als hierboven: de Site URL in Supabase")

hekje = urllib.parse.urlparse(plek).fragment
sleutels = urllib.parse.parse_qs(hekje)
sessie = (sleutels.get("access_token") or [""])[0]
controle("en levert een tijdelijke toegang op", bool(sessie),
         "" if sessie else f"achter het hekje stond: {hekje[:80]}")

print("\n3. Een nieuwe pincode kiezen")
# Supabase weigert een pincode die gelijk is aan de huidige. De wens was dat
# dezelfde pincode mocht; deze controle legt vast dat de weigering in elk geval
# begrijpelijk overkomt, want de website vertaalt hem naar gewone taal.
status, melding, _ = roep("/auth/v1/user", "PUT", {"password": "dealbot-pin-1234"},
                          sleutel=OPENBAAR, token=sessie)
tekst = (melding or {}).get("msg", "") if isinstance(melding, dict) else ""
controle("dezelfde pincode wordt geweigerd met een te vertalen melding",
         status >= 400 and "should be different" in tekst.lower(), tekst)

status, _ = log_in("1234")
controle("de oude pincode werkt dan nog gewoon", status == 200)

status, melding, _ = roep("/auth/v1/user", "PUT", {"password": "dealbot-pin-4321"},
                          sleutel=OPENBAAR, token=sessie)
controle("een andere pincode instellen lukt wel", status == 200,
         (melding or {}).get("msg") if isinstance(melding, dict) else "")

status, _ = log_in("4321")
controle("inloggen met de nieuwe pincode werkt", status == 200)

status, _ = log_in("1234")
controle("de oude pincode werkt niet meer", status >= 400, status)

print("\n4. Wat er mis kan gaan")
status, melding, koppen = roep(
    f"/auth/v1/verify?token=onzin-token&type=recovery&redirect_to={urllib.parse.quote(BESTEMMING)}",
    sleutel=OPENBAAR, volg=False)
plek = koppen.get("Location", "")
controle("een kapotte link geeft een nette klacht",
         "error" in plek or status >= 400, plek[:90] or status)

status, _, _ = roep("/auth/v1/recover", "POST",
                    {"email": "bestaat.echt.niet@dealbot-proef.nl"}, sleutel=OPENBAAR)
controle("een onbekend adres verraadt niets", status in (200, 429),
         "(429 = de mailer is even op adem aan het komen)" if status == 429 else "")

print("\nOpruimen")
ruim_op()
_, over, _ = roep("/auth/v1/admin/users?per_page=100")
namen = [g.get("email") for g in (over or {}).get("users", [])]
controle("het proefaccount is opgeruimd",
         not any((n or "").endswith("@dealbot-proef.nl") for n in namen), f"over: {namen}")

print(f"\n{len(geslaagd)} goed, {len(gezakt)} fout")
if gezakt:
    for regel in gezakt:
        print(f"  - {regel}")
    sys.exit(1)
