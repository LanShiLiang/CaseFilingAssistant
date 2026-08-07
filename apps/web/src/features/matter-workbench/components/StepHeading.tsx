import type { ReactNode } from "react";

import type { WorkflowStepNumber } from "../workflow";

export function StepHeading({
  step,
  title,
  description,
  icon
}: {
  step: WorkflowStepNumber;
  title: string;
  description: string;
  icon: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span>步骤 {step}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {icon}
    </div>
  );
}
