"use client";

import { LoaderCircle } from "lucide-react";

import { MatterFormProvider } from "./MatterForm";
import { MatterHeader } from "./components/MatterHeader";
import { StepNavigation } from "./components/StepNavigation";
import { ApplicationStep } from "./steps/ApplicationStep";
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

  return (
    <div className="workbench-shell">
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
              <ApplicationStep
                onUpload={controller.handleUpload}
                outstanding={controller.outstanding}
                busy={controller.anyBusy}
                onBack={() => controller.navigate(1)}
                onSave={controller.saveStepTwo}
              />
            ) : null}
            {activeStep === 3 ? (
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
                onBack={() => controller.navigate(2)}
                onContinue={() => controller.navigate(4)}
                onRetry={controller.retryFailedJob}
              />
            ) : null}
            {activeStep === 4 ? (
              <ExportStep
                generation={controller.generation}
                finalChecked={controller.finalChecked}
                checks={controller.exportChecks}
                confirmPending={controller.confirmPending}
                onCheckedChange={controller.setExportCheck}
                onConfirm={controller.confirmAndUnlock}
                onBack={() => controller.navigate(3)}
              />
            ) : null}
          </main>
        </MatterFormProvider>
      </div>
    </div>
  );
}
