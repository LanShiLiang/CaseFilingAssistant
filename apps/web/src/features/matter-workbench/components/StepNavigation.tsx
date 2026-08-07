const STEP_LABELS = ["当事人与依据", "申请内容", "检查与预览", "导出"] as const;

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
      <span className="step-caption">步骤 {activeStep} / 4</span>
      <nav aria-label="事项步骤">
        {STEP_LABELS.map((label, index) => {
          const step = index + 1;
          return (
            <button
              key={label}
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
