# GovAudit — Indonesian Government Website Budget Analyzer
> Sistem analisis anggaran website pemerintah Indonesia berbasis OSINT

---

## 🎯 Tentang Sistem

GovAudit menganalisis website pemerintah Indonesia secara otomatis untuk:
1. **Mendeteksi teknologi** yang digunakan (CMS, framework, CDN, library)
2. **Mengestimasi biaya wajar** pembangunan website berdasarkan fitur yang terdeteksi
3. **Membandingkan** dengan anggaran pengadaan aktual dari SIRUP LKPP
4. **Melabeli** hasil sebagai LEGIT / SUSPICIOUS / FRAUD

---

## 🔍 Studi Kasus: bgn.go.id

| Metrik | Nilai |
|--------|-------|
| **Estimasi Pasar Wajar** | Rp 1,075,000,000 (~1 Miliar) |
| **Anggaran Aktual (SIRUP)** | Rp 1,265,415,045,000 (~1.265 Triliun) |
| **Selisih** | **114,417%** |
| **Label** | 🚨 **FRAUD** |

### Temuan:
- Dua paket pengadaan IT BGN via **Penunjukan Langsung** tanpa tender terbuka
- Paket SIPGN: Rp 600 Miliar | Paket IoT 5.000 lokasi: Rp 665 Miliar
- **Tidak ada identitas vendor** yang tercantum di SPSE
- Melanggar **Perpres No. 12/2021** tentang Pengadaan Barang/Jasa
- Celios merekomendasikan investigasi **KPPU**
- Sumber: Tempo.co, IDNTimes (April 2025), SIRUP LKPP

---

## 🏗️ Arsitektur Sistem

```
govbudget/
├── server.py                          # HTTP Server (stdlib, no deps)
├── backend/
│   ├── models/
│   │   └── website_profile.py        # Data classes (WebsiteProfile, BudgetEstimate, etc.)
│   ├── scrapers/
│   │   └── website_scraper.py        # Web fetcher + HTML parser
│   └── analyzers/
│       ├── cost_estimation_engine.py # Core cost model (feature-based scoring)
│       ├── fraud_detection_engine.py # Fraud labeling + SIRUP data lookup
│       └── orchestrator.py           # Pipeline coordinator
└── frontend/
    └── index.html                    # Full UI (vanilla JS, no deps)
```

---

## 🚀 Cara Menjalankan

### Requirements
- Python 3.8+ (no external packages needed — pure stdlib)

### Run
```bash
cd govbudget
python3 server.py
# → http://localhost:8080
```

---

## 💡 Metodologi Estimasi Biaya

### Model: Feature-Based Weighted Scoring

Setiap fitur yang terdeteksi memiliki bobot biaya berdasarkan rate pasar Indonesia 2024:

| Komponen | Biaya Dasar |
|----------|------------|
| Design & UI/UX | Rp 15-27 juta |
| Frontend Development | Rp 20-70 juta |
| Backend Development | Rp 25-80 juta |
| CMS Integration | Rp 15-30 juta |
| Infrastruktur | Rp 12-50 juta |
| Per-subdomain | Rp 30 juta/domain |
| Project Management | 15% dari total |
| Testing & QA | 10% dari total |

### Multiplier

| Tipe Instansi | Multiplier |
|---------------|-----------|
| Kementerian | 2.5x |
| Badan Nasional | 2.0x |
| Lembaga | 1.8x |
| Provinsi | 1.6x |
| Kabupaten/Kota | 1.3x |
| Overhead Pengadaan Pemerintah | +35% |

### Fraud Thresholds
- **LEGIT**: Selisih < 30%
- **SUSPICIOUS**: Selisih 30-50%
- **FRAUD**: Selisih > 50%

---

## 📊 Data Sources (Open Data)

| Sumber | Akses |
|--------|-------|
| SIRUP LKPP | https://inaproc.lkpp.go.id |
| LPSE Nasional | https://spse.inaproc.id |
| Open Data Indonesia | https://data.go.id |
| BPS Salary Survey | https://bps.go.id |

---

## 🔮 Roadmap Pengembangan

### Phase 2 (Recommended)
- [ ] Integrasi API SIRUP LKPP secara real-time
- [ ] Database PostgreSQL untuk menyimpan riwayat analisis
- [ ] Machine learning model untuk deteksi anomali anggaran
- [ ] Crawler otomatis untuk semua K/L/D/I
- [ ] Export laporan PDF
- [ ] Dashboard perbandingan antar instansi

### Stack Rekomendasi untuk Production
- **Backend**: FastAPI (Python) + PostgreSQL + Redis
- **Frontend**: Next.js + TailwindCSS
- **ML**: scikit-learn / XGBoost untuk anomaly detection
- **Scraping**: Playwright (JS rendering) + rotating proxies
- **Data Pipeline**: Apache Airflow untuk crawling terjadwal
- **Deployment**: Docker + Kubernetes

---

## ⚠️ Disclaimer

Sistem ini adalah alat analisis OSINT berbasis estimasi teknis. Bukan pengganti audit resmi BPK atau KPK. Selalu verifikasi dengan dokumen pengadaan resmi. Label FRAUD dalam sistem ini berarti indikasi ketidakwajaran, bukan tuduhan hukum.

---

*Built with Python stdlib only — no external dependencies*
