const App = {
  user: null,
  currentPage: 'dashboard',

  async init() {
    this.bindAuth();
    const token = localStorage.getItem('ks_token');
    if (token) {
      try {
        this.user = await Api.me();
        this.showApp();
      } catch {
        localStorage.removeItem('ks_token');
        this.showAuth();
      }
    } else {
      this.showAuth();
    }
  },

  showAuth() {
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
  },

  showApp() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    const u = this.user;
    document.getElementById('sidebar-avatar').textContent = u.username[0].toUpperCase();
    document.getElementById('sidebar-name').textContent = u.username;
    document.getElementById('sidebar-email').textContent = u.email;
    this.navigate('dashboard');
  },

  navigate(page) {
    this.currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.navitem').forEach(n => n.classList.remove('active'));
    const pageEl = document.getElementById('page-' + page);
    if (pageEl) pageEl.classList.add('active');
    document.querySelector(`.navitem[data-page="${page}"]`)?.classList.add('active');
    const pages = { dashboard: DashboardPage, strategy: StrategyPage, watchlist: WatchlistPage, profile: ProfilePage, history: TradeHistoryPage };
    if (pages[page]) pages[page].render(pageEl);
  },

  bindAuth() {
    // Tab switching
    document.querySelectorAll('.atab').forEach(t => {
      t.addEventListener('click', () => {
        document.querySelectorAll('.atab').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        const tab = t.dataset.tab;
        document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
        document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
      });
    });

    // Login
    document.getElementById('login-form').addEventListener('submit', async e => {
      e.preventDefault();
      const btn = document.getElementById('login-btn');
      const errEl = document.getElementById('login-error');
      btn.disabled = true; btn.textContent = 'Giriş yapılıyor...';
      errEl.classList.add('hidden');
      try {
        const res = await Api.login(
          document.getElementById('login-email').value,
          document.getElementById('login-password').value
        );
        localStorage.setItem('ks_token', res.token);
        this.user = await Api.me();
        this.showApp();
      } catch (e) {
        errEl.textContent = e.message; errEl.classList.remove('hidden');
      }
      btn.disabled = false; btn.textContent = 'Giriş Yap';
    });

    // Register
    document.getElementById('register-form').addEventListener('submit', async e => {
      e.preventDefault();
      const btn = document.getElementById('reg-btn');
      const errEl = document.getElementById('reg-error');
      btn.disabled = true; btn.textContent = 'Kayıt oluşturuluyor...';
      errEl.classList.add('hidden');
      try {
        const res = await Api.register(
          document.getElementById('reg-email').value,
          document.getElementById('reg-username').value,
          document.getElementById('reg-password').value
        );
        localStorage.setItem('ks_token', res.token);
        this.user = await Api.me();
        this.showApp();
      } catch (e) {
        errEl.textContent = e.message; errEl.classList.remove('hidden');
      }
      btn.disabled = false; btn.textContent = 'Kayıt Ol';
    });

    // Nav
    document.querySelectorAll('.navitem').forEach(n => {
      n.addEventListener('click', () => this.navigate(n.dataset.page));
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
      localStorage.removeItem('ks_token');
      this.user = null;
      this.showAuth();
    });

    // Modal close
    document.getElementById('modal-close').addEventListener('click', () => this.closeModal());
    document.getElementById('modal-overlay').addEventListener('click', e => {
      if (e.target === document.getElementById('modal-overlay')) this.closeModal();
    });
  },

  openModal(title, bodyHtml) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-overlay').classList.remove('hidden');
  },

  closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.getElementById('modal-body').innerHTML = '';
  },

  toast(msg, type = 'default') {
    let t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.textContent = msg;
    t.className = 'toast ' + (type === 'success' ? 'success' : type === 'error' ? 'error' : '');
    requestAnimationFrame(() => t.classList.add('show'));
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('show'), 3000);
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
