<<<<<<< HEAD
# NeuroCloud — AI-Based Cloud Anomaly Detection Platform

MCA Major Project — full-stack cloud monitoring platform: public marketing site,
role-based user/admin dashboards, live simulated telemetry, a 4-algorithm ML
detection pipeline with model comparison, predictions, recommendations,
alerts, and CSV/Excel/PDF reporting.

## Phase Progress

- [x] **Phase 1** — Project scaffold, database models, authentication (register / login /
      forgot-password / reset-password / email verification), role-based access control,
      base dashboard shell, admin user management, design system
- [x] **Phase 2** — Cloud server management (CRUD), real-time simulated metrics
      (auto-refreshing every 5s), live dashboard charts, per-server monitoring view
- [x] **Phase 3** — AI/ML: dataset upload, model training & comparison (Isolation Forest,
      One-Class SVM, Random Forest, Decision Tree), automatic best-model activation,
      confusion matrix + feature importance display, live anomaly detection engine
- [x] **Phase 4** — Prediction module (24h forecast + failure probability), rule-based
      recommendation engine, in-app alerts with unread badge, CSV/Excel/PDF report generation
- [x] **Phase 5 (partial)** — Analytics dashboard (severity/type breakdown, top affected
      servers, fleet averages), professional royal-blue/cyan color system with dark/light
      mode toggle. System/audit logs viewer was already in Phase 1.

