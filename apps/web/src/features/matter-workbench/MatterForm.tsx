"use client";

import { createContext, useContext, type PropsWithChildren } from "react";

import type { Matter } from "@case-filing/contracts";

import { Field, type FieldProps } from "./components/Field";
import type {
  FieldChangeHandler,
  FieldConfirmationHandler,
  FormState
} from "./types";

interface MatterFormContextValue {
  matter: Matter;
  fields: FormState;
  onFieldChange: FieldChangeHandler;
  isFieldConfirmed: (name: string) => boolean;
  onFieldConfirmationChange: FieldConfirmationHandler;
}

const MatterFormContext = createContext<MatterFormContextValue | null>(null);

export function MatterFormProvider({
  children,
  ...value
}: PropsWithChildren<MatterFormContextValue>) {
  return <MatterFormContext.Provider value={value}>{children}</MatterFormContext.Provider>;
}

export function useMatterForm(): MatterFormContextValue {
  const context = useContext(MatterFormContext);
  if (!context) throw new Error("MatterForm components must be rendered inside MatterFormProvider.");
  return context;
}

type ContextBoundFieldProps =
  | "value"
  | "onChange"
  | "confirmed"
  | "onConfirmationChange"
  | "source"
  | "status";

export type MatterFieldProps = Omit<FieldProps, ContextBoundFieldProps> & {
  valueOverride?: string;
};

/** 领域步骤只声明字段语义；值、来源与人工确认状态由同一表单上下文绑定。 */
export function MatterField({
  name,
  valueOverride,
  ...props
}: MatterFieldProps) {
  const {
    matter,
    fields,
    onFieldChange,
    isFieldConfirmed,
    onFieldConfirmationChange
  } = useMatterForm();
  return (
    <Field
      {...props}
      name={name}
      value={valueOverride ?? fields[name] ?? ""}
      onChange={onFieldChange}
      confirmed={isFieldConfirmed(name)}
      onConfirmationChange={onFieldConfirmationChange}
      source={matter.sources[name]?.[0]}
      status={matter.confirmations[name]}
    />
  );
}
