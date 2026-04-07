const TF_LABELS = { '1m': '1d', '3m': '3d', '5m': '5d', '15m': '15d', '30m': '30d', '1h': '1s', '4h': '4s', '1d': '1G' };
const TF_NAMES  = { '1m': '1 dakika', '3m': '3 dakika', '5m': '5 dakika', '15m': '15 dakika', '30m': '30 dakika', '1h': '1 saat', '4h': '4 saat', '1d': '1 gün' };
const COINS = [
  {sym:'BTC',name:'Bitcoin'},{sym:'ETH',name:'Ethereum'},{sym:'BNB',name:'BNB'},
  {sym:'SOL',name:'Solana'},{sym:'XRP',name:'Ripple'},{sym:'ADA',name:'Cardano'},
  {sym:'DOGE',name:'Dogecoin'},{sym:'AVAX',name:'Avalanche'},{sym:'DOT',name:'Polkadot'},
  {sym:'MATIC',name:'Polygon'},{sym:'LINK',name:'Chainlink'},{sym:'LTC',name:'Litecoin'},
  {sym:'UNI',name:'Uniswap'},{sym:'ATOM',name:'Cosmos'},{sym:'NEAR',name:'NEAR Protocol'},
  {sym:'INJ',name:'Injective'},{sym:'ARB',name:'Arbitrum'},{sym:'OP',name:'Optimism'},
  {sym:'SUI',name:'Sui'},{sym:'APT',name:'Aptos'},{sym:'TON',name:'Toncoin'},
  {sym:'PEPE',name:'Pepe'},{sym:'WIF',name:'dogwifhat'},{sym:'TRX',name:'TRON'},
  {sym:'XLM',name:'Stellar'},{sym:'HBAR',name:'Hedera'},{sym:'FIL',name:'Filecoin'},
  {sym:'SEI',name:'Sei'},{sym:'RUNE',name:'THORChain'},{sym:'RNDR',name:'Render'},
];
const NOTES = [
  {label:'SMA Crossover',html:`<strong>Nasıl çalışır?</strong><br>Kısa SMA, uzun SMA'yı yukarı kestiğinde <em>altın kesişim (golden cross)</em> → AL. Aşağı kestiğinde <em>ölüm kesişimi</em> → SAT.<ul><li><strong>9/21:</strong> Scalping, kısa vadeli swing</li><li><strong>20/50:</strong> Klasik swing trade</li><li><strong>50/200:</strong> Uzun vadeli trend takibi</li></ul>`},
  {label:'RSI Filtresi',html:`<strong>RSI neden eklenir?</strong><br>Aşırı alım/satım bölgelerindeki sahte crossover sinyallerini filtreler.<ul><li><strong>70/30:</strong> Standart</li><li><strong>80/20:</strong> Agresif, daha az sinyal</li><li><strong>60/40:</strong> Konservatif, daha fazla sinyal</li></ul>`},
  {label:'Risk Yönetimi',html:`<strong>Yaygın Risk:Ödül oranları</strong><ul><li><strong>1:2</strong> — %33 kazanç yeterli</li><li><strong>1:3</strong> — %25 kazanç yeterli (önerilen)</li></ul>Her işlemde toplam sermayenin max <strong>%1-2</strong>'sini riske at.`},
  {label:'Optimizasyon',html:`<strong>İpuçları</strong><ul><li>Önce büyük TF (4s/günlük) trendini belirle</li><li>Backtest en az 3-6 ay olmalı</li><li>Over-fitting tehlikesi: geçmişe çok uyan parametre gelecekte çalışmaz</li></ul>`},
  {label:'Tuzaklar',html:`<strong>Sık hatalar</strong><ul><li><strong>Whipsaw:</strong> Yatay piyasada sürekli çaprazlanma → ADX>25 filtresi ekle</li><li><strong>Stop koymamak:</strong> Tek büyük mum tüm kazancı silebilir</li><li>Kısa SMA > Uzun SMA karıştırmak</li></ul>`},
];

