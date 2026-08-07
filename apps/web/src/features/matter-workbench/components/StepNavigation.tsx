import { WORKFLOW_STEPS } from "../workflow";

export function StepNavigation({
  activeStep,
  allowedSteps,
  onNavigate
}: {
  activeStep: number;
  allowedSteps: readonly boolean[];
  onNavigate: (step: number) => void;
}) {
  return (
    <aside className="step-sidebar">
      <span className="step-caption">步骤 {activeStep} / {WORKFLOW_STEPS.length}</span>
      <nav aria-label="事项步骤">
        {WORKFLOW_STEPS.map(({ key, label }, index) => {
          const step = index + 1;
          return (
            <button
              key={key}
              className={activeStep === step ? "active" : ""}
              disabled={!allowedSteps[index]}
              onClick={() => onNavigate(step)}
            >
              <span>{step}</span>{label}
            </button>
          );
        })}
      </nav>
      <p>步骤开放状态由服务端校验结果决定，浏览器不能跳过确认、检查或生成门禁。</p>
    </aside>
  );
}
