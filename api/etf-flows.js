// Funcție Vercel: ia fluxurile ETF spot BTC din SUA de la SoSoValue (ultima lună) și le dă paginii
// în același format ca data/etf_flows.csv. Răspunsul e ținut în cache-ul Vercel 6 ore, deci API-ul
// SoSoValue e apelat de câteva ori pe zi, indiferent câți vizitatori are site-ul.
// Cheia se pune în Vercel: Project → Settings → Environment Variables → SOSO_API_KEY.

const API = 'https://openapi.sosovalue.com/openapi/v1';
const TICKERS = ['IBIT', 'FBTC', 'BITB', 'ARKB', 'BTCO', 'EZBC', 'BRRR', 'HODL', 'BTCW', 'MSBT', 'GBTC', 'BTC'];
const PAUSE = 4000; // ms între cereri: API-ul dă 429 dacă sunt prea dese

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const millions = (v) => Math.round(Number(v) / 1e5) / 10 + 0; // + 0 transformă -0 în 0

async function get(path, key) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const resp = await fetch(API + path, { headers: { 'x-soso-api-key': key, 'User-Agent': 'flux-btc' } });
    const text = await resp.text();
    let body;
    try { body = JSON.parse(text); } catch { body = null; }
    if (resp.status === 429 && attempt < 2) {
      await sleep(((body && body.retry_after) || 20) * 1000 + 1000);
      continue;
    }
    if (!resp.ok || !body || body.code !== 0) {
      throw new Error(`${path} → HTTP ${resp.status}: ${body ? body.message : text.slice(0, 120)}`);
    }
    return body.data || [];
  }
}

module.exports = async (req, res) => {
  const key = (process.env.SOSO_API_KEY || '').trim();
  if (!key) {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(500).json({ error: 'Lipsește SOSO_API_KEY în Environment Variables din Vercel.' });
  }
  try {
    const end = new Date();
    const start = new Date(end.getTime() - 30 * 864e5);
    const win = `start_date=${start.toISOString().slice(0, 10)}&end_date=${end.toISOString().slice(0, 10)}`;

    const totals = await get(`/etfs/summary-history?symbol=BTC&country_code=US&limit=300&${win}`, key);
    const perEtf = {};
    for (const t of TICKERS) {
      await sleep(PAUSE);
      perEtf[t] = Object.fromEntries((await get(`/etfs/${t}/history?${win}`, key)).map((r) => [r.date, r.net_inflow]));
    }

    // Ca în update_data.py: ne oprim la prima zi nedecontată sau la care suma ETF-urilor ≠ Total.
    const rows = [];
    let warning = null;
    for (const r of totals.slice().sort((a, b) => (a.date < b.date ? -1 : 1))) {
      if (r.total_net_inflow == null) break;
      const row = { date: r.date };
      TICKERS.forEach((t) => { row[t] = millions(perEtf[t][r.date] || 0); });
      row.Total = millions(r.total_net_inflow);
      const sum = Math.round(TICKERS.reduce((s, t) => s + row[t], 0) * 10) / 10;
      if (Math.abs(sum - row.Total) > 0.5) {
        warning = `${r.date}: suma ETF-urilor ${sum} ≠ Total ${row.Total} (probabil un ETF nou)`;
        break;
      }
      rows.push(row);
    }

    res.setHeader('Cache-Control', 'public, s-maxage=21600, stale-while-revalidate=86400');
    return res.status(200).json({ updated: end.toISOString(), source: 'SoSoValue', warning, rows });
  } catch (e) {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(502).json({ error: String(e.message || e) });
  }
};
