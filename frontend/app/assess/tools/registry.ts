// app/assess/tools/registry.ts
// Maps a question's tool_type to the React component that renders it.
// Adding a new tool type later = add one line here, nothing else changes.

// app/assess/tools/registry.ts
import type { ComponentType } from "react";
import Mcq, { type McqProps } from "./Mcq";
import VoiceRecorder, { type VoiceRecorderProps } from "./VoiceRecorder";
import DataAnalysis, { type DataAnalysisProps } from "./DataAnalysis";
import MonacoEditor from "./MonacoEditor";
import TextAnswer, { type TextAnswerProps } from "./TextAnswer";

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
  multiple_choice: Mcq,
  voice: VoiceRecorder,
  open_ended: VoiceRecorder,
  text: VoiceRecorder,
  visualization: DataAnalysis,
  coding: MonacoEditor,
  text: TextAnswer,
};

export function getAnswerComponent(toolType: string): ComponentType<any> | null {
  return answerComponentRegistry[toolType] ?? null;
}