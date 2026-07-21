"use client";

import { getAnswerComponent } from "../assess/tools/registry";

const sampleVoiceQuestion = {
  id: "q-voice-1",
  body: "Describe a time you resolved a conflict on a team.",
  tool_type: "voice",
  payload: {
    time_limit_seconds: 60,
    evaluation_criteria: ["Names the situation", "Explains their actions", "Reflects on the outcome"],
  },
};

const sampleDataQuestion = {
  id: "q-data-1",
  body: "Sales dropped 30% while ad spend rose 20%. What would you investigate?",
  tool_type: "visualization",
  payload: {
    dataset: {
      headers: ["Month", "Sales", "Ad Spend"],
      rows: [
        ["Jan", 10000, 2000],
        ["Feb", 7000, 2400],
      ],
    },
    expected_insights: ["Notices the inverse relationship", "Proposes plausible causes"],
  },
};

export default function TestRegistryPage() {
  const VoiceComponent = getAnswerComponent(sampleVoiceQuestion.tool_type);
  const DataComponent = getAnswerComponent(sampleDataQuestion.tool_type);

  return (
    <div className="flex flex-col gap-8 p-8">
      <div>
        <h2 className="font-bold mb-2">Voice / Open-ended test:</h2>
        {VoiceComponent && (
          <VoiceComponent question={sampleVoiceQuestion} onSubmit={(r: unknown) => alert(JSON.stringify(r))} />
        )}
      </div>

      <div>
        <h2 className="font-bold mb-2">Data Analysis test:</h2>
        {DataComponent && (
          <DataComponent question={sampleDataQuestion} onSubmit={(r: unknown) => alert(JSON.stringify(r))} />
        )}
      </div>
    </div>
  );
}