// ── DASHBOARD ──
const DashboardPage = {
  async render(el) {
    el.innerHTML = `
      <div class="page-header">
        <div><div class="page-title">Pano</div><div class="page-sub" id="dash-sub">Yükleniyor...</div></div>
      </div>
      <div class="metrics-grid" id="dash-metrics">
        <div class="met"><div class="met-l">Stratejiler</div><div class="met-v blue" id="dm-strat">—</div></div>
        <div class="met"><div class="met-l">Backtest Sayısı</div><div class="met-v" id="dm-bt">—</div></div>
        <div class="met"><div class="met-l">İzleme Listesi</div><div class="met-v" id="dm-wl">—</div></div>
        <div class="met"><div class="met-l">En İyi P&L</div><div class="met-v pos" id="dm-best">—</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px;" id="dash-grids">
        <div class="card">
          <div class="card-title">Son Stratejiler</div>
          <div id="dash-recent-strats">Yükleniyor...</div>
        </div>
        <div class="card">
          <div class="card-title">İzleme Listesi</div>
          <div class="wl-grid" id="dash-wl-grid" style="grid-template-columns:1fr 1fr;gap:8px;"></div>
        </div>
      </div>`;
    try {
      const [stats, strats, wl] = await Promise.all([Api.getStats(), Api.listStrategies(), Api.getWatchlist()]);
      document.getElementById('dm-strat').textContent = stats.strategy_count;
      document.getElementById('dm-bt').textContent = stats.backtest_count;
      document.getElementById('dm-wl').textContent = stats.watchlist_count;
      document.getElementById('dm-best').textContent = stats.best_strategy ? '+' + stats.best_strategy.total_pnl.toFixed(2) + '%' : '—';
      document.getElementById('dash-sub').textContent = 'Hoş geldin! Son güncelleme: ' + new Date().toLocaleTimeString('tr-TR');

      const rs = document.getElementById('dash-recent-strats');
      const recent = strats.slice(0, 4);
      if (!recent.length) { rs.innerHTML = '<div style="color:var(--text2);font-size:13px;">Henüz strateji yok</div>'; }
      else {
        rs.innerHTML = recent.map(s => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:0.5px solid var(--border);">
            <div>
              <div style="font-size:13px;font-weight:500;">${s.name}</div>
              <div style="font-size:11px;color:var(--text2);">${s.symbol} · ${TF_NAMES[s.timeframe] || s.timeframe}</div>
            </div>
            <div style="font-size:12px;font-weight:600;color:${s.last_pnl > 0 ? 'var(--green)' : s.last_pnl < 0 ? 'var(--red)' : 'var(--text2)'}">
              ${s.last_pnl != null ? (s.last_pnl > 0 ? '+' : '') + s.last_pnl.toFixed(2) + '%' : '—'}
            </div>
          </div>`).join('');
      }

      // Watchlist prices
      const wlEl = document.getElementById('dash-wl-grid');
      if (!wl.length) { wlEl.innerHTML = '<div style="color:var(--text2);font-size:13px;">İzleme listesi boş</div>'; }
      else {
        wlEl.innerHTML = wl.slice(0, 6).map(w => `
          <div class="wl-card" style="padding:10px;" onclick="App.navigate('watchlist')">
            <div class="wl-sym">${w.symbol.replace('USDT', '')}</div>
            <div class="wl-price" id="wlp-${w.symbol}">Yükleniyor...</div>
          </div>`).join('');
        const syms = wl.slice(0, 6).map(w => w.symbol);
        const prices = await Binance.prices(syms);
        syms.forEach(sym => {
          const el2 = document.getElementById('wlp-' + sym);
          if (el2 && prices[sym]) el2.textContent = '$' + ChartEngine.fp(prices[sym]);
        });
      }
    } catch (e) { console.error(e); }
  }
};

// ── STRATEGY PAGE ──
const StrategyPage = {
  strategies: [],
  activeId: null,
  rawPrices: [],
  rawLabels: [],
  loading: false,

  async render(el) {
    el.innerHTML = `
      <div class="page-header">
        <div><div class="page-title">Stratejiler</div></div>
        <button class="btn-primary btn-sm" id="new-strat-btn" style="width:auto;">+ Yeni Strateji</button>
      </div>
      <div style="display:grid;grid-template-columns:300px 1fr;gap:14px;align-items:start;" id="strat-layout">
        <div>
          <div class="strategy-grid" id="strat-list">Yükleniyor...</div>
        </div>
        <div id="strat-detail">
          <div class="card" style="text-align:center;padding:40px;color:var(--text2);">Sol taraftan bir strateji seçin veya yeni oluşturun</div>
        </div>
      </div>`;
    document.getElementById('new-strat-btn').onclick = () => this.openEditor(null);
    await this.loadStrategies();
  },

  async loadStrategies() {
    this.strategies = await Api.listStrategies();
    const el = document.getElementById('strat-list');
    if (!el) return;
    if (!this.strategies.length) {
      el.innerHTML = '<div style="color:var(--text2);font-size:13px;padding:12px;">Henüz strateji yok. Yeni oluşturun.</div>';
      return;
    }
    el.innerHTML = this.strategies.map(s => `
      <div class="strat-card" data-id="${s.id}" onclick="StrategyPage.selectStrategy(${s.id})">
        <div class="strat-card-header">
          <span class="strat-name">${s.name}</span>
          <div class="strat-actions">
            <button class="btn-outline btn-sm" onclick="event.stopPropagation();StrategyPage.openEditor(${s.id})">Düzenle</button>
            <button class="btn-danger btn-sm" onclick="event.stopPropagation();StrategyPage.deleteStrategy(${s.id})">Sil</button>
          </div>
        </div>
        <div class="strat-meta">
          <span class="pill blue">${s.symbol}</span>
          <span class="pill">${TF_NAMES[s.timeframe] || s.timeframe}</span>
          <span class="pill">${s.days}g</span>
          <span class="pill">SMA ${s.sma1}/${s.sma2}</span>
        </div>
        <div class="strat-stats">
          <div class="strat-stat"><div class="strat-stat-l">İşlem</div><div class="strat-stat-v">${s.last_trades ?? '—'}</div></div>
          <div class="strat-stat"><div class="strat-stat-l">Kazanç %</div><div class="strat-stat-v">${s.last_wr != null ? s.last_wr + '%' : '—'}</div></div>
          <div class="strat-stat"><div class="strat-stat-l">P&L</div><div class="strat-stat-v ${s.last_pnl > 0 ? 'pos' : s.last_pnl < 0 ? 'neg' : ''}">${s.last_pnl != null ? (s.last_pnl > 0 ? '+' : '') + s.last_pnl.toFixed(2) + '%' : '—'}</div></div>
          <div class="strat-stat"><div class="strat-stat-l">MaxDD</div><div class="strat-stat-v neg">${s.last_dd != null ? '-' + s.last_dd.toFixed(2) + '%' : '—'}</div></div>
        </div>
      </div>`).join('');
    if (this.activeId) this.selectStrategy(this.activeId);
  },

  async selectStrategy(id) {
    this.activeId = id;
    document.querySelectorAll('.strat-card').forEach(c => c.style.borderColor = c.dataset.id == id ? 'var(--blue)' : '');
    const s = this.strategies.find(x => x.id === id);
    if (!s) return;
    const det = document.getElementById('strat-detail');
    det.innerHTML = `
      <div class="status-bar"><div class="sdot" id="sdot"></div><span id="stxt">Veri yükleniyor...</span>
        <button class="btn-outline btn-sm" id="rbtn">↻</button>
        <button class="btn-primary btn-sm" id="save-bt-btn" style="width:auto;margin-left:auto;">Backtest Kaydet</button>
        <input type="number" id="bot-amount" placeholder="USDT" min="5" style="width:80px;font-size:12px;padding:4px 6px;border:0.5px solid var(--border2);border-radius:6px;background:var(--bg2);color:var(--text);">
        <button class="btn-outline btn-sm" id="bot-btn" style="width:auto;">Botu Başlat</button>
<span id="bot-status-bar" style="font-size:11px;color:var(--text2);"></span>
      </div>
      <div id="bot-position-bar" style="display:none;background:var(--bg2);border-radius:8px;padding:8px 12px;margin-top:6px;font-size:12px;gap:10px;flex-wrap:wrap;align-items:center;">
        <span id="bp-info" style="color:var(--text2);flex:1;"></span>
        <input type="number" id="bp-sl" placeholder="Yeni SL" step="0.0001" style="width:90px;font-size:12px;padding:3px 6px;border:0.5px solid var(--border2);border-radius:6px;background:var(--bg);color:var(--text);">
        <input type="number" id="bp-tp" placeholder="Yeni TP" step="0.0001" style="width:90px;font-size:12px;padding:3px 6px;border:0.5px solid var(--border2);border-radius:6px;background:var(--bg);color:var(--text);">
        <button class="btn-outline btn-sm" id="bp-update-btn">SL/TP Güncelle</button>
        <button class="btn-danger btn-sm" id="bp-close-btn">Pozisyonu Kapat</button>
      </div>
      <div class="prog-wrap hidden" id="prog-wrap"><div class="prog-fill" id="prog-fill" style="width:0%"></div></div>
      <div class="info-txt" id="cinfo"></div>

      <div style="display:grid;grid-template-columns:240px 1fr;gap:14px;margin-top:12px;">
        <div style="display:flex;flex-direction:column;gap:10px;">
          <div class="card">
            <div class="card-title">Zaman Dilimi</div>
            <div class="btn-row-tf" id="tf-row">
              ${Object.entries(TF_LABELS).map(([k,v]) => `<button class="xbtn${k===s.timeframe?' active':''}" data-tf="${k}">${v}</button>`).join('')}
            </div>
          </div>
          <div class="card">
            <div class="card-title">Veri Aralığı</div>
            <div class="btn-row-tf" id="days-row">
              ${[1,3,7,14,30,90,180,365].map(d => `<button class="xbtn${d===s.days?' active':''}" data-d="${d}">${d<365?d+'g':'1y'}</button>`).join('')}
            </div>
          </div>
          <div class="card">
            <div class="card-title">Parametreler</div>
            ${this.paramRow('sma1','Kısa SMA',3,50,s.sma1)}
            ${this.paramRow('sma2','Uzun SMA',5,200,s.sma2)}
            ${this.paramRow('rsiP','RSI Periyodu',2,30,s.rsi_period)}
            ${this.paramRow('rsiOB','Aşırı Alım',55,90,s.rsi_ob)}
            ${this.paramRow('rsiOS','Aşırı Satım',10,45,s.rsi_os)}
            ${this.paramRow('sl','Stop Loss %',0.5,10,s.stop_loss,0.5)}
            ${this.paramRow('tp','Take Profit %',0.5,20,s.take_profit,0.5)}
          </div>
          <div class="card">
            <div class="card-title">Backtest Sonuçları</div>
            <div class="metrics-grid" style="grid-template-columns:1fr 1fr;">
              <div class="met"><div class="met-l">İşlem</div><div class="met-v" id="bm-t">—</div></div>
              <div class="met"><div class="met-l">Kazanç %</div><div class="met-v" id="bm-w">—</div></div>
              <div class="met"><div class="met-l">P&L</div><div class="met-v" id="bm-p">—</div></div>
              <div class="met"><div class="met-l">MaxDD</div><div class="met-v" id="bm-d">—</div></div>
            </div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;">
          <div class="chart-wrap"><div class="chart-label" id="chart-lbl">Fiyat & SMA</div>
            <div style="position:relative;height:270px;"><canvas id="pChart"></canvas></div>
            <div class="legend">
              <div class="li"><div class="ld" style="background:#6b7280;width:14px;"></div>Fiyat</div>
              <div class="li"><div class="ld" style="background:#2563eb;width:14px;"></div>Kısa SMA</div>
              <div class="li"><div class="ld" style="background:#d97706;width:14px;"></div>Uzun SMA</div>
              <div class="li"><div class="ld" style="background:#16a34a;width:7px;height:7px;border-radius:50%;"></div>Al</div>
              <div class="li"><div class="ld" style="background:#dc2626;width:7px;height:7px;border-radius:50%;"></div>Sat</div>
            </div>
          </div>
          <div class="chart-wrap"><div class="chart-label">RSI</div>
            <div style="position:relative;height:120px;"><canvas id="rChart"></canvas></div>
          </div>
          <div class="card"><div class="card-title">Son Sinyaller</div><div class="siglog" id="siglog"></div></div>
          <div class="card">
            <div class="card-title">Strateji Notları</div>
            <div class="note-tabs">${NOTES.map((n,i) => `<button class="ntab${i===0?' active':''}" data-n="${i}">${n.label}</button>`).join('')}</div>
            <div class="note-body" id="note-body">${NOTES[0].html}</div>
          </div>
        </div>
      </div>`;

    let curTf = s.timeframe, curDays = s.days;
    ChartEngine.buildCharts('pChart', 'rChart');

    const load = async () => {
      if (this.loading) return;
      this.loading = true;
      const sdot = document.getElementById('sdot'), stxt = document.getElementById('stxt');
      sdot.className = 'sdot loading'; stxt.textContent = 'Veri yükleniyor...';
      document.getElementById('prog-wrap').classList.remove('hidden');
      try {
        const [klines] = await Promise.all([
          Binance.allKlines(s.symbol, curTf, curDays, p => {
            const f = document.getElementById('prog-fill'); if (f) f.style.width = p + '%';
          })
        ]);
        this.rawPrices = klines.map(k => parseFloat(k[4]));
        this.rawLabels = klines.map(k => ChartEngine.fmtLabel(k[0], curDays, curTf));
        const n = this.rawPrices.length;
        const ci = document.getElementById('cinfo');
        if (ci) ci.textContent = n.toLocaleString('tr-TR') + ' mum · ' + new Date(klines[0][0]).toLocaleDateString('tr-TR') + ' – ' + new Date(klines[klines.length-1][0]).toLocaleDateString('tr-TR');
        sdot.className = 'sdot ok'; stxt.textContent = 'Güncellendi · ' + new Date().toLocaleTimeString('tr-TR');
        document.getElementById('prog-wrap').classList.add('hidden');
        document.getElementById('chart-lbl').textContent = `Fiyat & SMA · ${TF_NAMES[curTf] || curTf}`;
        this.runUpdate();
      } catch (e) {
        sdot.className = 'sdot err'; stxt.textContent = 'Bağlantı hatası: ' + e.message;
        document.getElementById('prog-wrap').classList.add('hidden');
      }
      this.loading = false;
    };

    this.runUpdate = () => {
      if (!this.rawPrices.length) return;
      const gv = id => parseFloat(document.getElementById(id)?.value) || 0;
      const bt = ChartEngine.render(this.rawPrices, this.rawLabels, {
        sma1: gv('sma1'), sma2: gv('sma2'), rsiPeriod: gv('rsiP'),
        rsiOB: gv('rsiOB'), rsiOS: gv('rsiOS'), stopLoss: gv('sl'), takeProfit: gv('tp')
      }, document.getElementById('siglog'), bt => {
        const pv = bt.pnl;
        document.getElementById('bm-t').textContent = bt.trades;
        document.getElementById('bm-w').textContent = bt.trades ? bt.wr + '%' : '—';
        const pe = document.getElementById('bm-p');
        pe.textContent = bt.trades ? (pv > 0 ? '+' : '') + pv.toFixed(2) + '%' : '—';
        pe.className = 'met-v ' + (pv > 0 ? 'pos' : pv < 0 ? 'neg' : '');
        document.getElementById('bm-d').textContent = bt.trades ? '-' + bt.mdd.toFixed(2) + '%' : '—';
      });
      this._lastBt = bt;
    };

    document.getElementById('tf-row').addEventListener('click', e => {
      const b = e.target.closest('.xbtn'); if (!b) return;
      document.querySelectorAll('#tf-row .xbtn').forEach(x => x.classList.remove('active'));
      b.classList.add('active'); curTf = b.dataset.tf; load();
    });
    document.getElementById('days-row').addEventListener('click', e => {
      const b = e.target.closest('.xbtn'); if (!b) return;
      document.querySelectorAll('#days-row .xbtn').forEach(x => x.classList.remove('active'));
      b.classList.add('active'); curDays = parseInt(b.dataset.d); load();
    });
    document.getElementById('rbtn').onclick = load;

    ['sma1','sma2','rsiP','rsiOB','rsiOS','sl','tp'].forEach(id => {
      const sl = document.getElementById(id), nm = document.getElementById(id + 'n');
      if (!sl || !nm) return;
      sl.addEventListener('input', e => { nm.value = e.target.value; this.runUpdate(); });
      nm.addEventListener('input', e => {
        let v = parseFloat(e.target.value);
        const mn = parseFloat(sl.min), mx = parseFloat(sl.max);
        if (isNaN(v)) return; v = Math.max(mn, Math.min(mx, v));
        sl.value = v; this.runUpdate();
      });
    });

    document.getElementById('save-bt-btn').onclick = async () => {
      if (!this._lastBt || !this._lastBt.trades) { App.toast('Önce veri yükleyin ve çalıştırın', 'error'); return; }
      try { const gv = id2 => parseFloat(document.getElementById(id2)?.value) || 0;
await Api.updateStrategy(id, { name: s.name, symbol: s.symbol, timeframe: curTf, days: curDays, sma1: gv('sma1'), sma2: gv('sma2'), rsi_period: gv('rsiP'), rsi_ob: gv('rsiOB'), rsi_os: gv('rsiOS'), stop_loss: gv('sl'), take_profit: gv('tp'), notes: s.notes });
        await Api.saveBacktest({ strategy_id: id, total_trades: this._lastBt.trades, win_rate: this._lastBt.wr, total_pnl: this._lastBt.pnl, max_drawdown: this._lastBt.mdd });
        App.toast('Backtest kaydedildi', 'success');
        await this.loadStrategies();
      } catch (e) { App.toast(e.message, 'error'); }
    };
document.getElementById('bot-btn').onclick = async () => {
  const btn = document.getElementById('bot-btn');
  const bar = document.getElementById('bot-status-bar');
  try {
    const status = await Api.botStatus();
    if (status.running) {
      await Api.stopBot();
      btn.textContent = 'Botu Başlat';
      btn.className = 'btn-outline btn-sm';
      bar.textContent = 'Bot durduruldu';
    } else {
      const amount = parseFloat(document.getElementById('bot-amount').value);
if (!amount || amount < 5) { App.toast('Minimum 5 USDT girin', 'error'); return; }
await Api.startBot(id, amount);
      btn.textContent = 'Botu Durdur';
      btn.className = 'btn-danger btn-sm';
      bar.textContent = 'Bot çalışıyor...';
      botStatusInterval = setInterval(async () => {
        const s = await Api.botStatus();
        if (!s.running) { clearInterval(botStatusInterval); btn.textContent = 'Botu Başlat'; btn.className = 'btn-outline btn-sm'; }
        bar.textContent = s.running ? `Sinyal: ${s.last_signal} | SMA1: ${s.sma1_val} | SMA2: ${s.sma2_val} | Bakiye: ${s.balance} USDT | İşlem: ${s.trades}` : 'Bot durdu';
const posBar = document.getElementById('bot-position-bar');
if (posBar) {
  if (s.running && s.active_position) {
    posBar.style.display = 'flex';
    const ap = s.active_position;
    document.getElementById('bp-info').textContent = `${ap.side} @ ${ap.entry_price} | SL: ${ap.sl_price} | TP: ${ap.tp_price} | Güncel: ${s.current_price || '—'}`;
  } else {
    posBar.style.display = 'none';
  }
}
      }, 10000);
    }
  } catch (e) { App.toast(e.message, 'error'); }
};
let botStatusInterval;
Api.botStatus().then(s => {
  const btn = document.getElementById('bot-btn');
  const bar = document.getElementById('bot-status-bar');
  if (!btn) return;
  if (s.running) {
    btn.textContent = 'Botu Durdur';
    btn.className = 'btn-danger btn-sm';
    bar.textContent = `Çalışıyor: ${s.symbol} ${s.timeframe}`;
  }
}).catch(() => {});
    det.querySelector('.note-tabs').addEventListener('click', e => {
      const t = e.target.closest('.ntab'); if (!t) return;
      const n = parseInt(t.dataset.n);
      det.querySelectorAll('.ntab').forEach((x, i) => x.classList.toggle('active', i === n));
      document.getElementById('note-body').innerHTML = NOTES[n].html;
    });

    load();
  },

  paramRow(id, label, min, max, val, step = 1) {
    return `<div class="param-row">
      <div class="param-label">${label}</div>
      <div class="param-controls">
        <input type="range" min="${min}" max="${max}" step="${step}" value="${val}" id="${id}">
        <input type="number" min="${min}" max="${max}" step="${step}" value="${val}" id="${id}n" class="numbox">
      </div>
    </div>`;
  },

  openEditor(id) {
    const s = id ? this.strategies.find(x => x.id === id) : null;
    App.openModal(id ? 'Strateji Düzenle' : 'Yeni Strateji', `
      <div class="editor-grid">
        <div class="field" style="grid-column:1/-1"><label>Strateji Adı</label>
          <input type="text" id="e-name" value="${s ? s.name : ''}" placeholder="Örn: BTC Swing Stratejisi" required></div>
        <div class="field"><label>Coin / Parite</label>
          <div class="search-wrap">
            <input class="sinput" id="e-sym-search" placeholder="${s ? s.symbol : 'BTCUSDT'}" autocomplete="off">
            <div class="cdd hidden" id="e-sym-dd"></div>
          </div>
          <input type="hidden" id="e-sym" value="${s ? s.symbol : 'BTCUSDT'}">
        </div>
        <div class="field"><label>Zaman Dilimi</label>
          <select id="e-tf">${Object.entries(TF_NAMES).map(([k,v]) => `<option value="${k}"${s && s.timeframe===k?' selected':''}>${v}</option>`).join('')}</select>
        </div>
        <div class="field"><label>Veri Aralığı (gün)</label>
          <input type="number" id="e-days" value="${s ? s.days : 7}" min="1" max="730"></div>
      </div>
      <div class="section-divider">SMA Parametreleri</div>
      <div class="editor-grid">
        <div class="field"><label>Kısa SMA</label><input type="number" id="e-sma1" value="${s ? s.sma1 : 9}" min="3" max="50"></div>
        <div class="field"><label>Uzun SMA</label><input type="number" id="e-sma2" value="${s ? s.sma2 : 21}" min="5" max="200"></div>
      </div>
      <div class="section-divider">RSI Parametreleri</div>
      <div class="editor-grid">
        <div class="field"><label>RSI Periyodu</label><input type="number" id="e-rsip" value="${s ? s.rsi_period : 14}" min="2" max="30"></div>
        <div class="field"><label>Aşırı Alım</label><input type="number" id="e-rsiob" value="${s ? s.rsi_ob : 70}" min="55" max="90"></div>
        <div class="field"><label>Aşırı Satım</label><input type="number" id="e-rsios" value="${s ? s.rsi_os : 30}" min="10" max="45"></div>
      </div>
      <div class="section-divider">Risk Yönetimi</div>
      <div class="editor-grid">
        <div class="field"><label>Stop Loss %</label><input type="number" id="e-sl" value="${s ? s.stop_loss : 2}" min="0.5" max="10" step="0.5"></div>
        <div class="field"><label>Take Profit %</label><input type="number" id="e-tp" value="${s ? s.take_profit : 4}" min="0.5" max="20" step="0.5"></div>
      </div>
      <div class="section-divider">Notlar</div>
      <div class="field"><textarea id="e-notes" placeholder="Strateji notlarınız...">${s ? s.notes : ''}</textarea></div>
      <div class="modal-footer">
        <button class="btn-outline" onclick="App.closeModal()">İptal</button>
        <button class="btn-primary" style="width:auto;" id="e-save-btn">${id ? 'Güncelle' : 'Oluştur'}</button>
      </div>`);

    // Coin search in editor
    const si = document.getElementById('e-sym-search');
    si.addEventListener('input', e => {
      const q = e.target.value.trim().toLowerCase();
      const dd = document.getElementById('e-sym-dd');
      if (!q) { dd.classList.add('hidden'); return; }
      const res = COINS.filter(c => c.sym.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)).slice(0, 8);
      if (!res.length) { dd.classList.add('hidden'); return; }
      dd.innerHTML = res.map(c => `<div class="ditem" data-s="${c.sym}USDT"><span class="dsym">${c.sym}/USDT</span><span class="dname">${c.name}</span></div>`).join('');
      dd.classList.remove('hidden');
      dd.querySelectorAll('.ditem').forEach(el => el.addEventListener('click', () => {
        document.getElementById('e-sym').value = el.dataset.s;
        si.value = el.dataset.s; dd.classList.add('hidden');
      }));
    });

    document.getElementById('e-save-btn').onclick = async () => {
      const name = document.getElementById('e-name').value.trim();
      if (!name) { App.toast('Strateji adı gerekli', 'error'); return; }
      const sym = document.getElementById('e-sym').value || 'BTCUSDT';
      const data = {
        name, symbol: sym,
        timeframe: document.getElementById('e-tf').value,
        days: parseInt(document.getElementById('e-days').value),
        sma1: parseInt(document.getElementById('e-sma1').value),
        sma2: parseInt(document.getElementById('e-sma2').value),
        rsi_period: parseInt(document.getElementById('e-rsip').value),
        rsi_ob: parseInt(document.getElementById('e-rsiob').value),
        rsi_os: parseInt(document.getElementById('e-rsios').value),
        stop_loss: parseFloat(document.getElementById('e-sl').value),
        take_profit: parseFloat(document.getElementById('e-tp').value),
        notes: document.getElementById('e-notes').value,
      };
      try {
        if (id) await Api.updateStrategy(id, data);
        else { const ns = await Api.createStrategy(data); this.activeId = ns.id; }
        App.closeModal(); App.toast(id ? 'Strateji güncellendi' : 'Strateji oluşturuldu', 'success');
        await this.loadStrategies();
        if (!id && this.activeId) this.selectStrategy(this.activeId);
      } catch (e) { App.toast(e.message, 'error'); }
    };
  },

  async deleteStrategy(id) {
    if (!confirm('Bu stratejiyi silmek istediğinizden emin misiniz?')) return;
    try {
      await Api.deleteStrategy(id);
      if (this.activeId === id) {
        this.activeId = null;
        const det = document.getElementById('strat-detail');
        if (det) det.innerHTML = '<div class="card" style="text-align:center;padding:40px;color:var(--text2);">Sol taraftan bir strateji seçin</div>';
      }
      App.toast('Strateji silindi');
      await this.loadStrategies();
    } catch (e) { App.toast(e.message, 'error'); }
  }
};

// ── WATCHLIST PAGE ──
const WatchlistPage = {
  async render(el) {
    el.innerHTML = `
      <div class="page-header">
        <div><div class="page-title">İzleme Listesi</div></div>
        <div style="display:flex;gap:8px;align-items:center;">
          <div class="search-wrap">
            <input class="sinput" id="wl-search" placeholder="Coin ekle... (BTC, ETH...)" style="width:220px;">
            <div class="cdd hidden" id="wl-dd"></div>
          </div>
        </div>
      </div>
      <div class="wl-grid" id="wl-grid">Yükleniyor...</div>`;

    await this.loadWatchlist();

    const si = document.getElementById('wl-search');
    si.addEventListener('input', e => {
      const q = e.target.value.trim().toLowerCase();
      const dd = document.getElementById('wl-dd');
      if (!q) { dd.classList.add('hidden'); return; }
      const res = COINS.filter(c => c.sym.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)).slice(0, 8);
      if (!res.length) { dd.classList.add('hidden'); return; }
      dd.innerHTML = res.map(c => `<div class="ditem" data-s="${c.sym}USDT"><span class="dsym">${c.sym}/USDT</span><span class="dname">${c.name}</span></div>`).join('');
      dd.classList.remove('hidden');
      dd.querySelectorAll('.ditem').forEach(el2 => el2.addEventListener('click', async () => {
        si.value = ''; dd.classList.add('hidden');
        try { await Api.addToWatchlist(el2.dataset.s); App.toast(el2.dataset.s + ' eklendi', 'success'); await this.loadWatchlist(); }
        catch (e) { App.toast(e.message, 'error'); }
      }));
    });
    document.addEventListener('click', e => { if (!e.target.closest('.search-wrap')) document.getElementById('wl-dd')?.classList.add('hidden'); });
  },

  async loadWatchlist() {
    const wl = await Api.getWatchlist();
    const el = document.getElementById('wl-grid');
    if (!el) return;
    if (!wl.length) { el.innerHTML = '<div style="color:var(--text2);">İzleme listeniz boş. Üstten coin ekleyin.</div>'; return; }
    el.innerHTML = wl.map(w => `
      <div class="wl-card">
        <button class="wl-remove" onclick="WatchlistPage.remove('${w.symbol}')">✕</button>
        <div class="wl-sym">${w.symbol.replace('USDT', '')}<span style="font-size:11px;color:var(--text2);font-weight:400;">/USDT</span></div>
        <div class="wl-price" id="wlp-${w.symbol}">Yükleniyor...</div>
        <div style="font-size:10px;color:var(--text2);margin-top:4px;">${new Date(w.added_at).toLocaleDateString('tr-TR')}</div>
      </div>`).join('');
    const prices = await Binance.prices(wl.map(w => w.symbol));
    wl.forEach(w => {
      const el2 = document.getElementById('wlp-' + w.symbol);
      if (el2 && prices[w.symbol]) el2.textContent = '$' + ChartEngine.fp(prices[w.symbol]);
      else if (el2) el2.textContent = '—';
    });
  },

  async remove(symbol) {
    try { await Api.removeFromWatchlist(symbol); App.toast(symbol + ' kaldırıldı'); await this.loadWatchlist(); }
    catch (e) { App.toast(e.message, 'error'); }
  }
};

// ── PROFILE PAGE ──
const ProfilePage = {
  async render(el) {
    const [me, stats, settings] = await Promise.all([Api.me(), Api.getStats(), Api.getSettings()]);
    el.innerHTML = `
      <div class="page-header"><div class="page-title">Profil</div></div>
      <div class="profile-grid">
        <div style="display:flex;flex-direction:column;gap:14px;">
          <div class="card">
            <div class="card-title">Hesap Bilgileri</div>
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
              <div class="user-avatar" style="width:48px;height:48px;font-size:18px;">${me.username[0].toUpperCase()}</div>
              <div><div style="font-size:16px;font-weight:600;">${me.username}</div><div style="font-size:13px;color:var(--text2);">${me.email}</div></div>
            </div>
            <div style="font-size:12px;color:var(--text2);">Kayıt: ${new Date(me.created_at).toLocaleDateString('tr-TR')}</div>
            <div style="font-size:12px;color:var(--text2);">Son giriş: ${me.last_login ? new Date(me.last_login).toLocaleString('tr-TR') : '—'}</div>
          </div>
          <div class="card">
            <div class="card-title">İstatistikler</div>
            <div class="metrics-grid" style="grid-template-columns:1fr 1fr;">
              <div class="met"><div class="met-l">Stratejiler</div><div class="met-v blue">${stats.strategy_count}</div></div>
              <div class="met"><div class="met-l">Backtestler</div><div class="met-v">${stats.backtest_count}</div></div>
              <div class="met"><div class="met-l">İzleme</div><div class="met-v">${stats.watchlist_count}</div></div>
              <div class="met"><div class="met-l">En İyi P&L</div><div class="met-v pos">${stats.best_strategy ? '+' + stats.best_strategy.total_pnl.toFixed(2) + '%' : '—'}</div></div>
            </div>
            ${stats.best_strategy ? `<div style="font-size:12px;color:var(--text2);margin-top:8px;">En iyi strateji: <strong>${stats.best_strategy.name}</strong></div>` : ''}
          </div>
          <div class="card">
            <div class="card-title">Şifre Değiştir</div>
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div class="field"><label>Mevcut Şifre</label><input type="password" id="pw-cur" placeholder="••••••"></div>
              <div class="field"><label>Yeni Şifre</label><input type="password" id="pw-new" placeholder="En az 6 karakter"></div>
              <button class="btn-outline" onclick="ProfilePage.changePassword()">Şifreyi Güncelle</button>
            </div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px;">
          <div class="card">
            <div class="card-title">Tercihler</div>
            <div style="display:flex;flex-direction:column;gap:12px;">
              <div class="field"><label>Varsayılan Zaman Dilimi</label>
                <select id="pref-tf">${Object.entries(TF_NAMES).map(([k,v]) => `<option value="${k}"${settings.default_tf===k?' selected':''}>${v}</option>`).join('')}</select>
              </div>
              <div class="field"><label>Varsayılan Veri Aralığı (gün)</label>
                <input type="number" id="pref-days" value="${settings.default_days}" min="1" max="365">
              </div>
              <button class="btn-primary" onclick="ProfilePage.saveSettings()">Tercihleri Kaydet</button>
            </div>
          </div>
          <div class="card">
            <div class="card-title">Backtest Geçmişi (Son 10)</div>
            <div id="bt-history">Yükleniyor...</div>
          </div>
        </div>
      </div>`;
    this.loadBtHistory();
  },

  async loadBtHistory() {
    const el = document.getElementById('bt-history');
    if (!el) return;
    try {
      const strats = await Api.listStrategies();
      const allBt = [];
      for (const s of strats.slice(0, 5)) {
        const h = await Api.backtestHistory(s.id);
        h.forEach(b => allBt.push({ ...b, strat_name: s.name }));
      }
      allBt.sort((a, b) => new Date(b.ran_at) - new Date(a.ran_at));
      const rows = allBt.slice(0, 10);
      if (!rows.length) { el.innerHTML = '<div style="color:var(--text2);font-size:13px;">Henüz backtest kaydedilmedi</div>'; return; }
      el.innerHTML = `<table class="history-table">
        <tr><th>Strateji</th><th>İşlem</th><th>W%</th><th>P&L</th><th>Tarih</th></tr>
        ${rows.map(r => `<tr>
          <td>${r.strat_name}</td>
          <td>${r.total_trades}</td>
          <td>${r.win_rate.toFixed(1)}%</td>
          <td style="color:${r.total_pnl > 0 ? 'var(--green)' : 'var(--red)'}">${r.total_pnl > 0 ? '+' : ''}${r.total_pnl.toFixed(2)}%</td>
          <td style="color:var(--text2);font-size:11px;">${new Date(r.ran_at).toLocaleDateString('tr-TR')}</td>
        </tr>`).join('')}
      </table>`;
    } catch (e) { el.innerHTML = '<div style="color:var(--text2);">Yüklenemedi</div>'; }
  },

  async saveSettings() {
    try {
      await Api.updateSettings({
        default_tf: document.getElementById('pref-tf').value,
        default_days: parseInt(document.getElementById('pref-days').value),
      });
      App.toast('Tercihler kaydedildi', 'success');
    } catch (e) { App.toast(e.message, 'error'); }
  },

  async changePassword() {
    const cur = document.getElementById('pw-cur').value;
    const nw  = document.getElementById('pw-new').value;
    if (!cur || !nw) { App.toast('Tüm alanları doldurun', 'error'); return; }
    try {
      await Api.changePassword(cur, nw);
      App.toast('Şifre güncellendi', 'success');
      document.getElementById('pw-cur').value = '';
      document.getElementById('pw-new').value = '';
    } catch (e) { App.toast(e.message, 'error'); }
  }
};
