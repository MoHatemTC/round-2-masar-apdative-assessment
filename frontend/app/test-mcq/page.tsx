"use client";

import Mcq from "../assess/tools/Mcq";

const sampleQuestion = {
  id: "q-1",
  body: "In a Retrieval-Augmented Generation (RAG) system, what is the primary purpose of embeddings?",
  payload: {
    options: [
      { id: "a", text: "To compress the model's weights for faster inference" },
      { id: "b", text: "To represent text as vectors so semantically similar chunks can be found by nearest-neighbour search" },
      { id: "c", text: "To encrypt the documents before storage" },
      { id: "d", text: "To translate the documents into English" },
    ],
  },
};

export default function TestPage() {
  return (
    <Mcq
      question={sampleQuestion}
      onSubmit={(result) => alert(JSON.stringify(result))}
    />
  );
}