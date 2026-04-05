const ChartEngine = {
  pChart: null,
  rChart: null,

  sma(data, p) {
    return data.map((_, i) => {
      if (i < p - 1) return null;
      return data.slice(i - p + 1, i + 1).reduce((a, b) => a + b, 0) / p;
    });
  },

  rsi(data, p) {
    const r = Array(data.length).fill(null);
    for (let i = p; i < data.length; i++) {
      let g = 0, l = 0;
      for (let j = i - p + 1; j <= i; j++) {
        const d = data[j] - data[j - 1];
        if (d > 0) g += d; else l -= d;
      }
      const rs = l === 0 ? 100 : g / l;
      r[i] = parseFloat((100 - 100 / (1 + rs)).toFixed(2));
    }
    return r;
  },

  getSignals(s1, s2, rv, ob, os, prices) {
    const sigs = [];
    for (let i = 1; i < prices.length; i++) {
      if (!s1[i] || !s2[i] || !s1[i - 1] || !s2[i - 1]) continue;
      const cu = s1[i - 1] <= s2[i - 1] && s1[i] > s2[i];
      const cd = s1[i - 1] >= s2[i - 1] && s1[i] < s2[i];
      const rv2 = rv[i];
      if (cu && (rv2 === null || rv2 < ob)) sigs.push({ i, type: 'buy', price: prices[i], rsi: rv2 });
      if (cd && (rv2 === null || rv2 > os)) sigs.push({ i, type: 'sell', price: prices[i], rsi: rv2 });
    }
    return sigs;
  },

  backtest(sigs, sl, tp) {
    let trades = 0, wins = 0, pnl = 0, mdd = 0, peak = 0, cum = 0, pos = null;
    for (const s of sigs) {
      if (s.type === 'buy' && !pos) { pos = s; continue; }
      if (s.type === 'sell' && pos) {
        const pct = (s.price - pos.price) / pos.price * 100;
        const c = Math.max(-sl, Math.min(tp, pct));
        pnl += c; cum += c; trades++;
        if (c > 0) wins++;
        if (cum > peak) peak = cum;
        const dd = peak - cum;
        if (dd > mdd) mdd = dd;
        pos = null;
      }
    }
    return { trades, wr: trades ? parseFloat((wins / trades * 100).toFixed(1)) : 0, pnl: parseFloat(pnl.toFixed(2)), mdd: parseFloat(mdd.toFixed(2)) };
  },

  fp(p) {
    if (p === null || p === undefined) return '—';
    if (p >= 10000) return p.toLocaleString('tr-TR', { maximumFractionDigits: 0 });
    if (p >= 1000) return p.toLocaleString('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (p >= 1) return p.toFixed(3);
    if (p >= 0.001) return p.toFixed(5);
    return p.toFixed(8);
  },

  fmtLabel(ts, days, tf) {
    const d = new Date(ts);
    if (tf === '1d') return d.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: '2-digit' });
    if (days <= 1) return d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    if (days <= 7) return d.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: '2-digit' });
  },

  buildCharts(pId, rId) {
    const dk = window.matchMedia('(prefers-color-scheme:dark)').matches;
    const gc = dk ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.06)';
    const tc = dk ? '#9ca3af' : '#6b7280';
    const lc = dk ? '#9ca3af' : '#4b5563';
    if (this.pChart) { this.pChart.destroy(); this.pChart = null; }
    if (this.rChart) { this.rChart.destroy(); this.rChart = null; }
    this.pChart = new Chart(document.getElementById(pId), {
      type: 'line',
      data: { labels: [], datasets: [
        { label: 'Fiyat', data: [], borderColor: lc, borderWidth: 1.5, pointRadius: 0, tension: .1, fill: false, yAxisID: 'y' },
        { label: 'SMA1',  data: [], borderColor: '#2563eb', borderWidth: 2, pointRadius: 0, tension: .1, fill: false, yAxisID: 'y' },
        { label: 'SMA2',  data: [], borderColor: '#d97706', borderWidth: 2, pointRadius: 0, tension: .1, fill: false, borderDash: [5, 4], yAxisID: 'y' },
        { label: 'Al',    data: [], borderColor: '#16a34a', backgroundColor: '#16a34a', pointStyle: 'triangle', pointRadius: 8, showLine: false, yAxisID: 'y' },
        { label: 'Sat',   data: [], borderColor: '#dc2626', backgroundColor: '#dc2626', pointStyle: 'triangle', pointRadius: 8, rotation: 180, showLine: false, yAxisID: 'y' },
      ]},
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 150 },
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false, callbacks: { label: c => c.parsed.y == null ? '' : c.dataset.label + ': $' + this.fp(c.parsed.y) } } },
        scales: {
          x: { ticks: { color: tc, maxTicksLimit: 10, font: { size: 10 }, maxRotation: 25 }, grid: { color: gc } },
          y: { ticks: { color: tc, callback: v => '$' + this.fp(v), font: { size: 10 } }, grid: { color: gc } }
        }
      }
    });
    this.rChart = new Chart(document.getElementById(rId), {
      type: 'line',
      data: { labels: [], datasets: [
        { label: 'RSI', data: [], borderColor: '#7c3aed', borderWidth: 1.5, pointRadius: 0, tension: .1, fill: false },
        { label: 'OB',  data: [], borderColor: '#dc2626', borderWidth: 1, borderDash: [4, 4], pointRadius: 0 },
        { label: 'OS',  data: [], borderColor: '#16a34a', borderWidth: 1, borderDash: [4, 4], pointRadius: 0 },
      ]},
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 150 },
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: tc, maxTicksLimit: 10, font: { size: 10 }, maxRotation: 25 }, grid: { color: gc } },
          y: { min: 0, max: 100, ticks: { color: tc, stepSize: 25, font: { size: 10 } }, grid: { color: gc } }
        }
      }
    });
  },

  render(prices, labels, params, siglogEl, metricsCallback) {
    const { sma1, sma2, rsiPeriod, rsiOB, rsiOS, stopLoss, takeProfit } = params;
    const N = prices.length;
    const s1 = this.sma(prices, sma1);
    const s2 = this.sma(prices, sma2);
    const rv = this.rsi(prices, rsiPeriod);
    const sigs = this.getSignals(s1, s2, rv, rsiOB, rsiOS, prices);
    const bt = this.backtest(sigs, stopLoss, takeProfit);

    this.pChart.data.labels = labels;
    this.pChart.data.datasets[0].data = prices;
    this.pChart.data.datasets[1].data = s1;
    this.pChart.data.datasets[2].data = s2;
    const bp = Array(N).fill(null), sp = Array(N).fill(null);
    for (const s of sigs) { if (s.type === 'buy') bp[s.i] = s.price; else sp[s.i] = s.price; }
    this.pChart.data.datasets[3].data = bp;
    this.pChart.data.datasets[4].data = sp;
    this.pChart.update();

    this.rChart.data.labels = labels;
    this.rChart.data.datasets[0].data = rv;
    this.rChart.data.datasets[1].data = Array(N).fill(rsiOB);
    this.rChart.data.datasets[2].data = Array(N).fill(rsiOS);
    this.rChart.update();

    if (siglogEl) {
      const rec = sigs.slice(-12).reverse();
      if (!rec.length) {
        siglogEl.innerHTML = '<div style="color:var(--text2);font-size:12px;">Sinyal yok — parametreleri ayarlayın</div>';
      } else {
        siglogEl.innerHTML = rec.map(s =>
          `<div class="sr ${s.type}"><span class="sbadge">${s.type === 'buy' ? 'AL' : 'SAT'}</span>
           <span style="opacity:.7;font-size:10px;">${labels[s.i]}</span>
           <span style="font-weight:600;">$${this.fp(s.price)}</span>
           ${s.rsi !== null ? `<span style="font-size:10px;opacity:.65;">RSI ${s.rsi.toFixed(0)}</span>` : ''}</div>`
        ).join('');
      }
    }

    if (metricsCallback) metricsCallback(bt);
    return bt;
  }
};
