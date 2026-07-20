"use client";
// Admin: paste/upload a question-bank JSON → import → it becomes a Question Set.  [TODO: build out]
import { useState } from "react";
import { importBank } from "@/lib/api";

export default function QuestionBankPage() {
  const [json, setJson] = useState("");
  const [setName, setSetName] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function handleImport() {
    setErr(""); setMsg("");
    let items: unknown[];
    try { items = JSON.parse(json); if (!Array.isArray(items)) throw new Error("Expected a JSON array"); }
    catch (e) { setErr(e instanceof Error ? e.message : "Invalid JSON"); return; }
    try {
      const r = await importBank(items, setName.trim() || undefined);
      setMsg(`Imported ${r.questions} questions` + (r.set ? ` → set "${r.set.name}" (${r.set.item_count})` : ""));
      setJson("");
    } catch (e) { setErr(e instanceof Error ? e.message : "Import failed"); }
  }

  return (
    <main style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Question Bank — Import</h1>
      <p>Paste a JSON that defines competencies, sub-competencies, and questions (with difficulty).
         It becomes a reusable Question Set you pick when creating an assessment.</p>
      {/* TODO: also fetch getQuestionTypes() to render per-type templates + a schema-driven single-add form */}
      <input placeholder="Set name (optional)" value={setName} onChange={(e) => setSetName(e.target.value)}
             style={{ width: "100%", padding: 8, marginBottom: 8 }} />
      <textarea value={json} onChange={(e) => setJson(e.target.value)} rows={16}
                placeholder='[{"source_ref":"...","track":{...},"sub_competency":{...},"tool_type":"mcq","difficulty":"easy","body":"...","payload":{...}}]'
                style={{ width: "100%", fontFamily: "monospace", padding: 8 }} />
      <button onClick={handleImport} disabled={!json.trim()} style={{ marginTop: 8, padding: "8px 16px" }}>Import</button>
      {msg && <p style={{ color: "green" }}>{msg}</p>}
      {err && <p style={{ color: "crimson" }}>{err}</p>}
    </main>
  );
}
