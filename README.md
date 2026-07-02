# Lightweight Dropout Prediction and Early Warning System (EWS)
> **Explainable AI for University Foundation Programs in Ghana**  
> CS Department | 2026 Batch Mini-Project | Group 3

---

## 🎯 Project Overview

This system identifies at-risk foundation-year students by **Week 6 of semester** using only five registry-available features — no LMS telemetry, no paid cloud services. It combines an **XGBoost classifier** with **SHAP explainability** to give counsellors plain-language briefs on why a student was flagged, and logs all interventions for tracking.

**AUC-ROC: 0.997** (XGBoost) vs 0.753 (Rule-based) on 2,000 student records.

---

## 👥 Group Members

| # | Index No. | Name | Role |
|---|-----------|------|------|
| 1 | 9019123 | Fobi Osei Randy Yamoah | ML / Data Engineer |
| 2 | 9018323 | Angela Essein | Backend / Systems Dev |
| 3 | 9019523 | Frank Fatawu Bakuwale Techi Junior | Frontend / Mobile Dev |
| 4 | 9019323 | Fosu Kwame Korletey | Analytics / XAI Lead |
| 5 | 9018623 | Essilfie David Amoabeng (PM) | EdTech / Pedagogy & PM |

---

## 🏗️ System Architecture

```
University Registry (CSV)
        │
        ▼
Python ETL Pipeline  ←── CTGAN Synthetic Data (500 records)
(SHA-256 anonymisation, feature engineering, imputation)
        │
        ▼
  SQLite Database
(students, predictions, interventions, alerts)
        │
        ├──► XGBoost Classifier (Optuna HPO) ──► Risk Score (0–1)
        │           │
        │           ▼
        │    SHAP TreeExplainer ──► Waterfall Charts + Beeswarm
        │
        ▼
  FastAPI REST API (async, APScheduler nightly job)
        │
        ▼
  React Dashboard (university LAN, no internet required)
  ├── Risk Heatmap (cohort overview)
  ├── Student Drill-Down (SHAP waterfall)
  ├── Analytics Page (ROC curve, Beeswarm, Pilot Metrics)
  ├── Interventions Log
  └── Settings (upload data, re-train model)
```

**Deployment:** University server or Raspberry Pi 4 (8GB RAM). Zero paid cloud dependency.

---

## ⚙️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11.8 |
| ML Classifier | XGBoost + Optuna HPO | 2.0.3 / 3.4.0 |
| Explainability | SHAP TreeExplainer | 0.44.0 |
| Synthetic Data | CTGAN (SDV) | 1.9.0 |
| Backend API | FastAPI + SQLAlchemy | 0.110.0 |
| Database | SQLite (dev) / PostgreSQL (prod) | — |
| Frontend | React 18 + Vite + Recharts | 18.2 |
| Dataset | OULAD (Open University Learning Analytics) | Public |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Clone the repository
```bash
git clone https://github.com/Essilfie2005/EWS-MINI-PROJECT-.git
cd EWS-MINI-PROJECT-
```

### 2. Start the Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend will automatically:
- Initialise the SQLite database
- Download and seed the OULAD dataset (first run only, ~2 min)
- Load the pre-trained XGBoost model

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 4. Login
| Username | Password | Role |
|----------|----------|------|
| `admin` | `ews2024` | Administrator |
| `counsellor` | `ews2024` | Counsellor |

---

## 📊 Key Features

### Dashboard
- **Risk Heatmap** — colour-coded grid of all students (green/amber/red/critical)
- **Cohort Summary** — total students, flagged count, average risk score
- **Feature Importance** — XGBoost gain-based importance chart

### Students Page
- Search, sort, and filter by risk band
- Click any student to open their full risk profile

### Student Detail Page
- **SHAP Waterfall Chart** — click "Generate Explanation" to see exactly which features drove the risk score
- **Intervention Logging** — record counsellor contact, type, and outcome
- **Risk History** — track how a student's risk score changes over time

### Analytics Page
- **ROC Curve** — XGBoost vs Logistic Regression vs Rule-based comparison
- **SHAP Beeswarm** — cohort-level feature impact summary
- **Pilot Metrics** — AUC-ROC, intervention conversion rate, usability score

### Settings Page
- **Upload Week 6 Cohort Data** (CSV)
- **Re-train Model** — runs Optuna HPO for 100 trials, auto-scores all students
- **Generate SHAP Explanations** — pre-computes SHAP for all students (populates Beeswarm chart)
- **Factory Reset** — clears all student data

---

## 🔬 Model Performance

| Metric | XGBoost | Logistic Regression | Rule-based |
|--------|---------|-------------------|------------|
| AUC-ROC | **0.997** | 0.997 | 0.753 |
| Training Data | OULAD (2,000 students) | — | — |
| Features | 5 registry features | — | attendance < 60% AND quiz < 40% |

The 5 input features:
1. `attendance_rate` — % of classes attended
2. `quiz_average` — average quiz score
3. `assignment_submission_rate` — % of assignments submitted
4. `mobile_engagement_freq` — mobile login frequency
5. `financial_aid_status` — IMD band (financial vulnerability indicator)

---

## 📁 Project Structure

```
dropout-early-warning/
├── backend/
│   ├── app/
│   │   ├── routers/          # API endpoints (students, predictions, dashboard, auth)
│   │   ├── services/         # ML pipeline, SHAP, CTGAN, scheduler
│   │   ├── models/           # SQLAlchemy ORM models + Pydantic schemas
│   │   ├── utils/            # OULAD seeding, metrics, anonymisation
│   │   ├── main.py           # FastAPI app factory
│   │   ├── config.py         # Settings (env vars)
│   │   └── database.py       # Async SQLAlchemy engine
│   ├── saved_models/         # Trained XGBoost model + scaler
│   ├── plots/                # SHAP waterfall PNGs
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, Students, Analytics, Settings, Login
│   │   ├── components/       # Layout, shared UI, dashboard widgets
│   │   ├── services/api.js   # Axios API client
│   │   └── context/          # Toast notifications
│   └── package.json
└── README.md
```

---

## 🔒 Ethics & Privacy

- All student IDs are **SHA-256 salted hashed** before storage
- No personally identifiable information (PII) is stored
- Compliant with the **Ghana Data Protection Act 2012**
- CTGAN synthetic records are clearly flagged in the database
- Counsellors log voluntary participation; logs deleted after 12 months

---

## 📄 Supervisor

**Mr. Eric Opoku Osei** | Expected Completion: Mid-July 2026

---

## 📜 Licence

MIT Licence — open for replication by any Ghanaian university.
