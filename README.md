# Kripto Strateji — Kurulum & Deployment

## Proje Yapısı

```
kripto-strateji/
├── backend/
│   ├── main.py           # FastAPI uygulama
│   ├── database.py       # SQLite veritabanı
│   ├── auth_utils.py     # JWT + şifreleme
│   └── routers/
│       ├── auth.py       # Kayıt / giriş
│       ├── strategies.py # Strateji CRUD + backtest
│       ├── watchlist.py  # İzleme listesi
│       └── users.py      # Profil & ayarlar
├── frontend/
│   ├── templates/
│   │   └── index.html    # Ana SPA sayfası
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── api.js          # Backend + Binance API istemcisi
│           ├── chart-engine.js # SMA/RSI hesaplama ve grafik
│           ├── pages.js        # Sayfa bileşenleri
│           └── app.js          # Yönlendirme & auth
└── requirements.txt
```

---

## Yerel Kurulum

```bash
# 1. Repoyu klonla / klasörü aç
cd kripto-strateji

# 2. Python ortamı oluştur
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Sunucuyu başlat
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Tarayıcıda aç
# http://localhost:8000
```

---

## Ücretsiz Deployment Seçenekleri

### Seçenek 1: Railway (Önerilen — En kolay)

1. https://railway.app adresine git
2. "New Project" → "Deploy from GitHub repo"
3. Root dizinine `Procfile` ekle:
   ```
   web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Environment variable ekle: `SECRET_KEY=gizli-anahtar-buraya`
5. Deploy et — URL otomatik verilir

### Seçenek 2: Render

1. https://render.com → New Web Service
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Environment: `SECRET_KEY=...`

### Seçenek 3: VPS (DigitalOcean / Hetzner)

```bash
# Sunucuya bağlan
ssh root@sunucu-ip

# Repoyu klonla
git clone https://github.com/kullanici/kripto-strateji.git
cd kripto-strateji
pip install -r requirements.txt

# Nginx kurulumu (opsiyonel — HTTPS için)
apt install nginx certbot

# systemd servisi oluştur
cat > /etc/systemd/system/kripto.service << EOF
[Unit]
Description=Kripto Strateji
After=network.target

[Service]
WorkingDirectory=/root/kripto-strateji/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
Environment=SECRET_KEY=gizli-anahtar-buraya

[Install]
WantedBy=multi-user.target
EOF

systemctl enable kripto && systemctl start kripto
```

---

## Güvenlik Notları

- `SECRET_KEY` değerini mutlaka değiştir (en az 32 karakter rastgele string)
- Production'da HTTPS kullan (Let's Encrypt — ücretsiz)
- `database.py`'deki `DB_PATH` değerini kalıcı bir dizine ayarla

## API Dokümantasyonu

Sunucu çalışırken: http://localhost:8000/docs

---

## Özellikler

- ✅ Email + şifre ile kayıt / giriş (JWT token)
- ✅ Strateji oluşturma, düzenleme, silme
- ✅ Binance gerçek veri entegrasyonu (8 timeframe, 2 yıla kadar)
- ✅ SMA Crossover + RSI backtest motoru
- ✅ Backtest sonuçlarını kaydetme ve geçmişi görüntüleme
- ✅ Kişisel izleme listesi (canlı fiyatlarla)
- ✅ Kullanıcı profili ve tercihler
- ✅ Dark mode desteği
