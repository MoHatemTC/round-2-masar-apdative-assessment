"use client";

import { useState } from "react";
import { getAnswerComponent } from "./registry";

export default function ToolsPage() {

  const [submitted, setSubmitted] = useState(false);

  const question = {
  id: "demo-code-question",
  body: "Write a function that adds two numbers.",
  payload: {
    language: "python",
    starter_code: `def add(a,b):
    pass
`,
    test_cases: [
      {
        input: "add(2,3)",
        expected_output: "5",
      },
      {
        input: "add(5,7)",
        expected_output: "12",
      },
      {
        input: "add(-1,1)",
        expected_output: "0",
      },
    ],
  },
};


  const toolType = "coding";


  const Component = getAnswerComponent(toolType);


  async function handleSubmit(answer: unknown) {
  console.log("Submitted:", answer);

  setSubmitted(true);

  // simulate network request
  await new Promise((resolve) => setTimeout(resolve, 1000));

  alert("Answer submitted!");

  setSubmitted(false);
}


  if (!Component) {
    return (
      <div>
        No renderer found for {toolType}
      </div>
    );
  }


  return (
    <main className="p-8">

      <h1 className="text-2xl font-bold mb-6">
        Assessment Tool
      </h1>


      <Component
        question={question}
        onSubmit={handleSubmit}
        isSubmitting={submitted}
      />


    </main>
  );
}