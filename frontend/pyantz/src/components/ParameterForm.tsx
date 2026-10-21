/**
 * Edit the parameters of a job as a form made from its schema, or as raw json.
 *
 * Parameters which are jobs are not here: they are opened as nested levels.
 */
import { Component, useMemo, useState, type ReactNode } from "react";
import Form from "@rjsf/core";
import type { RJSFSchema } from "@rjsf/utils";
import { customizeValidator } from "@rjsf/validator-ajv8";
import Ajv2019 from "ajv/dist/2019";
import { JsonEditor } from "json-edit-react";
import { simpleSchema } from "../model/classify";
import type { NestedKind } from "../model/graph";
import {
  buildUiSchema,
  ignoringTemplates,
  simplifyForForm,
} from "../model/rjsf";
import { useSchema } from "../hooks/useSchema";
import { useAppDispatch } from "../store/hooks";
import { jsonEditorTheme, useColorScheme } from "../theme";
import { updateJob } from "../store/slices/graphSlice";

const validator = ignoringTemplates(
  customizeValidator({
    AjvClass: Ajv2019,
    ajvOptionsOverrides: { strict: false },
  }),
);

class FormBoundary extends Component<
  { fallback: (message: string) => ReactNode; children: ReactNode },
  { message: string | null }
> {
  state = { message: null as string | null };

  static getDerivedStateFromError(error: unknown) {
    return { message: error instanceof Error ? error.message : String(error) };
  }

  render() {
    return this.state.message === null
      ? this.props.children
      : this.props.fallback(this.state.message);
  }
}

interface ParameterFormProps {
  nodeId: string;
  fn: string;
  parameters: Record<string, unknown>;
}

export default function ParameterForm({
  nodeId,
  fn,
  parameters,
}: ParameterFormProps) {
  const dispatch = useAppDispatch();
  const { schema, loadError, kinds } = useSchema(fn);
  const scheme = useColorScheme();
  const [mode, setMode] = useState<"form" | "raw">("form");

  const formSchema = useMemo(
    () =>
      schema
        ? simplifyForForm(
            simpleSchema(schema, kinds as Record<string, NestedKind>),
          )
        : undefined,
    [schema, kinds],
  );

  const setParameters = (next: Record<string, unknown>) =>
    dispatch(
      updateJob({
        id: nodeId,
        changes: { parameters: next },
        editKey: `${nodeId}:parameters`,
      }),
    );

  const raw = (notice?: string) => (
    <div>
      {notice ? (
        <p role="status" className="small text-warning-emphasis mb-2">
          {notice}
        </p>
      ) : null}
      <JsonEditor
        data={parameters}
        theme={jsonEditorTheme(scheme)}
        setData={(data: unknown) =>
          setParameters(data as Record<string, unknown>)
        }
      />
    </div>
  );

  if (!formSchema) {
    return raw(
      loadError
        ? `Schema unavailable (${loadError}); editing raw JSON.`
        : "No schema for this job; editing raw JSON.",
    );
  }

  return (
    <div>
      <div
        className="btn-group btn-group-sm mb-2"
        role="group"
        aria-label="Edit as"
      >
        {(["form", "raw"] as const).map((option) => (
          <button
            key={option}
            type="button"
            className={`btn btn-outline-secondary ${mode === option ? "active" : ""}`}
            aria-pressed={mode === option}
            onClick={() => setMode(option)}
          >
            {option === "form" ? "Form" : "Raw JSON"}
          </button>
        ))}
      </div>
      {mode === "raw" ? (
        raw()
      ) : (
        <FormBoundary
          fallback={(message) =>
            raw(`This form can't be shown (${message}); editing raw JSON.`)
          }
        >
          <Form
            schema={formSchema as RJSFSchema}
            formData={parameters}
            validator={validator}
            liveValidate="onChange"
            showErrorList={false}
            noHtml5Validate
            uiSchema={buildUiSchema(formSchema)}
            experimental_defaultFormStateBehavior={{
              emptyObjectFields: "skipDefaults",
              arrayMinItems: { populate: "requiredOnly" },
            }}
            // changes the form makes by itself (defaults) have no id: not the user's
            onChange={(event, id) => {
              if (id !== undefined && event.formData) {
                setParameters(event.formData as Record<string, unknown>);
              }
            }}
          >
            <></>
          </Form>
        </FormBoundary>
      )}
    </div>
  );
}
