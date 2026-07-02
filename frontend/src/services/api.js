import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ──── Auth ──────────────────────────────────────────────────────────
export const login = (username, password) =>
  axios.post(`${API_BASE}/auth/login`, { username, password });

export const logout = () => {
  localStorage.removeItem('ews_token');
  localStorage.removeItem('ews_user');
};

// Request interceptor — attach auth token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('ews_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — unified error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;
      if (status === 401) {
        localStorage.removeItem('ews_token');
      }
    }
    return Promise.reject(error);
  }
);

// ──── Dashboard ─────────────────────────────────
export const fetchDashboardOverview = () => api.get('/dashboard/summary');
export const fetchRiskDistribution = () => api.get('/dashboard/risk-distribution');
export const fetchHeatmapData = () => api.get('/students/');
export const fetchCohortTrend = () => api.get('/dashboard/model-metrics');
export const fetchHealthCheck = () => api.get('/dashboard/health');
export const fetchFeatureImportance = () => api.get('/dashboard/feature-importance');

// ──── Students ──────────────────────────────────
export const fetchStudents = (params) => api.get('/students/', { params });
export const fetchStudentDetail = (id) => api.get(`/students/${id}`);
export const fetchStudentByAnon = (anonId) => api.get(`/students/anon/${anonId}`);
export const fetchStudentStats = () => api.get('/students/stats/summary');

// ──── Predictions ───────────────────────────────
export const triggerBatchPrediction = () => api.post('/predictions/predict-batch');
export const triggerSinglePrediction = (payload) => api.post('/predictions/predict', payload);
export const triggerTraining = () => api.post('/predictions/train');
export const fetchModelInfo = () => api.get('/predictions/model-info');
export const fetchPredictionHistory = (studentId) => api.get(`/predictions/history/${studentId}`);
export const generateSyntheticData = () => api.post('/predictions/generate-synthetic');
export const generateBeeswarm = () => api.post('/predictions/generate-beeswarm');
export const generateShapBatch = () => api.post('/predictions/generate-shap-batch', {}, { timeout: 600000 });

// ──── Interventions ─────────────────────────────
export const createIntervention = (payload) => api.post('/interventions/', payload);
export const updateIntervention = (id, payload) => api.put(`/interventions/${id}`, payload);
export const fetchInterventions = (params) => api.get('/interventions/', { params });
export const fetchStudentInterventions = (studentId) => api.get(`/interventions/student/${studentId}`);

// ──── Alerts ────────────────────────────────────────────────────────
export const fetchAlerts = (params) => api.get('/alerts/', { params });
export const markAlertRead = (id) => api.patch(`/alerts/${id}/read`);
export const markAllAlertsRead = () => api.post('/alerts/mark-all-read');
export const sendSmsAlert = (payload) => api.post('/alerts/send', payload);
export const triggerBatchAlerts = () => api.post('/alerts/trigger-batch');

// ──── Analytics ──────────────────────────────────────────────────────
export const fetchRocCurve = () => api.get('/dashboard/roc-curve');
export const fetchBeeswarmData = () => api.get('/dashboard/beeswarm');
export const fetchPilotMetrics = () => api.get('/dashboard/pilot-metrics');

// ──── Data Management ───────────────────────────
export const uploadCSV = (formData) =>
  api.post('/students/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const factoryReset = () => api.delete('/system/factory-reset');

// ──── Settings (client-side with API model info) ──
export const fetchSettings = () => {
  const saved = JSON.parse(localStorage.getItem('ews_settings') || '{}');
  const defaults = {
    risk_threshold: 0.5,
  };
  return Promise.resolve({ data: { ...defaults, ...saved } });
};

export const updateSettings = (payload) => {
  localStorage.setItem('ews_settings', JSON.stringify(payload));
  return Promise.resolve({ data: payload });
};

export default api;
