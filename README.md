# Flux instituțional BTC

Dashboard cu fluxurile nete zilnice ale ETF-urilor spot Bitcoin din SUA (sursa: API-ul oficial SoSoValue).

## Structură

```
flux-btc/
├── index.html                         ← pagina (grafice d3, totul într-un fișier)
├── data/
│   └── etf_flows.csv                  ← datele: o zi pe rând, milioane $
├── update_data.py                     ← ia zilele noi de la SoSoValue (doar Python, fără pip)
├── .github/workflows/update-data.yml  ← rulează update_data.py automat de 4 ori pe zi
└── README.md
```

## Cât de „live” sunt datele

Fluxurile ETF sunt date **zilnice**, nu în timp real: emitenții (BlackRock, Fidelity etc.) raportează
o dată pe zi, după închiderea bursei din SUA (~23:00 ora României), iar cifrele se definitivează T+1.
Nu există o sursă publică intraday pentru „ce cumpără instituțiile acum”. Ziua de ieri apare deci
în dashboard peste noapte sau a doua zi dimineață. Dacă datele rămân în urmă peste 4 zile,
pagina afișează un avertisment roșu.

De ce nu Farside: farside.co.uk blochează cererile automate (Cloudflare, 403), deci nu poate fi actualizat automat.

## Pornire: actualizare automată zilnică (o singură dată)

1. **Cheia API SoSoValue:** cont pe https://sosovalue.com/developer/dashboard → „Apply your Key”.
   Aștepți aprobarea (statusul apare în același dashboard).
2. **Repo GitHub:** pe github.com → New repository (ex. `flux-btc`) → „uploading an existing file” →
   tragi în pagină *conținutul* folderului `flux-btc` (inclusiv folderul `.github`) → Commit.
   Dacă Windows ascunde `.github`, creezi fișierul în GitHub: Add file → Create new file →
   numele `.github/workflows/update-data.yml` și lipești conținutul.
3. **Cheia în GitHub:** repo → Settings → Secrets and variables → Actions → New repository secret →
   nume `SOSO_API_KEY`, valoare = cheia.
4. **Prima rulare:** tab-ul Actions → „Actualizare date ETF” → Run workflow. Dacă trece, CSV-ul primește
   ultima lună de la SoSoValue (rândurile din acea lună sunt rescrise cu cifrele SoSoValue).
   De aici rulează singur de 4 ori pe zi; dacă eșuează, GitHub îți trimite email.
5. **Site-ul:** repo → Settings → Pages → Source: Deploy from a branch → `main` / `(root)` → Save.
   Primești un link `https://<user>.github.io/flux-btc/`, care se actualizează la fiecare commit al botului.
   (Merge și Vercel: Add New → Project → importi repo-ul.)

## Rulare locală (opțional)

Pagina citește `data/etf_flows.csv`, deci trebuie deschisă printr-un server local:
în VS Code instalezi extensia **Live Server** → click dreapta pe `index.html` → **Open with Live Server**.

Actualizare manuală a datelor (necesită Python 3.9+), în PowerShell:

```
$env:SOSO_API_KEY = "cheia_ta"
python update_data.py
```

Scriptul rescrie zilele din ultima lună cu cifrele SoSoValue și adaugă zilele noi. Se oprește la
prima zi nedecontată (o reia data viitoare). Dacă suma ETF-urilor nu dă Total-ul (de obicei a apărut
un ETF nou), iese cu eroare: adaugă tickerul în `TICKERS` din `update_data.py` și din `index.html`.
