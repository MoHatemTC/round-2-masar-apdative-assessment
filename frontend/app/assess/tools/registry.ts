// app/assess/tools/registry.ts
// Maps a question's tool_type to the React component that renders it.
// Adding a new tool type later = add one line here, nothing else changes.

import type { ComponentType } from "react";
import Mcq, { type McqProps } from "./Mcq";
import OpenEndedText, { type OpenEndedTextProps } from "./OpenEndedText";
import DataAnalysis, { type DataAnalysisProps } from "./DataAnalysis";

// A loose common shape every answer component shares, so the registry can
// treat them uniformly even though each has slightly different props.
export interface AnswerComponentProps {
  question: {
    id: string;
    body: string;
    payload: Record<string, unknown>;
  };
  onSubmit: (result: unknown) => void;
  isSubmitting?: boolean;
}

export const answerComponentRegistry: Record<string, ComponentType<any>> = {
  mcq: Mcq,
  voice: OpenEndedText,
  visualization: DataAnalysis,
};

export function getAnswerComponent(toolType: string): ComponentType<any> | null {
  return answerComponentRegistry[toolType] ?? null;
}