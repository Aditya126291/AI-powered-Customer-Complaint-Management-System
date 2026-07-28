import { useEffect, useState } from 'react';
import { deleteSavedComplaint, fetchSavedComplaints, type SavedComplaintRecord } from '../features/copilot/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function SavedComplaintsModal({ isOpen, onClose }: Props) {
  const [records, setRecords] = useState<SavedComplaintRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<SavedComplaintRecord | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchSavedComplaints();
      setRecords(data);
    } catch {
      // Ignore error for fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      void loadData();
    }
  }, [isOpen]);

  const handleDelete = async (id: number) => {
    try {
      await deleteSavedComplaint(id);
      if (selected?.id === id) setSelected(null);
      void loadData();
    } catch {
      // Ignore
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <div>
            <h2>📁 Saved QMS Complaints Ledger</h2>
            <p>Database records persisted from customer complaint intake</p>
          </div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </header>

        <div className="modal-body">
          {loading ? (
            <div className="loading-state">Loading complaints from database...</div>
          ) : records.length === 0 ? (
            <div className="empty-ledger">
              <p>No complaints saved in the database yet.</p>
              <small>Use the AI Copilot to log a complaint and click "Save complaint" to commit to the QMS database.</small>
            </div>
          ) : (
            <div className="ledger-grid">
              <div className="records-list">
                {records.map((r) => (
                  <div
                    key={r.id}
                    className={`record-item ${selected?.id === r.id ? 'active' : ''}`}
                    onClick={() => setSelected(r)}
                  >
                    <div className="record-top">
                      <span className="rec-num">{r.complaintNumber}</span>
                      <span className={`severity-badge ${r.severity.toLowerCase()}`}>{r.severity || 'Normal'}</span>
                    </div>
                    <strong className="rec-product">{r.productName || 'Unspecified Product'}</strong>
                    <div className="rec-sub">
                      <span>Batch: {r.batchLotNumber || 'N/A'}</span>
                      <span>Customer: {r.customerName || 'N/A'}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="record-details">
                {selected ? (
                  <div className="details-card">
                    <div className="details-header">
                      <h3>{selected.complaintNumber}</h3>
                      <button className="delete-btn" onClick={() => handleDelete(selected.id)}>Delete Record</button>
                    </div>
                    <table className="details-table">
                      <tbody>
                        <tr><td>Customer:</td><td>{selected.customerName || '-'}</td></tr>
                        <tr><td>Source:</td><td>{selected.complaintSource || '-'}</td></tr>
                        <tr><td>Product:</td><td>{selected.productName || '-'}</td></tr>
                        <tr><td>Strength/Grade:</td><td>{selected.strengthGrade || '-'}</td></tr>
                        <tr><td>Batch/Lot:</td><td>{selected.batchLotNumber || '-'}</td></tr>
                        <tr><td>Mfg Date:</td><td>{selected.manufacturingDate || '-'}</td></tr>
                        <tr><td>Expiry Date:</td><td>{selected.expiryDate || '-'}</td></tr>
                        <tr><td>Quantity:</td><td>{selected.affectedQuantity || '-'}</td></tr>
                        <tr><td>Site/Block:</td><td>{selected.originatingSite || '-'}</td></tr>
                        <tr><td>Defect Type:</td><td>{selected.complaintType || '-'}</td></tr>
                        <tr><td>Defect Summary:</td><td>{selected.defectSummary || '-'}</td></tr>
                        <tr><td>Risk Assessment:</td><td>{selected.riskAssessment || '-'}</td></tr>
                        <tr><td>Status:</td><td><span className="status-tag">{selected.status}</span></td></tr>
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="select-prompt">Select a complaint from the list to view complete details.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
