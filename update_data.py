"""
Actualizează data/etf_flows.csv din API-ul oficial SoSoValue (https://sosovalue.com/developer/dashboard).

Rulare:  SOSO_API_KEY=<cheia ta> python update_data.py
Cerințe: Python 3.9+, fără pachete externe.

Reguli:
- API-ul dă doar ultima lună; zilele din fereastra asta sunt rescrise cu cifrele SoSoValue
  (fluxurile se definitivează T+1 și uneori se corectează), zilele mai vechi rămân neatinse;
- o zi e acceptată doar dacă e decontată (Total != null) și suma ETF-urilor = Total (toleranță 0.5 mil $);
- la prima zi nedecontată sau care nu se potrivește ne oprim, ca să nu rămână găuri în date;
  ea va fi reîncercată la rularea următoare;
- o nepotrivire pe o zi decontată (de obicei = a apărut un ETF nou) iese cu cod 1, ca să primești alertă.
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

API = "https://openapi.sosovalue.com/openapi/v1"
CSV_PATH = Path(__file__).parent / "data" / "etf_flows.csv"
TICKERS = ["IBIT", "FBTC", "BITB", "ARKB", "BTCO", "EZBC", "BRRR", "HODL", "BTCW", "MSBT", "GBTC", "BTC"]
COLUMNS = ["date", *TICKERS, "Total"]
TOLERANCE = 0.5  # milioane $
PAUSE = 6  # secunde între cereri: limita API e 20/minut, dar în practică dă 429 și la 15/minut


def get(path: str, key: str, **params) -> list:
    url = f"{API}{path}?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"x-soso-api-key": key, "User-Agent": "flux-btc updater"})
    for attempt in range(4):
        time.sleep(PAUSE)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            raw = e.read() or b"{}"
            try:
                body = json.loads(raw)
            except ValueError:
                body = {"message": f"răspuns non-JSON (server={e.headers.get('Server')}, "
                                   f"cf-mitigated={e.headers.get('cf-mitigated')}): {raw[:200]!r}"}
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(int(body.get("retry_after", 30)) + 1)
                continue
            sys.exit(f"STOP: {path} → HTTP {e.code}: {body.get('message', body)}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(15)
                continue
            sys.exit(f"STOP: {path} → {e}")
    if body.get("code") != 0:
        sys.exit(f"STOP: {path} → {body.get('code')}: {body.get('message')}")
    return body.get("data") or []


def millions(v) -> float:
    return round(float(v) / 1e6, 1) + 0.0  # + 0.0 transformă -0.0 în 0.0


def main() -> None:
    key = os.environ.get("SOSO_API_KEY", "").strip()
    if not key:
        sys.exit("STOP: lipsește SOSO_API_KEY (cheia de pe https://sosovalue.com/developer/dashboard).")

    end = date.today()
    window = {"start_date": (end - timedelta(days=30)).isoformat(), "end_date": end.isoformat()}

    # .get(): în zilele încă nedecontate SoSoValue poate omite câmpul cu totul, nu doar să-l dea null.
    totals = {r["date"]: r.get("total_net_inflow")
              for r in get("/etfs/summary-history", key, symbol="BTC", country_code="US", limit=300, **window)}
    per_etf = {t: {r["date"]: r.get("net_inflow") for r in get(f"/etfs/{t}/history", key, **window)} for t in TICKERS}

    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = {r["date"]: r for r in csv.DictReader(f)}

    changes, mismatch = [], False
    for d in sorted(totals):
        if totals[d] is None:
            print(f"AȘTEPT {d}: ziua nu e încă decontată la SoSoValue")
            break
        new = {"date": d, **{t: millions(per_etf[t].get(d) or 0) for t in TICKERS}, "Total": millions(totals[d])}
        s = round(sum(new[t] for t in TICKERS), 1)
        if abs(s - new["Total"]) > TOLERANCE:
            print(f"STOP {d}: suma ETF-urilor {s} ≠ Total {new['Total']}. "
                  f"Probabil a apărut un ETF nou: verifică GET /etfs?symbol=BTC&country_code=US și TICKERS.")
            mismatch = True
            break
        new = {k: (f"{v:.1f}" if isinstance(v, float) else v) for k, v in new.items()}
        old = rows.get(d)
        if old != new:
            changes.append(("ACTUALIZAT" if old else "ADĂUGAT", d, old, new))
            rows[d] = new

    if changes:
        with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows[d] for d in sorted(rows))
        for kind, d, old, new in changes:
            was = f" (era {old['Total']})" if old else ""
            print(f"{kind} {d}: Total {float(new['Total']):+.1f} mil ${was}")
    else:
        print(f"Nicio schimbare. Ultima zi în date: {max(rows) if rows else '-'}")

    if mismatch:
        sys.exit(1)


if __name__ == "__main__":
    main()
