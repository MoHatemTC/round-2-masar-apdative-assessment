"use client";

import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

interface MonacoEditorProps {
  question: {
    id: string;
    body: string;
    payload: Record<string, unknown>;
  };
  onSubmit: (result: unknown) => void;
  isSubmitting?: boolean;
}

export default function MonacoEditor({
  question,
  onSubmit,
  isSubmitting = false,
}: MonacoEditorProps) {
  const payload = question.payload as {
    language?: string;
    starter_code?: string;
  };

  const language = payload.language ?? "python";
  const starterCode = payload.starter_code ?? "";

  const [code, setCode] = useState(starterCode);

  useEffect(() => {
    setCode(starterCode);
  }, [starterCode]);

  function handleRun() {
    // Week 3: backend run endpoint / sandbox can be connected here.
    console.log("Run clicked");
    console.log(code);
  }

  function handleSubmit() {
    onSubmit({
      code,
    });
  }

  return (
    <div className="flex flex-col gap-4">

      {/* Question */}

      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {question.body}
        </h2>
      </div>

      {/* Language Badge */}

      <div className="flex justify-between items-center">

        <span className="rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white">
          {language.toUpperCase()}
        </span>

        <span className="text-sm text-gray-500 dark:text-gray-400">
          Coding Question
        </span>

      </div>

      {/* Monaco */}

      <div className="overflow-hidden rounded-md border border-gray-300 dark:border-neutral-700">

        <Editor
          height="500px"
          language={language}
          value={code}
          theme="vs-dark"
          onChange={(value) => setCode(value ?? "")}
          loading="Loading editor..."
          options={{
            automaticLayout: true,
            minimap: {
              enabled: false,
            },
            fontSize: 14,
            scrollBeyondLastLine: false,
            tabSize: 4,
            insertSpaces: true,
            wordWrap: "on",
            readOnly: isSubmitting,
            roundedSelection: true,
            smoothScrolling: true,
            bracketPairColorization: {
              enabled: true,
            },
          }}
        />

      </div>

      {/* Footer */}

      <div className="flex items-center justify-between">

        <span className="text-xs text-gray-500 dark:text-gray-400">
          {code.length} characters
        </span>

        <div className="flex gap-3">

          <button
            type="button"
            onClick={handleRun}
            disabled={isSubmitting}
            className="rounded-md border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-neutral-800"
          >
            ▶ Run
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? "Submitting..." : "Submit"}
          </button>

        </div>

      </div>

    </div>
  );
}