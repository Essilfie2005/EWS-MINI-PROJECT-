import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
export const fetchRecentAlerts = () => api.get('/alerts/');
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

// ──── Alerts / SMS ──────────────────────────────
export const sendSMSAlert = (payload) => api.post('/interventions/send-sms', payload);
export const sendWhatsAppAlert = (payload) => api.post('/interventions/send-whatsapp', payload);
export const fetchAlertHistory = (params) => api.get('/alerts/', { params });
export const markAlertRead = (alertId) => api.patch(`/alerts/${alertId}/read`);
export const dismissAlert = (alertId) => api.patch(`/alerts/${alertId}/dismiss`);
export const markAllAlertsRead = () => api.post('/alerts/mark-all-read');

// ──── Interventions ─────────────────────────────
export const createIntervention = (payload) => api.post('/interventions/', payload);
export const updateIntervention = (id, payload) => api.put(`/interventions/${id}`, payload);
export const fetchInterventions = (params) => api.get('/interventions/', { params });
export const fetchInterventionStats = () => api.get('/students/stats/summary');
export const fetchStudentInterventions = (studentId) => api.get(`/interventions/student/${studentId}`);

// ──── Data Management ───────────────────────────
export const uploadCSV = (formData) =>
  api.post('/students/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const triggerRetrain = () => api.post('/predictions/train');
export const factoryReset = () => api.delete('/system/factory-reset');

// ──── Settings (client-side with API model info) ──
export const fetchSettings = () => {
  const saved = JSON.parse(localStorage.getItem('ews_settings') || '{}');
  const defaults = {
    risk_threshold: 0.5,
    sms_enabled: false,
    at_username: 'sandbox',
    at_api_key: '',
    at_sender_id: '',
    alert_cron_hour: 18,
    alert_cron_minute: 0,
  };
  return Promise.resolve({ data: { ...defaults, ...saved } });
};

export const updateSettings = (payload) => {
  localStorage.setItem('ews_settings', JSON.stringify(payload));
  return Promise.resolve({ data: payload });
};

export default api;

