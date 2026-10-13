# Flux instituțional BTC

Dashboard cu fluxurile nete zilnice ale ETF-urilor spot Bitcoin din SUA (sursa: API-ul oficial SoSoValue).

## Structură

```
flux-btc/
├── index.html                         ← pagina (grafice d3, totul într-un fișier)
├── api/etf-flows.js                   ← funcție Vercel: date live de la SoSoValue (ultima lună)
├── vercel.json                        ← durata maximă a funcției
├── data/
│   └── etf_flows.csv                  ← copie de rezervă: o zi pe rând, milioane $
├── update_data.py                     ← actualizează manual CSV-ul de la SoSoValue (doar Python, fără pip)
├── .github/workflows/update-data.yml  ← robot GitHub pentru CSV (momentan blocat de SoSoValue, vezi mai jos)
└── README.md
```

## Cum se actualizează datele

Pe Vercel, pagina cere datele de la `api/etf-flows`, care le ia direct de la SoSoValue. Răspunsul e ținut
în cache 6 ore, deci site-ul se actualizează singur, fără calculatorul tău și fără commit-uri.
Dacă funcția nu răspunde (cheie lipsă, API indisponibil, rulare locală), pagina folosește
`data/etf_flows.csv`. Subsolul paginii arată ce sursă e folosită în acel moment.

Fluxurile ETF sunt date **zilnice**, nu în timp real: emitenții (BlackRock, Fidelity etc.) raportează
o dată pe zi, după închiderea bursei din SUA (~23:00 ora României), iar cifrele se definitivează T+1.
Ziua de ieri apare deci peste noapte sau a doua zi dimineață. Dacă datele rămân în urmă peste 4 zile,
pagina afișează un avertisment roșu.

De ce nu Farside: farside.co.uk blochează cererile automate (Cloudflare, 403).
De ce nu robotul GitHub: SoSoValue (tot prin Cloudflare) blochează serverele GitHub Actions.

## Publicare pe Vercel

1. vercel.com → **Add New → Project** → importi repo-ul `flux-btc` din GitHub
   (dacă nu apare, „Adjust GitHub App Permissions” și îi dai acces la repo).
2. Framework Preset: **Other**, fără build. Înainte de Deploy, la **Environment Variables**:
   nume `SOSO_API_KEY`, valoare = cheia de pe https://sosovalue.com/developer/dashboard.
3. **Deploy**. Verificare: `https://<site>.vercel.app/api/etf-flows` trebuie să dea JSON cu `rows`.
   Prima cerere durează ~1 minut (12 ETF-uri, cu pauze din cauza limitei API), apoi vine din cache.

## Rulare locală (opțional)

Local nu există funcția Vercel, așa că pagina folosește CSV-ul. Trebuie deschisă printr-un server local:
în terminal `python -m http.server 8000`, apoi http://localhost:8000.

Actualizare manuală a CSV-ului (necesită Python 3.9+), în PowerShell:

```
$env:SOSO_API_KEY = "cheia_ta"
python update_data.py
```

Scriptul rescrie zilele din ultima lună cu cifrele SoSoValue și adaugă zilele noi. Se oprește la
prima zi nedecontată (o reia data viitoare). Dacă suma ETF-urilor nu dă Total-ul (de obicei a apărut
un ETF nou), iese cu eroare: adaugă tickerul în `TICKERS` din `update_data.py`, `api/etf-flows.js` și `index.html`.
