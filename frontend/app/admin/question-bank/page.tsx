"use client";
// Admin: paste/upload a question-bank JSON → import → it becomes a Question Set.  [TODO: build out]
import { useEffect, useState, useRef } from "react";
import { 
  importBank,
  browseQuestions,
  type QuestionBrowserItem,
  listCompetencies
 } from "@/lib/api";

import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

export default function QuestionBankPage() {
  const [json, setJson] = useState("");
  const [setName, setSetName] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [questions, setQuestions] = useState<QuestionBrowserItem[]>([]);
  const [toolType, setToolType] = useState("");
  const [competency, setCompetency] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const fileInputRef = useRef<HTMLInputElement>(null);

  type Competency = {
    id: string;
    name: string;
  };

  const [competencies, setCompetencies] = useState<Competency[]>([]);

  useEffect(() => {
    setLoadingQuestions(true);
    setErr("");
    setCurrentPage(1);

    browseQuestions({
      tool_type: toolType || undefined,
      competency: competency || undefined,
      difficulty: difficulty
        ? Number(difficulty)
        : undefined,
      })
        .then(setQuestions)
        .catch((e) => {
          console.error(e);
          setErr("Failed to load questions.");
        })
        .finally(() => setLoadingQuestions(false));
    }, [toolType, competency, difficulty]);

    useEffect(() => {
      async function loadCompetencies() {
        try {
          const data = await listCompetencies();
          setCompetencies(data);
        } catch (err) {
          console.error(err);
          setErr("Failed to load competencies.");
      }
    }

    loadCompetencies();
  }, []);

function openFilePicker() {
  fileInputRef.current?.click();
}

async function handleFileSelected(
  e: React.ChangeEvent<HTMLInputElement>
) {
  const file = e.target.files?.[0];

  if (!file) return;

  if (!file.name.endsWith(".json")) {
    setMsg("");
    setErr("Please choose a JSON file.");
    return;
  }

  try {
    const text = await file.text();

    JSON.parse(text); // validate

    setJson(text);
    setErr("");
  } catch {
    setMsg("");
    setErr("Selected file is not valid JSON.");
  } finally {
    e.target.value = ""; // reset file input so the same file can be selected again
  }
}

  async function handleImport() {
    setIsImporting(true);
    setErr(""); 
    setMsg("");
    let items: unknown[];
    try { items = JSON.parse(json); if (!Array.isArray(items)) throw new Error("Expected a JSON array"); }
    catch (e) { 
      setErr(e instanceof Error ? e.message : "Invalid JSON");
      setIsImporting(false);
      return;
    }
    try {
      const r = await importBank(items, setName.trim() || undefined);
      setMsg(`Imported ${r.questions} questions` + (r.set ? ` → set "${r.set.name}" (${r.set.item_count})` : ""));
      setJson("");
      setSetName("");
      setLoadingQuestions(true);

      const updated = await browseQuestions({
        tool_type: toolType || undefined,
        competency: competency || undefined,
        difficulty: difficulty ? Number(difficulty) : undefined,
      });

      setQuestions(updated);
      setCurrentPage(1);

      const comps = await listCompetencies();
      setCompetencies(comps);

    } catch (e) {
        setErr(
          e instanceof Error 
            ? e.message  
            : "Import failed"
          ); 
      }
    finally{
      setIsImporting(false);
      setLoadingQuestions(false);
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <h1 className="text-3xl font-bold">
        Question Bank
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        Import a new question bank or browse existing questions. Upload a JSON file containing competencies, sub-competencies, and questions to create a reusable question set for assessments.
      </p>
      <Card>
      <h2 className="text-lg font-semibold mb-4">
        Browse Questions
      </h2>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">

       <div>
        <label className="mb-1 block text-sm font-medium">
          Tool Type
        </label>
        <select disabled={loadingQuestions} className="w-full rounded-md border border-gray-300 bg-white p-2 text-gray-900 dark:border-gray-700 dark:bg-gray-800 dark:text-white" value={toolType} onChange={(e) => setToolType(e.target.value)}>
          <option value="">All</option>
          <option value="mcq">MCQ</option>
          <option value="coding">Coding</option>
          <option value="voice">Voice</option>
          <option value="visualization">Visualization</option>
        </select>
       </div>

       <div>
        <label className="mb-1 block text-sm font-medium">
          Competency
        </label>
        <select
          disabled={loadingQuestions}
          className="w-full rounded-md border border-gray-300 bg-white p-2 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
          value={competency}
          onChange={(e) => setCompetency(e.target.value)}
        >
          <option value="">All Competencies</option>

          {competencies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
       </div>

       <div>
        <label className="mb-1 block text-sm font-medium">
          Difficulty
        </label>
        <select disabled={loadingQuestions} className="w-full rounded-md border border-gray-300 bg-white p-2 dark:border-gray-700 dark:bg-gray-800 dark:text-white" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
          <option value="">All Difficulties</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5">5</option>
        </select>
       </div>

      </div>
    </Card>

      {/* TODO: also fetch getQuestionTypes() to render per-type templates + a schema-driven single-add form */}
      
      <Card className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            Question Browser
          </h2>

          <span className="text-sm text-gray-500 dark:text-gray-400">
            {loadingQuestions ? "Loading..." : `${questions.length} questions`}
          </span>
        </div>

        {(() => {
          const totalQuestions = questions.length;
          const totalPages = Math.max(1, Math.ceil(totalQuestions / ITEMS_PER_PAGE));
          const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
          const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, totalQuestions);
          const displayedQuestions = questions.slice(startIndex, startIndex + ITEMS_PER_PAGE);

          return (
            <>
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b dark:border-gray-700">
                    <th className="w-1/2 text-left p-3">Question</th>
                    <th className="text-left p-3">Competency</th>
                    <th className="text-left p-3">Tool Type</th>
                    <th className="text-left p-3">Difficulty</th>
                  </tr>
                </thead>

                <tbody>
                  {loadingQuestions ? (
                    <tr>
                      <td colSpan={4} className="py-10">
                        <div className="flex items-center justify-center gap-3">
                          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"></div>
                          <span>Loading questions...</span>
                        </div>
                      </td>
                    </tr>
                  ) : totalQuestions === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-10 text-center text-gray-500 dark:text-gray-400">
                        No questions match the selected filters.
                      </td>
                    </tr>
                  ) : (
                    displayedQuestions.map((q) => (
                      <tr key={q.id} className="border-b odd:bg-white hover:bg-gray-100 even:bg-gray-50 dark:odd:bg-gray-900 dark:even:bg-gray-800 dark:hover:bg-gray-700">
                        <td className="max-w-lg break-words p-3">{q.text}</td>
                        <td className="p-3">{q.competency.name}</td>
                        <td className="p-3">{q.tool_type}</td>
                        <td className="p-3">{q.difficulty}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>

              {!loadingQuestions && totalQuestions > 0 && (
                <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-gray-200 dark:border-gray-700 pt-4 text-sm text-gray-500 dark:text-gray-400">
                  <div>
                    Showing <span className="font-medium text-gray-900 dark:text-white">{startIndex + 1}</span>–<span className="font-medium text-gray-900 dark:text-white">{endIndex}</span> of <span className="font-medium text-gray-900 dark:text-white">{totalQuestions}</span> questions
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={currentPage === 1}
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                    >
                      Previous
                    </Button>

                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                      .map((p, idx, arr) => {
                        const prevPage = arr[idx - 1];
                        const showEllipsis = prevPage && p - prevPage > 1;
                        return (
                          <div key={p} className="flex items-center gap-1">
                            {showEllipsis && <span className="px-1 text-gray-400">…</span>}
                            <button
                              type="button"
                              onClick={() => setCurrentPage(p)}
                              className={`h-8 min-w-[2rem] px-2.5 rounded-md text-xs font-medium transition-colors ${
                                currentPage === p
                                  ? "bg-blue-600 text-white font-semibold"
                                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                              }`}
                            >
                              {p}
                            </button>
                          </div>
                        );
                      })}

                    <Button
                      type="button"
                      variant="secondary"
                      disabled={currentPage >= totalPages}
                      onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          );
        })()}
      </Card>

      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json"
        onChange={handleFileSelected}
        className="hidden"
      />

      <Card className="mt-8 space-y-4">
      <h2 className="text-lg font-semibold mb-4">
        Upload Question Bank
      </h2>
      <input className="w-full rounded-md border border-gray-300 bg-white p-2 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
        placeholder="Set name (optional)" value={setName} onChange={(e) => setSetName(e.target.value)} />
      
      <div className="flex gap-3 mb-4">
        <Button
          type="button"
          onClick={openFilePicker}
          disabled={isImporting}
        >
          Import JSON File
        </Button>

        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            setJson("");
            setSetName("");
            setErr("");
            setMsg("");
            fileInputRef.current && (fileInputRef.current.value = ""); // reset file input so the same file can be selected again
          }}
        >
          Clear
        </Button>
      </div>

      <textarea className="w-full rounded-md border border-gray-300 bg-white p-3 font-mono min-h-[350px] dark:border-gray-700 dark:bg-gray-800 dark:text-white"
        value={json} onChange={(e) => setJson(e.target.value)} 
        placeholder='[{"source_ref":"...","track":{...},"sub_competency":{...},"tool_type":"mcq","difficulty":3,"body":"...","payload":{...}}]' />
      <Button onClick={handleImport} disabled={!json.trim() || isImporting}>
        {isImporting ? "Importing..." : "Import Question Bank"}
      </Button>
      </Card>
      {msg && (
        <Card>
          <p className="font-medium text-green-600 dark:text-green-400">{msg}</p>
        </Card>
      )}

      {err && (
        <Card>
          <p className="font-medium text-red-600 dark:text-red-400">{err}</p>
        </Card>
      )}
    </main>
  );
}
