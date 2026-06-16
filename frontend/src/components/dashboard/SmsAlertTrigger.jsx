import { useState } from 'react';
import { MessageSquare, Send, Loader2, CheckCircle2, X } from 'lucide-react';
import { sendSmsAlert, triggerBatchAlerts } from '../../services/api';
import { useToast } from '../../context/ToastContext';

/**
 * Can be used in two modes:
 *  1. standalone panel (no studentId) — batch-trigger alerts for all high-risk students
 *  2. single-student mode (studentId provided) — send a targeted SMS for one student
 */
export default function SmsAlertTrigger({ studentId = null, studentData = null, onSent }) {
  const addToast = useToast();
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const label = studentId ? 'Send SMS Alert' : 'Trigger Batch Alerts';

  const handleSend = async () => {
    setSending(true);
    setShowConfirm(false);
    try {
      if (studentId) {
        await sendSmsAlert({ student_id: parseInt(studentId, 10) });
        addToast(`SMS alert sent for student ${studentId}`, 'success');
      } else {
        await triggerBatchAlerts();
        addToast('Batch SMS alerts triggered for all high-risk students', 'success');
      }
      setSent(true);
      setTimeout(() => setSent(false), 4000);
      if (onSent) onSent();
    } catch (err) {
      const detail = err.response?.data?.detail;
      addToast(
        typeof detail === 'string' ? detail : 'SMS send failed — check Africa\'s Talking config',
        'error'
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button
        className={`btn btn-sm ${sent ? 'btn-success' : 'btn-secondary'}`}
        onClick={() => setShowConfirm(true)}
        disabled={sending}
        title={label}
      >
        {sending ? (
          <><Loader2 size={14} className="spin" /> Sending...</>
        ) : sent ? (
          <><CheckCircle2 size={14} /> Sent</>
        ) : (
          <><MessageSquare size={14} /> {label}</>
        )}
      </button>

      {/* Confirmation modal */}
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div
            className="modal-content slide-up"
            style={{ maxWidth: 420 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Send size={18} style={{ color: 'var(--accent)' }} />
                Confirm SMS Alert
              </h3>
              <button className="modal-close" onClick={() => setShowConfirm(false)}>
                <X size={16} />
              </button>
            </div>

            {studentId ? (
              <div style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
                Send an SMS alert to the counsellor assigned to{' '}
                <strong style={{ color: 'var(--text-primary)' }}>Student {studentId}</strong>?
                {studentData && (
                  <div style={{
                    marginTop: 12,
                    padding: '10px 14px',
                    background: 'rgba(244,63,94,0.08)',
                    borderRadius: 8,
                    border: '1px solid rgba(244,63,94,0.15)',
                    fontSize: 13,
                  }}>
                    <div style={{ color: '#f43f5e', fontWeight: 600, marginBottom: 4 }}>
                      Preview SMS
                    </div>
                    <div style={{ fontFamily: 'monospace', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      Student {studentId} flagged HIGH RISK.
                      {studentData.attendance_rate != null
                        ? ` Attendance: ${Number(studentData.attendance_rate).toFixed(0)}%.`
                        : ''}
                      {studentData.quiz_average != null
                        ? ` Quiz Avg: ${Number(studentData.quiz_average).toFixed(0)}%.`
                        : ''}
                      {' '}Please contact within 5 days.
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
                This will trigger SMS alerts via{' '}
                <strong style={{ color: 'var(--accent)' }}>Africa's Talking API</strong> for all
                currently high-risk and critical students that have not yet been alerted today.
              </div>
            )}

            <div className="modal-actions">
              <button className="btn btn-secondary btn-sm" onClick={() => setShowConfirm(false)}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleSend}>
                <Send size={14} /> Confirm Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
