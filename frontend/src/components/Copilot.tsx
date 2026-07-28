import { useRef, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { applyPatch, resetForm } from '../features/complaint/complaintSlice';
import { processComplaint, uploadComplaint, type AiResponse } from '../features/copilot/api';
import { addMessage, resetChat, setAiResult, setProcessing } from '../features/copilot/copilotSlice';

export function Copilot() {
  const dispatch = useAppDispatch();
  const [draft, setDraft] = useState('');
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const { messages, processing, missingFields, risk, rootCause, capaRecommendations } = useAppSelector((s) => s.copilot);
  const form = useAppSelector((s) => s.complaint.form);

  const hasFormContent = Boolean(
    form.productName || form.customerName || form.batchLotNumber || form.defectSummary || messages.length > 1
  );

  const applyAiResult = (result: AiResponse) => {
    dispatch(applyPatch(result.patch));
    dispatch(setAiResult(result));
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: result.message }));
  };

  const submit = async () => {
    const text = draft.trim();
    if (!text || processing) return;
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text }));
    setDraft('');
    dispatch(setProcessing(true));
    try {
      applyAiResult(await processComplaint(text, form));
    } catch (error) {
      dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: error instanceof Error ? error.message : 'Something went wrong.' }));
    } finally {
      dispatch(setProcessing(false));
    }
  };

  const upload = async (file?: File) => {
    if (!file || processing) return;
    if (file.size > 10 * 1024 * 1024) {
      dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: 'This file is larger than the 10 MB upload limit.' }));
      return;
    }
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text: `Uploaded complaint document: ${file.name}` }));
    dispatch(setProcessing(true));
    try {
      applyAiResult(await uploadComplaint(file, form));
    } catch (error) {
      dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: error instanceof Error ? error.message : 'The document could not be processed.' }));
    } finally {
      dispatch(setProcessing(false));
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  // Quick Action Button Handlers
  const handleSummarize = () => {
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text: 'Summarize the complaint' }));
    const summaryText = `📋 COMPLAINT EXECUTIVE SUMMARY:\n` +
      `• Customer: ${form.customerName || 'Pending identification'}\n` +
      `• Product: ${form.productName || 'Pharmaceutical Product'} ${form.strengthGrade ? `(${form.strengthGrade})` : ''}\n` +
      `• Batch Number: ${form.batchLotNumber || 'Not specified'}\n` +
      `• Affected Quantity: ${form.affectedQuantity || 'Not specified'}\n` +
      `• Reported Defect: ${form.defectSummary || 'Quality deviation under evaluation'}\n` +
      `• Initial Triage: ${form.severity || 'Medium'} Severity | ${form.priority || 'High'} Priority`;
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: summaryText }));
  };

  const handleCapa = () => {
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text: 'CAPA recommendation' }));
    const capaText = capaRecommendations.length > 0
      ? `🔧 RECOMMENDED CAPA ACTIONS:\n` + capaRecommendations.map((c, i) => `${i + 1}. ${c}`).join('\n')
      : `🔧 RECOMMENDED CAPA ACTIONS:\n` +
        `1. Immediate Containment: Place batch ${form.batchLotNumber || 'inventory'} on QA quarantine hold and halt further dispatch.\n` +
        `2. Root Cause Audit: Review batch manufacturing execution records, raw material COAs, and environmental cleanroom logs.\n` +
        `3. Preventive Action: Implement automated inline particle/defect vision inspection and retrain production personnel.`;
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: capaText }));
  };

  const handleRisk = () => {
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text: 'AI risk classification' }));
    const riskText = `🛡️ AI RISK CLASSIFICATION:\n` +
      `• Severity Level: ${form.severity || 'High'}\n` +
      `• Priority Level: ${form.priority || 'High'}\n` +
      `• Triage Assessment: ${risk || 'Potential quality deviation requiring mandatory QA containment and investigation.'}`;
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: riskText }));
  };

  const handleRootCause = () => {
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text: 'Root cause recommendation' }));
    const rcText = `🔬 ROOT CAUSE RECOMMENDATION:\n` +
      `• Scientific Hypothesis: ${rootCause || 'Potential container closure integrity failure, raw material degradation, or filling line deviation.'}\n\n` +
      `• Recommended QA Investigation Plan:\n` +
      `  1. Inspect primary packaging seals and capping machine spindle torque logs.\n` +
      `  2. Conduct stability chamber testing on reserve batch samples.\n` +
      `  3. Audit cleanroom HVAC particulate counts for the manufacturing date run.`;
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: rcText }));
  };

  const handleFileAnother = () => {
    dispatch(resetForm());
    dispatch(resetChat());
  };

  return (
    <aside className="copilot-card">
      <header className="copilot-header">
        <div className="sparkle">✦</div>
        <div>
          <h2>AIVOA Copilot</h2>
          <p>Drop complaint files or paste text below.</p>
        </div>
        <span className="online" />
      </header>

      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => fileInput.current?.click()}
        onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') fileInput.current?.click(); }}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); void upload(event.dataTransfer.files[0]); }}
      >
        <input
          ref={fileInput}
          className="file-input"
          type="file"
          accept=".pdf,.docx,.txt,.eml,application/pdf,text/plain,message/rfc822"
          onChange={(event) => void upload(event.target.files?.[0])}
        />
        <strong>⇧ Drag & drop a complaint document</strong>
        <span>or click to browse</span>
        <small>PDF, DOCX, TXT, EML · Max file size: 10 MB</small>
      </div>

      <div className="chat-log">
        {messages.map((message) => (
          <div className={`message ${message.role}`} key={message.id}>
            {message.text}
          </div>
        ))}
        {processing && (
          <div className="message assistant">
            <span className="typing">AI is processing complaint details…</span>
          </div>
        )}
      </div>

      {hasFormContent && (
        <div className="quick-actions-container">
          <span className="quick-actions-label">⚡ Quick Actions:</span>
          <div className="quick-actions-grid">
            <button className="action-pill" onClick={handleSummarize}>
              📝 Summarize complaint
            </button>
            <button className="action-pill" onClick={handleCapa}>
              🔧 CAPA recommendation
            </button>
            <button className="action-pill" onClick={handleRisk}>
              🛡️ AI risk classification
            </button>
            <button className="action-pill" onClick={handleRootCause}>
              🔬 Root cause recommendation
            </button>
            <button className="action-pill action-pill-reset" onClick={handleFileAnother}>
              🔄 File another complaint
            </button>
          </div>
        </div>
      )}

      {(risk || rootCause || capaRecommendations.length > 0 || missingFields.length > 0) && (
        <div className="insight-panel">
          {risk && (
            <div className="insight-section">
              <strong>🛡️ AI Risk Classification:</strong>
              <p>{risk}</p>
            </div>
          )}

          {rootCause && (
            <div className="insight-section">
              <strong>🔬 Root Cause Hypothesis:</strong>
              <p>{rootCause}</p>
            </div>
          )}

          {capaRecommendations.length > 0 && (
            <div className="insight-section">
              <strong>🔧 Recommended CAPA Actions:</strong>
              <ul className="capa-list">
                {capaRecommendations.map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ul>
            </div>
          )}

          {missingFields.length > 0 && (
            <div className="insight-section missing-section">
              <strong>Still needed:</strong> {missingFields.join(', ')}
            </div>
          )}
        </div>
      )}

      <div className="chat-composer">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder="Type a message or paste a complaint…"
        />
        <button className="send" onClick={() => void submit()} disabled={!draft.trim() || processing}>
          ✓
        </button>
      </div>
      <p className="powered">POWERED BY LANGGRAPH · AI output must be verified</p>
    </aside>
  );
}
