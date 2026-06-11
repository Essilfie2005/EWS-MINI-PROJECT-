# 🎓 Dropout Early-Warning System (EWS)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![React](https://img.shields.io/badge/react-18.x-61dafb.svg)

An AI-powered Early Warning System designed for university foundation programs (specifically tailored for West African institutions). The system uses Machine Learning to predict student dropout risk in real-time, provides Explainable AI (XAI) to educators, and automates early interventions via SMS.

This project was built as a Mini Project by **Group 3**.

---

## ✨ Key Features

* **🤖 Predictive Machine Learning:** Utilises an **XGBoost** classifier with automated Hyperparameter Optimisation (via Optuna) to predict dropout risk.
* **🧠 Explainable AI (XAI):** Integrates **SHAP** (SHapley Additive exPlanations) to provide waterfall plots and feature-importance metrics, explaining *why* a specific student is at risk.
* **📱 Automated Interventions:** Connects to the **Africa's Talking API** to automatically send SMS alerts to at-risk students or their academic advisors.
* **☁️ Cloud-Native Architecture:** 100% cloud-ready. Serializes the trained ML models directly into a **Supabase PostgreSQL** database, ensuring data and models survive ephemeral server spins on free hosting tiers like Render.
* **🎨 Premium UI/UX:** A stunning, modern dashboard built with React and Vite, featuring glassmorphism, responsive mobile layouts, and a guided onboarding tutorial.

---

## 🛠️ Technology Stack

**Frontend:**
* React.js (Vite)
* Custom CSS (Glassmorphism & Responsive CSS Grid)
* Axios (API Communication)
* Recharts (Data Visualisation)
* Lucide React (Icons)

**Backend:**
* Python 3 & FastAPI (Asynchronous Web Framework)
* XGBoost & scikit-learn (Machine Learning Pipeline)
* Optuna (Hyperparameter Tuning)
* SHAP (Explainable AI)
* SQLAlchemy + Asyncpg (Database ORM)
* APScheduler (Background CRON Jobs)

**Infrastructure:**
* **Database:** Supabase (PostgreSQL)
* **Frontend Hosting:** Vercel (Recommended)
* **Backend Hosting:** Render (Recommended)

---

## 🚀 Deployment Instructions

### 1. Backend (Render)
1. Create a New Web Service on Render linked to this repository.
2. Set the Root Directory to `backend`.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5. Add your `DATABASE_URL` as an Environment Variable (use your Supabase connection string).

### 2. Frontend (Vercel)
1. Import this repository into Vercel.
2. Set the Root Directory to `frontend`.
3. Set the Framework Preset to `Vite`.
4. In Environment Variables, add `VITE_API_BASE_URL` and set it to your deployed Render URL (e.g., `https://your-backend.onrender.com/api`).

---

## 💻 Local Development Setup

If you want to run the project locally on your machine:

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/dropout-early-warning.git
cd dropout-early-warning
```

**2. Start the Backend**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # On Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Start the Frontend**
```bash
cd frontend
npm install
npm run dev
```

*Note: The local setup will automatically fall back to an SQLite file (`dropout.db`) if no PostgreSQL `DATABASE_URL` is provided, ensuring seamless local testing.*

---
*Built with ❤️ for student success.*
