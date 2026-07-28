import { useRef, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { applyPatch } from '../features/complaint/complaintSlice';
import { processComplaint, uploadComplaint, type AiResponse } from '../features/copilot/api';
import { addMessage, setAiResult, setProcessing } from '../features/copilot/copilotSlice';

export function Copilot() {
  const dispatch = useAppDispatch(); const [draft, setDraft] = useState(''); const [dragging, setDragging] = useState(false); const fileInput = useRef<HTMLInputElement>(null); const { messages, processing, missingFields, risk } = useAppSelector((s) => s.copilot); const form = useAppSelector((s) => s.complaint.form);
  const applyAiResult = (result: AiResponse) => { dispatch(applyPatch(result.patch)); dispatch(setAiResult(result)); dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: result.message })); };
  const submit = async () => {
    const text = draft.trim(); if (!text || processing) return;
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text })); setDraft(''); dispatch(setProcessing(true));
    try { applyAiResult(await processComplaint(text, form)); }
    catch (error) { dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: error instanceof Error ? error.message : 'Something went wrong.' })); }
    finally { dispatch(setProcessing(false)); }
  };
  const upload = async (file?: File) => {
    if (!file || processing) return;
    if (file.size > 10 * 1024 * 1024) { dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: 'This file is larger than the 10 MB upload limit.' })); return; }
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', text: `Uploaded complaint document: ${file.name}` })); dispatch(setProcessing(true));
    try { applyAiResult(await uploadComplaint(file, form)); }
    catch (error) { dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', text: error instanceof Error ? error.message : 'The document could not be processed.' })); }
    finally { dispatch(setProcessing(false)); if (fileInput.current) fileInput.current.value = ''; }
  };
  return <aside className="copilot-card">
    <header className="copilot-header"><div className="sparkle">✦</div><div><h2>AIVOA Copilot</h2><p>Drop complaint files or paste text below.</p></div><span className="online" /></header>
    <div className={`upload-zone ${dragging ? 'dragging' : ''}`} role="button" tabIndex={0} onClick={() => fileInput.current?.click()} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') fileInput.current?.click(); }} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); void upload(event.dataTransfer.files[0]); }}><input ref={fileInput} className="file-input" type="file" accept=".pdf,.docx,.txt,.eml,application/pdf,text/plain,message/rfc822" onChange={(event) => void upload(event.target.files?.[0])} /><strong>⇧ Drag & drop a complaint document</strong><span>or click to browse</span><small>PDF, DOCX, TXT, EML · Max file size: 10 MB</small></div>
    <div className="chat-log">{messages.map((message) => <div className={`message ${message.role}`} key={message.id}>{message.text}</div>)}{processing && <div className="message assistant"><span className="typing">AI is extracting and checking the complaint…</span></div>}</div>
    {(risk || missingFields.length > 0) && <div className="insight-panel">{risk && <p><strong>Initial risk:</strong> {risk}</p>}{missingFields.length > 0 && <p><strong>Still needed:</strong> {missingFields.join(', ')}</p>}</div>}
    <div className="chat-composer"><textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void submit(); } }} placeholder="Type a message or paste a complaint…" /><button className="send" onClick={() => void submit()} disabled={!draft.trim() || processing}>✓</button></div>
    <p className="powered">POWERED BY LANGGRAPH · AI output must be verified</p>
  </aside>;
}
