"use client";

import { LoaderCircle } from "lucide-react";

import { MatterFormProvider } from "./MatterForm";
import { MatterHeader } from "./components/MatterHeader";
import { OperationProgressModal } from "./components/OperationProgressModal";
import { StepNavigation } from "./components/StepNavigation";
import { ExportStep } from "./steps/ExportStep";
import { PartiesAndBasisStep } from "./steps/PartiesAndBasisStep";
import { ReviewStep } from "./steps/ReviewStep";
import { useMatterWorkbenchController } from "./useMatterWorkbenchController";

export function MatterWorkbench({ matterId }: { matterId: string }) {
  const controller = useMatterWorkbenchController(matterId);

  if (controller.isLoading) {
    return <main className="loading-page"><LoaderCircle className="spin" /> 正在读取本地事项……</main>;
  }
  if (!controller.matter || controller.queryError) {
    return <main className="loading-page">事项读取失败，请返回首页重试。</main>;
  }

  const { matter, activeStep } = controller;
  const operationActive = controller.operation !== null;

  return (
    <div className="workbench-shell">
      <div
        className="workbench-interaction-layer"
        inert={operationActive ? true : undefined}
        aria-hidden={operationActive ? true : undefined}
      >
        <MatterHeader matter={matter} />
        <div className="workbench-grid">
          <StepNavigation
            activeStep={activeStep}
            allowedSteps={controller.allowedSteps}
            onNavigate={controller.navigate}
          />
          <MatterFormProvider
            matter={matter}
            fields={controller.fields}
            onFieldChange={controller.updateField}
            isFieldEdited={controller.isFieldEdited}
          >
            <main className="workbench-main">
              {controller.error ? <div className="error-banner" role="alert">{controller.error}</div> : null}
              <fieldset className="workbench-form-lock" disabled={operationActive}>

                {activeStep === 1 ? (
                  <PartiesAndBasisStep
                    onUpload={controller.handleUpload}
                    busy={controller.anyBusy}
                    onSave={controller.saveStepOne}
                    dismissedScopeSignalIds={controller.dismissedScopeSignalIds}
                    onScopeSignalDismissalChange={controller.setScopeSignalDismissed}
                  />
                ) : null}
                {activeStep === 2 ? (
                  <ReviewStep
                    validation={controller.validation}
                    generation={controller.generation}
                    job={controller.job}
                    validationPending={controller.validationPending}
                    generationPending={controller.generationPending}
                    generationBusy={controller.generationBusy}
                    retryPending={controller.retryPending}
                    onValidate={controller.runValidation}
                    onGenerate={controller.generate}
                    onBack={() => controller.navigate(1)}
                    onContinue={() => controller.navigate(3)}
                    onRetry={controller.retryFailedJob}
                  />
                ) : null}
                {activeStep === 3 ? (
                  <ExportStep
                    generation={controller.generation}
                    finalChecked={controller.finalChecked}
                    checks={controller.exportChecks}
                    confirmPending={controller.confirmPending}
                    onCheckedChange={controller.setExportCheck}
                    onConfirm={controller.confirmAndUnlock}
                    onBack={() => controller.navigate(2)}
                  />
                ) : null}
              </fieldset>
            </main>
          </MatterFormProvider>
        </div>
      </div>
      <OperationProgressModal
        operation={controller.operation}
        jobProgress={controller.job?.progress}
        onDismiss={controller.dismissOperation}
      />
    </div>
  );
}