**Not yet built** (flagged honestly rather than faked): JWT token auth (session-based
Flask-Login auth is implemented and is what protects every route — JWT would only
matter if you're exposing a separate token-authenticated REST API for a mobile app or
third-party integration), global cross-entity search, automated test suite, ROC curve
plotting (ROC-AUC score is computed and shown, but the curve itself isn't rendered),
CPU/Memory/Disk/Network *trend* charts specifically on the admin dashboard (per-server
trend charts exist on the server detail and monitoring pages).

## Quick Start (local, SQLite — zero setup)

```bash
cd neurocloud
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit SECRET_KEY, mail settings, etc.

python create_admin.py          # creates database + an admin account
python run.py                   # visit http://localhost:5000
```

Admin login defaults to `admin@neurocloud.app` / `Admin@12345` (change via
`ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` before running `create_admin.py`).

**First steps after logging in as admin:**
1. Go to **My Servers → Add Server** — this seeds 24h of realistic historical metrics.
2. Go to **Model Training → Train All 4 Models** — trains and auto-activates the best one.
3. Go to **AI Detection → Run Detection Now** — flags anomalies and generates recommendations.
4. Go to **Resource Monitoring** to watch live-updating charts (auto-refresh every 5s).
5. Register a second account (in an incognito window) to see the non-admin experience —
   regular users only see their own servers/alerts/reports and are blocked from `/admin`.

## Switching to MySQL

By default the app uses a local SQLite file at `database/neurocloud.db` so
it runs with no external setup. For your final submission/deployment:

1. Create a MySQL database: `CREATE DATABASE neurocloud;`
2. In `.env`, uncomment and set:
   ```
   DATABASE_URL=mysql+pymysql://root:password@localhost:3306/neurocloud
   ```
3. Re-run `python create_admin.py` to create tables in MySQL.

## What's implemented

**Auth & access control**
- Registration, login, logout, forgot/reset password (Flask-Mail), email verification,
  profile editing, change password — all CSRF-protected (Flask-WTF), hashed passwords
- Role-based access control (`@admin_required`) — verified: non-admins get a 403 on every
  admin-only route and API endpoint
- Audit logging (`SystemLog`) on register/login/logout/server changes/training/admin actions

**Cloud monitoring**
- Full server CRUD (add/edit/delete), per-server alert thresholds, 11 tracked metrics
  (CPU, memory, disk, disk I/O, network throughput/latency, packet loss, bandwidth,
  response time, error rate, request rate) plus availability, uptime, temperature and
  power consumption simulations
- Live monitoring: a `/monitoring/api/tick` endpoint advances the simulation and the
  dashboard polls it every 5 seconds, updating stat cards and Chart.js line charts in place

**AI / ML**
- Trains and compares 4 algorithms in one pass: Isolation Forest, One-Class SVM (both
  unsupervised), Random Forest, Decision Tree (both supervised) — on a chronological
  train/test split so nothing future leaks into training
- Reports accuracy, precision, recall, F1, ROC-AUC, confusion matrix, and feature
  importance (for the two supervised models) per model; automatically activates the
  highest-F1 model, with a manual override available
- Detection engine scores recent metrics with the active model, creates `Anomaly` rows,
  and triggers both the recommendation engine and an in-app `Alert`
- Prediction module trains a quick RandomForest regressor per server on demand to
  forecast CPU/memory/disk 24h out, plus a heuristic failure-probability score

**Operational features**
- Rule-based recommendation engine (CPU saturation → scale VM, memory leak → increase
  RAM, disk saturation → clean disk / increase storage, network anomaly → investigate
  security threat, etc.)
- Alerts with unread-count badge in the sidebar, mark-as-read
- Reports: generate and download CSV, Excel (openpyxl), and PDF (ReportLab) anomaly
  reports; report history per user
- Analytics dashboard: severity/type breakdown charts, fleet-wide resource averages,
  top-5 affected servers (7-day window)

**Design**
- Palette: Primary `#2563EB`, Secondary `#3B82F6`, Accent `#06B6D4`, Success `#22C55E`,
  Warning `#F59E0B`, Danger `#EF4444`, dark background `#0F172A` / card `#1E293B`,
  light background `#F8FAFC`, text `#E2E8F0`, hover `#60A5FA` — all as CSS custom
  properties in `app/static/css/design-system.css`
- Dark/light mode toggle (topbar button, persisted via `localStorage`, applied before
  first paint to avoid a flash of the wrong theme)
- Space Grotesk (display) + Inter (body) + JetBrains Mono (data readouts) type system

Every module above was exercised end-to-end via automated curl-driven test scripts
(register → login → add server → seed history → live tick → train 4 models → run
detection → view recommendations → check alerts → generate + download all 3 report
formats → predictions API → analytics API → role-restriction checks) before delivery,
with zero server errors in the logs.

## Folder Structure

```
neurocloud/
├── app/
│   ├── models/         # SQLAlchemy models (User, CloudServer, CloudMetric, Anomaly,
│   │                     Alert, Recommendation, Dataset, MLModel, Prediction, Report, SystemLog)
│   ├── routes/          # Blueprints: main, auth, dashboard, admin, servers, monitoring,
│   │                     ai, alerts, reports, analytics
│   ├── services/         # metrics_simulator, ml_engine, anomaly_engine,
│   │                     recommendation_engine, prediction_engine, report_engine
│   ├── templates/        # Jinja2 templates, one folder per module
│   ├── static/           # CSS (design-system.css), JS (theme.js + inline per-page scripts)
│   ├── ml_models/saved/  # Trained model + scaler artifacts (joblib)
│   └── utils/             # decorators, email, audit logging
├── config/                 # Dev/Prod/Testing config, SQLite fallback + MySQL support
├── database/                # SQLite file lives here in dev
├── uploads/ datasets/ reports/ logs/
├── requirements.txt
├── run.py
└── create_admin.py
```

## Known limitations (flagged honestly)

- Datasets/trained models are shared across all users (a shared sandbox), while
  detection *results*, alerts, and reports are scoped per user — a real production
  version would isolate data per organization/account.
- Email sending (verification, password reset, alert emails) uses Flask-Mail; with no
  SMTP credentials configured it fails silently (wrapped in try/except) — set
  `MAIL_SERVER`/`MAIL_USERNAME`/`MAIL_PASSWORD` in `.env` to enable real delivery, or
  leave `MAIL_SUPPRESS_SEND=True` for local development.
- No automated test suite yet (the `tests/` folder is scaffolded but empty) — all
  verification so far has been manual/scripted end-to-end testing, not pytest.
=======
# -Cloud-_Anomoly-Detection-_Plateform
loud Anomaly Detection is an AI/ML-based system designed to identify unusual or abnormal behavior in cloud infrastructure. It continuously analyzes infrastructure metrics such as CPU utilization, memory usage, disk usage, network traffic, response time, and resource consumption to detect patterns that may indicate performance issues, failures, 
>>>>>>> 865b920fd6bc00c29646e58c8ab2c72cbe8b9df9
