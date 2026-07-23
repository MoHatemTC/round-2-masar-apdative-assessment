"use client";

import { useRef, useState } from "react";
import { adminImportBank, AdminImportSummary } from "@/lib/api";

export default function ImportPage() {
  const [jsonText, setJsonText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AdminImportSummary | null>(null);
  const [error, setError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleImport() {
    setError("");
    setResult(null);

    let payload;

    try {
      payload = JSON.parse(jsonText);
    } catch {
      setError("Invalid JSON format");
      return;
    }

    setLoading(true);

    try {
      const response = await adminImportBank(payload);

      setResult(response);

      if (response.success) {
        setJsonText("");
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Import failed"
      );
    }

    setLoading(false);
  }

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleFileSelected(
    e: React.ChangeEvent<HTMLInputElement>
  ) {
    const file = e.target.files?.[0];

    if (!file) return;

    if (!file.name.endsWith(".json")) {
      setError("Please choose a JSON file.");
      return;
    }

    try {
      const text = await file.text();

      JSON.parse(text); // validate

      setJsonText(text);
      setError("");
    } catch {
      setError("Selected file is not valid JSON.");
    }
  }

  return (
    <main className="max-w-5xl mx-auto p-8">

      <h1 className="text-3xl font-bold mb-4">
        Question Bank Import
      </h1>

      <p className="mb-6 text-gray-600">
        Paste a QuestionBank JSON payload or import a JSON file.
        The backend will validate and import directly into Supabase.
      </p>

      <input
        type="file"
        accept=".json,application/json"
        ref={fileInputRef}
        onChange={handleFileSelected}
        className="hidden"
      />

      <div className="flex gap-3 mb-4">

        <button
          onClick={openFilePicker}
          className="px-5 py-3 rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          Import JSON File
        </button>

        <button
          onClick={() => setJsonText("")}
          className="px-5 py-3 rounded bg-gray-300"
        >
          Clear
        </button>

      </div>

      <textarea
        value={jsonText}
        onChange={(e) => setJsonText(e.target.value)}
        rows={25}
        className="w-full border rounded p-4 font-mono text-sm"
        placeholder={`{
  "competencies": [],
  "questions": [],
  "question_set": {
    "name": "Python Basics",
    "description": "Python Assessment",
    "items": []
  }
}`}
      />

      <button
        onClick={handleImport}
        disabled={loading || !jsonText}
        className="mt-5 px-6 py-3 rounded bg-black text-white disabled:opacity-50"
      >
        {loading ? "Importing..." : "Import Question Bank"}
      </button>

      {error && (
        <div className="mt-6 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 p-5 border rounded">

          <h2 className="font-bold mb-4">
            Import Result
          </h2>

          <div className="space-y-2">

            <p>
              <strong>Status:</strong>{" "}
              {result.success ? "✅ Success" : "❌ Failed"}
            </p>

            <p>
              <strong>Competencies Imported:</strong>{" "}
              {result.competencies_imported}
            </p>

            <p>
              <strong>Questions Imported:</strong>{" "}
              {result.questions_imported}
            </p>

            <p>
              <strong>Question Set Items:</strong>{" "}
              {result.question_set_items_imported}
            </p>

          </div>

          {result.errors.length > 0 && (
            <div className="mt-5">

              <h3 className="font-semibold text-red-600">
                Validation Errors
              </h3>

              <ul className="list-disc ml-6 mt-2">
                {result.errors.map((err, index) => (
                  <li key={index}>
                    Row {err.row} • {err.field}: {err.message}
                  </li>
                ))}
              </ul>

            </div>
          )}

        </div>
      )}

    </main>
  );
}