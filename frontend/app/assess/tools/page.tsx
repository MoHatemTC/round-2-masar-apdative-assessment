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
      starter_code:
`def add(a,b):
    pass
`
    }
  };


  const toolType = "coding";


  const Component = getAnswerComponent(toolType);


  function handleSubmit(answer: unknown) {
    console.log("Submitted:", answer);
    setSubmitted(true);
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