"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import FormField from "@/components/ui/FormField";
import {
  createAssessment,
  getCompetencies,
  getQuestionSets,
  getCompetencyTracks,
  type QuestionSet,
  type CompetencyTrack,
} from "@/lib/api";

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function CreateAssessmentPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [questionSetId, setQuestionSetId] = useState("");
  const [timeLimit, setTimeLimit] = useState("30");
  const [competencies, setCompetencies] = useState<string[]>([]);
  const [competenciesLoading, setCompetenciesLoading] = useState(false);
  const [competenciesError, setCompetenciesError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [questionSetsLoading, setQuestionSetsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const comboboxRef = useRef<HTMLDivElement>(null);

  const [allTracks, setAllTracks] = useState<CompetencyTrack[]>([]);

  useEffect(() => {
    getQuestionSets()
      .then(setQuestionSets)
      .catch(() => {})
      .finally(() => setQuestionSetsLoading(false));

    getCompetencyTracks()
      .then(setAllTracks)
      .catch(() => {});
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (comboboxRef.current && !comboboxRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const trackNameMap = useMemo(() => {
    const map = new Map<string, string>();
    allTracks.forEach((t) => map.set(t.id, t.name));
    return map;
  }, [allTracks]);

  const filteredSets = useMemo(() => {
    if (!searchTerm.trim()) return questionSets;
    const lower = searchTerm.toLowerCase();
    return questionSets.filter(
      (qs) =>
        qs.name.toLowerCase().includes(lower) ||
        qs.id.toLowerCase().includes(lower)
    );
  }, [questionSets, searchTerm]);

  const selectedSetName = useMemo(() => {
    const found = questionSets.find((qs) => qs.id === questionSetId);
    return found?.name || "";
  }, [questionSets, questionSetId]);

  function handleSelectSet(qs: QuestionSet) {
    setQuestionSetId(qs.id);
    setSearchTerm(qs.name);
    setDropdownOpen(false);
  }

  function handleInputChange(value: string) {
    setSearchTerm(value);
    setDropdownOpen(true);
    const exact = questionSets.find((qs) => qs.name.toLowerCase() === value.toLowerCase());
    if (exact) {
      setQuestionSetId(exact.id);
    } else {
      setQuestionSetId("");
    }
  }

  function handleInputFocus() {
    setDropdownOpen(true);
    if (questionSetId && selectedSetName) {
      setSearchTerm(selectedSetName);
    }
  }

  useEffect(() => {
    if (!UUID_REGEX.test(questionSetId)) {
      setCompetencies([]);
      setCompetenciesError(null);
      return;
    }

    setCompetenciesLoading(true);
    setCompetenciesError(null);

    getCompetencies(questionSetId)
      .then((data) => {
        setCompetencies(data);
        setCompetenciesLoading(false);
      })
      .catch((err) => {
        setCompetenciesError(err instanceof Error ? err.message : "Failed to load competencies");
        setCompetencies([]);
        setCompetenciesLoading(false);
      });
  }, [questionSetId]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      await createAssessment({
        title,
        question_set_id: questionSetId,
        time_limit_min: parseInt(timeLimit, 10) || 30,
      });
      router.push("/admin/assessments");
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create assessment");
      setSubmitting(false);
    }
  };

  const isFormValid = title.trim() !== "" && UUID_REGEX.test(questionSetId) && parseInt(timeLimit, 10) > 0;

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Create Assessment</h1>
      </div>
      <Card className="max-w-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="flex flex-col gap-5"
        >
          <FormField
            label="Title"
            value={title}
            onChange={setTitle}
            placeholder="e.g. Frontend Developer Assessment"
          />

          <div className="flex flex-col gap-1">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground/90 tracking-tight">
                Question Set
              </label>
              <div ref={comboboxRef} className="relative">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => handleInputChange(e.target.value)}
                  onFocus={handleInputFocus}
                  placeholder={questionSetsLoading ? "Loading question sets…" : "Search by name…"}
                  disabled={questionSetsLoading}
                  className={
                    "w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground " +
                    "placeholder:text-muted-foreground shadow-inner-sm " +
                    "transition-colors duration-150 " +
                    "hover:border-[color:var(--accent-strong)]/50 " +
                    "focus:outline-none focus:border-[color:var(--ring)] focus:ring-2 focus:ring-ring/40 " +
                    "disabled:opacity-50 disabled:cursor-not-allowed"
                  }
                />
                {questionSetId && !dropdownOpen && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuestionSetId("");
                      setSearchTerm("");
                      setCompetencies([]);
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                      <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                    </svg>
                  </button>
                )}
                {dropdownOpen && (
                  <ul className="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-md border border-input bg-card py-1 shadow-lg">
                    {filteredSets.length === 0 ? (
                      <li className="px-3 py-2 text-sm text-muted-foreground italic">
                        No question sets found.
                      </li>
                    ) : (
                      filteredSets.map((qs) => (
                        <li
                          key={qs.id}
                          onClick={() => handleSelectSet(qs)}
                          className={
                            "flex flex-col gap-0.5 cursor-pointer px-3 py-2 text-sm transition-colors " +
                            "hover:bg-primary/10 " +
                            (qs.id === questionSetId ? "bg-primary/5 text-primary font-medium" : "text-foreground")
                          }
                        >
                          <span>{qs.name}</span>
                          <span className="text-xs text-muted-foreground font-mono">{qs.id}</span>
                        </li>
                      ))
                    )}
                  </ul>
                )}
              </div>
            </div>
            {competenciesLoading && (
              <div className="mt-2 flex items-center gap-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                <span className="text-xs text-gray-500 dark:text-gray-400">Loading competencies…</span>
              </div>
            )}
            {competenciesError && (
              <p className="mt-2 text-xs text-red-600 dark:text-red-400">{competenciesError}</p>
            )}

            {competencies.length > 0 && (
              <div className="mt-2">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  Measured Competency Tracks
                </span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {competencies.map((id) => (
                    <span
                      key={id}
                      className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/40 px-3 py-1 text-xs font-medium text-blue-800 dark:text-blue-300"
                    >
                      {trackNameMap.get(id) || id}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <FormField
            label="Time Limit (minutes)"
            value={timeLimit}
            onChange={setTimeLimit}
            type="number"
            placeholder="30"
          />

          {submitError && (
            <p className="text-sm text-red-600 dark:text-red-400">{submitError}</p>
          )}

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" disabled={!isFormValid || submitting}>
              {submitting ? "Creating…" : "Create Assessment"}
            </Button>
            <Button variant="secondary" onClick={() => router.push("/admin/assessments")}>
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
