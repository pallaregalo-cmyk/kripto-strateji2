const API_BASE = '';

const Api = {
  _token() { return localStorage.getItem('ks_token'); },

  async _req(method, path, body) {
    const headers = { 'Content-Type': 'application/json' };
    if (this._token()) headers['Authorization'] = 'Bearer ' + this._token();
    const res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Sunucu hatası');
    return data;
  },

  get: (p) => Api._req('GET', p),
  post: (p, b) => Api._req('POST', p, b),
  put: (p, b) => Api._req('PUT', p, b),
  delete: (p) => Api._req('DELETE', p),

  // Auth
  login: (email, password) => Api.post('/api/auth/login', { email, password }),
  register: (email, username, password) => Api.post('/api/auth/register', { email, username, password }),
  me: () => Api.get('/api/auth/me'),

  // Strategies
  listStrategies: () => Api.get('/api/strategies/'),
  createStrategy: (data) => Api.post('/api/strategies/', data),
  updateStrategy: (id, data) => Api.put(`/api/strategies/${id}`, data),
  deleteStrategy: (id) => Api.delete(`/api/strategies/${id}`),
  saveBacktest: (data) => Api.post('/api/strategies/backtest', data),
  backtestHistory: (id) => Api.get(`/api/strategies/${id}/history`),

  // Watchlist
  getWatchlist: () => Api.get('/api/watchlist/'),
  addToWatchlist: (symbol) => Api.post('/api/watchlist/', { symbol }),
  removeFromWatchlist: (symbol) => Api.delete(`/api/watchlist/${symbol}`),

  // User
  getSettings: () => Api.get('/api/users/settings'),
  updateSettings: (data) => Api.put('/api/users/settings', data),
  changePassword: (current_password, new_password) =>
    Api.put('/api/users/password', { current_password, new_password }),
  getStats: () => Api.get('/api/users/stats'),
};

// Binance public API (client-side, no auth needed)
const Binance = {
  async klines(symbol, interval, startTime, endTime) {
    const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&startTime=${startTime}&endTime=${endTime}&limit=1000`;
    const r = await fetch(url);
    if (!r.ok) throw new Error('Binance API hatası');
    return r.json();
  },
  async price(symbol) {
    const r = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`);
    if (!r.ok) return null;
    const d = await r.json();
    return parseFloat(d.price);
  },
  async prices(symbols) {
    const r = await fetch('https://api.binance.com/api/v3/ticker/price');
    if (!r.ok) return {};
    const all = await r.json();
    const map = {};
    all.forEach(t => { if (symbols.includes(t.symbol)) map[t.symbol] = parseFloat(t.price); });
    return map;
  },
  tfMs(tf) {
    return { '1m': 60000, '3m': 180000, '5m': 300000, '15m': 900000, '30m': 1800000, '1h': 3600000, '4h': 14400000, '1d': 86400000 }[tf] || 900000;
  },
  async allKlines(symbol, tf, days, onProgress) {
    const endTime = Date.now();
    const startTime = endTime - days * 86400000;
    const chunkMs = 1000 * this.tfMs(tf);
    const totalMs = endTime - startTime;
    let all = [], cur = startTime, fetched = 0;
    while (cur < endTime) {
      const ce = Math.min(cur + chunkMs, endTime);
      const data = await this.klines(symbol, tf, cur, ce);
      if (!data.length) break;
      all = all.concat(data);
      cur = data[data.length - 1][0] + this.tfMs(tf);
      fetched += chunkMs;
      if (onProgress) onProgress(Math.min(99, Math.round(fetched / totalMs * 100)));
      if (data.length < 1000) break;
      await new Promise(r => setTimeout(r, 80));
    }
    const seen = new Set();
    return all.filter(k => { if (seen.has(k[0])) return false; seen.add(k[0]); return true; })
              .sort((a, b) => a[0] - b[0]);
  }
};
// Bot
Api.startBot = (strategy_id, trade_amount) => Api.post('/api/bot/start', { strategy_id, trade_amount });
Api.stopBot  = () => Api.post('/api/bot/stop');
Api.botStatus = () => Api.get('/api/bot/status');
