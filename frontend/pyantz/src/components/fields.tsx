/** Small labelled inputs, shared by the panels. */
import { useId, type ReactNode } from "react";

interface FieldShellProps {
  label: string;
  help?: ReactNode;
  error?: string | null;
  children: (props: { id: string; describedBy?: string }) => ReactNode;
}

const FieldShell = ({ label, help, error, children }: FieldShellProps) => {
  const id = useId();
  const messageId = `${id}-message`;
  const hasMessage = Boolean(error) || Boolean(help);
  return (
    <div className="mb-2">
      <label htmlFor={id} className="form-label mb-1 small fw-semibold">
        {label}
      </label>
      {children({ id, describedBy: hasMessage ? messageId : undefined })}
      {error ? (
        <div id={messageId} className="invalid-feedback d-block">
          {error}
        </div>
      ) : help ? (
        <div id={messageId} className="form-text">
          {help}
        </div>
      ) : null}
    </div>
  );
};

interface TextFieldProps {
  label: string;
  value: string | undefined | null;
  onChange: (value: string) => void;
  help?: ReactNode;
  error?: string | null;
  placeholder?: string;
}

export const TextField = ({
  label,
  value,
  onChange,
  help,
  error,
  placeholder,
}: TextFieldProps) => (
  <FieldShell label={label} help={help} error={error}>
    {({ id, describedBy }) => (
      <input
        id={id}
        type="text"
        className={`form-control form-control-sm ${error ? "is-invalid" : ""}`}
        value={value ?? ""}
        placeholder={placeholder}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
    )}
  </FieldShell>
);

interface NumberFieldProps {
  label: string;
  value: number | undefined | null;
  // undefined when the box is emptied
  onChange: (value: number | undefined) => void;
  help?: ReactNode;
  min?: number;
}

export const NumberField = ({
  label,
  value,
  onChange,
  help,
  min,
}: NumberFieldProps) => (
  <FieldShell label={label} help={help}>
    {({ id, describedBy }) => (
      <input
        id={id}
        type="number"
        className="form-control form-control-sm"
        value={value ?? ""}
        min={min}
        aria-describedby={describedBy}
        onChange={(event) =>
          onChange(
            event.target.value === "" ? undefined : Number(event.target.value),
          )
        }
      />
    )}
  </FieldShell>
);

interface CheckFieldProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  help?: ReactNode;
}

export const CheckField = ({
  label,
  checked,
  onChange,
  help,
}: CheckFieldProps) => {
  const id = useId();
  return (
    <div className="form-check mb-2">
      <input
        id={id}
        type="checkbox"
        className="form-check-input"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <label htmlFor={id} className="form-check-label small">
        {label}
      </label>
      {help ? <div className="form-text">{help}</div> : null}
    </div>
  );
};

interface SelectFieldProps<T extends string> {
  label: string;
  value: T;
  options: readonly T[];
  onChange: (value: T) => void;
  help?: ReactNode;
}

export const SelectField = <T extends string>({
  label,
  value,
  options,
  onChange,
  help,
}: SelectFieldProps<T>) => (
  <FieldShell label={label} help={help}>
    {({ id, describedBy }) => (
      <select
        id={id}
        className="form-select form-select-sm"
        value={value}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.value as T)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    )}
  </FieldShell>
);
