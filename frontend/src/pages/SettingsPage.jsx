import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Sliders,
  Database,
  Upload,
  RefreshCw,
  Save,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  PlayCircle,
} from 'lucide-react';
import { fetchSettings, updateSettings, uploadCSV, factoryReset } from '../services/api';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

export default function SettingsPage() {
  const addToast = useToast();
  const fileRef = useRef(null);

  const [settings, setSettings] = useState({ risk_threshold: 0.5 });
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [retrainResult, setRetrainResult] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [predicting, setPredicting] = useState(false);

  const handleFactoryReset = async () => {
    setResetting(true);
    try {
      await factoryReset();
      addToast('Factory reset completed successfully', 'success');
      setShowResetModal(false);
    } catch (err) {
      const detail = err.response?.data?.detail;
      addToast(typeof detail === 'string' ? detail : 'Factory reset failed', 'error');
    } finally {
      setResetting(false);
    }
  };

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSettings();
      if (res.data) {
        setSettings((prev) => ({ ...prev, ...res.data }));
      }
    } catch (err) {
      // settings are stored locally — don't block the page on failure, just use defaults
      console.warn('Could not load settings, using defaults:', err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings(settings);
      addToast('Settings saved successfully', 'success');
    } catch (err) {
      const detail = err.response?.data?.detail;
      addToast(typeof detail === 'string' ? detail : 'Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input immediately so the same file can be re-selected after an error
    if (fileRef.current) fileRef.current.value = '';

    const allowed = ['.csv', '.pdf', '.doc', '.docx'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      addToast('Please upload a CSV, PDF, or Word (.docx) file', 'error');
      return;
    }

    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await uploadCSV(formData);
      const result = res.data;
      setUploadResult(result);
      const count = (result.inserted || 0) + (result.updated || 0);
      addToast(`✅ ${count} students processed (${result.inserted || 0} new, ${result.updated || 0} updated)`, 'success');

      // Fire predictions in background — don't block UI
      setPredicting(true);
      addToast('Scoring students in background — check Students page shortly...', 'info');
      api.post('/predictions/predict-batch', { student_ids: null }, { timeout: 600000 })
        .then(() => {
          addToast('✅ Risk scores generated! Refresh the Students page.', 'success');
          setPredicting(false);
        })
        .catch(() => {
          addToast('Scoring may still be running. Check Students page in a minute.', 'warning');
          setPredicting(false);
        });
    } catch (err) {
      // Friendly message when backend is simply not running
      if (!err.response) {
        addToast('Cannot reach backend — make sure the server is running on port 8000.', 'error');
      } else {
        const detail = err.response?.data?.detail;
        const msg = typeof detail === 'string' ? detail
          : Array.isArray(detail) ? detail.map(d => d.msg || JSON.stringify(d)).join('; ')
          : `Upload failed (${err.response.status})`;
        addToast(msg, 'error');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainResult(null);
    addToast('Model training started — this takes 1-2 minutes. You can navigate away.', 'info');

    // Fire training in background
    api.post('/predictions/train', {}, { timeout: 600000 })
      .then((res) => {
        const result = res.data;
        setRetrainResult(result);
        setRetraining(false);
        addToast(`✅ Model trained! AUC: ${result.metrics?.auc_roc?.toFixed(3) || 'N/A'}`, 'success');

        // Now score all students with new model
        setPredicting(true);
        addToast('Scoring all students with new model...', 'info');
        return api.post('/predictions/predict-batch', { student_ids: null }, { timeout: 600000 });
      })
      .then(() => {
        addToast('✅ All students scored! Refresh the Students page.', 'success');
        setPredicting(false);
      })
      .catch((err) => {
        const detail = err.response?.data?.detail;
        const msg = typeof detail === 'string' ? detail
          : Array.isArray(detail) ? detail.map(d => d.msg || JSON.stringify(d)).join('; ')
          : 'Training may still be running. Check back in a minute.';
        addToast(msg, 'warning');
        setRetraining(false);
        setPredicting(false);
      });
  };

  return (
    <div className="fade-in" style={{ maxWidth: 720 }}>
      {/* Risk Threshold */}
      <div className="glass-card slide-up settings-section">
        <h3 className="settings-section-title">
          <Sliders size={18} /> Risk Threshold Configuration
        </h3>

        <div className="settings-row">
          <div className="settings-row-info">
            <span className="settings-row-label">Risk Classification Threshold</span>
            <span className="settings-row-desc">
              Students with a predicted probability above this threshold are flagged as at-risk.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <input
              type="range"
              className="range-slider"
              min="0"
              max="1"
              step="0.05"
              value={settings.risk_threshold}
              onChange={(e) =>
                setSettings({ ...settings, risk_threshold: parseFloat(e.target.value) })
              }
            />
            <span
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: 'var(--accent)',
                minWidth: 48,
                textAlign: 'right',
              }}
            >
              {settings.risk_threshold.toFixed(2)}
            </span>
          </div>
        </div>

      </div>

      {/* Data Management */}
      <div className="glass-card slide-up stagger-3 settings-section">
        <h3 className="settings-section-title">
          <Database size={18} /> Data Management
        </h3>

        <div className="settings-row">
          <div className="settings-row-info">
            <span className="settings-row-label">Upload Week 6 Cohort Data</span>
            <span className="settings-row-desc">
              Upload the entire foundation-year cohort at Week 6. Accepts <strong>CSV, PDF, or Word (.docx)</strong>.<br />
              <strong>Required:</strong> student_id (8 digits) · index_number (7 digits) · mid_sem_result (out of 30)<br />
              <strong>Optional but recommended:</strong> attendance_rate (%) · end_sem_result (out of 70)
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.pdf,.doc,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,text/csv"
              onChange={handleUpload}
              style={{ display: 'none' }}
            />
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => fileRef.current?.click()}
              disabled={uploading || predicting}
            >
              {uploading ? (
                <><Loader2 size={14} className="spin" /> Uploading...</>
              ) : predicting ? (
                <><Loader2 size={14} className="spin" /> Scoring...</>
              ) : (
                <><Upload size={14} /> Upload File</>
              )}
            </button>
          </div>
        </div>

        {/* Upload Result */}
        {uploadResult && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 8,
            padding: '12px 16px',
            marginTop: 8,
            fontSize: 13,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontWeight: 600 }}>
              <CheckCircle2 size={16} /> Upload Complete
            </div>
            <div style={{ color: 'var(--text-secondary)', marginTop: 6 }}>
              {uploadResult.inserted} students inserted · {uploadResult.updated || 0} updated · {uploadResult.total_rows} total rows processed
            </div>
          </div>
        )}

        <div className="settings-row" style={{ marginTop: 16 }}>
          <div className="settings-row-info">
            <span className="settings-row-label">Re-train Prediction Model</span>
            <span className="settings-row-desc">
              Trains XGBoost with Optuna HPO on all student data. Takes 1-2 minutes. Automatically scores all students after training.
            </span>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleRetrain}
            disabled={retraining || predicting}
          >
            {retraining ? (
              <><Loader2 size={14} className="spin" /> Training...</>
            ) : predicting ? (
              <><Loader2 size={14} className="spin" /> Scoring...</>
            ) : (
              <><RefreshCw size={14} /> Re-train</>
            )}
          </button>
        </div>

        {/* Retrain Result */}
        {retrainResult && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 8,
            padding: '12px 16px',
            marginTop: 8,
            fontSize: 13,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontWeight: 600 }}>
              <CheckCircle2 size={16} /> Model Trained — {retrainResult.model_version}
            </div>
            <div style={{ color: 'var(--text-secondary)', marginTop: 6, display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px 24px' }}>
              <span>AUC-ROC: <strong>{retrainResult.metrics?.auc_roc?.toFixed(4)}</strong></span>
              <span>F1 Score: <strong>{retrainResult.metrics?.f1_score?.toFixed(4)}</strong></span>
              <span>Accuracy: <strong>{(retrainResult.metrics?.accuracy * 100)?.toFixed(1)}%</strong></span>
              <span>Precision: <strong>{retrainResult.metrics?.precision?.toFixed(4)}</strong></span>
              <span>Recall: <strong>{retrainResult.metrics?.recall?.toFixed(4)}</strong></span>
              <span>Cohen κ: <strong>{retrainResult.metrics?.cohen_kappa?.toFixed(4)}</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* System Tutorial */}
      <div className="glass-card slide-up stagger-4 settings-section">
        <h3 className="settings-section-title">
          <PlayCircle size={18} /> System Tutorial
        </h3>
        <div className="settings-row">
          <div className="settings-row-info">
            <span className="settings-row-label">Restart Onboarding Tutorial</span>
            <span className="settings-row-desc">
              Reset your tutorial progress and launch the Welcome modal. This is great for showing off the system to new stakeholders!
            </span>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              localStorage.removeItem('ews_tutorial_seen');
              window.location.reload();
            }}
          >
            <PlayCircle size={14} /> Restart Tutorial
          </button>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="glass-card slide-up stagger-5 settings-section" style={{ borderColor: 'rgba(239, 68, 68, 0.3)' }}>
        <h3 className="settings-section-title" style={{ color: '#ef4444' }}>
          <AlertTriangle size={18} /> Danger Zone
        </h3>
        <div className="settings-row">
          <div className="settings-row-info">
            <span className="settings-row-label" style={{ color: '#ef4444' }}>Factory Reset System</span>
            <span className="settings-row-desc">
              Permanently delete all students, predictions, and intervention logs. Settings will be preserved.
            </span>
          </div>
          <button
            className="btn btn-sm"
            style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}
            onClick={() => setShowResetModal(true)}
            disabled={resetting}
          >
            {resetting ? <Loader2 size={14} className="spin" /> : <AlertTriangle size={14} />} Factory Reset
          </button>
        </div>
      </div>

      {/* Save Button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? (
            <><Loader2 size={14} className="spin" /> Saving...</>
          ) : (
            <><Save size={14} /> Save Settings</>
          )}
        </button>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetModal && (
        <div className="modal-overlay">
          <div className="modal-content slide-up" style={{ maxWidth: 400, borderColor: 'rgba(239, 68, 68, 0.3)' }}>
            <div className="modal-header">
              <h3 style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertTriangle size={20} /> Confirm Factory Reset
              </h3>
            </div>
            <div className="modal-body">
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Are you absolutely sure you want to perform a factory reset? 
                This will <strong>permanently delete</strong> all students, predictions, alerts, and intervention logs.
              </p>
              <p style={{ color: 'var(--text-secondary)', marginTop: 12, lineHeight: 1.5 }}>
                Your settings (Risk Threshold) will be preserved. This action cannot be undone.
              </p>
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowResetModal(false)}
                disabled={resetting}
              >
                Cancel
              </button>
              <button 
                className="btn" 
                style={{ backgroundColor: '#ef4444', color: '#fff' }}
                onClick={handleFactoryReset}
                disabled={resetting}
              >
                {resetting ? <Loader2 size={16} className="spin" /> : 'Yes, Delete Everything'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
