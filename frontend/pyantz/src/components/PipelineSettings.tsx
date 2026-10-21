/** Edit what belongs to the whole pipeline: the submitter, the host, the variables. */
import { JsonEditor } from "json-edit-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  setHost,
  setSubmitter,
  setVariables,
} from "../store/slices/graphSlice";
import { jsonEditorTheme, useColorScheme } from "../theme";
import { CheckField, NumberField, SelectField, TextField } from "./fields";

type Raw = Record<string, unknown>;

const SUBMITTER_TYPES = ["local_proc", "slurm_sbatch"] as const;
const HOST_TYPES = ["local", "ssh", "container"] as const;

const NEW_SUBMITTER: Record<(typeof SUBMITTER_TYPES)[number], Raw> = {
  local_proc: { type_: "local_proc", working_directory: "pyantz_work" },
  slurm_sbatch: { type_: "slurm_sbatch", working_dir: "pyantz_work" },
};

const NEW_HOST: Record<(typeof HOST_TYPES)[number], Raw | undefined> = {
  local: undefined,
  ssh: { type_: "ssh", remote_host: "" },
  container: { type_: "container" },
};

/** Set a key, or remove it when there is no value. */
const withKey = (settings: Raw, key: string, value: unknown): Raw => {
  const next = { ...settings };
  if (value === undefined) delete next[key];
  else next[key] = value;
  return next;
};

const RawEditor = ({
  data,
  onChange,
  label,
}: {
  data: Raw;
  onChange: (data: Raw) => void;
  label: string;
}) => {
  const scheme = useColorScheme();
  return (
    <div aria-label={label} role="group">
      <JsonEditor
        data={data}
        theme={jsonEditorTheme(scheme)}
        setData={(next: unknown) => onChange(next as Raw)}
      />
    </div>
  );
};

export default function PipelineSettings() {
  const dispatch = useAppDispatch();
  const { submitter, host, variables } = useAppSelector(
    (state) => state.graph.pipeline,
  );

  const submitterType = (submitter.type_ as string | undefined) ?? "local_proc";
  const hostType = (host?.type_ as string | undefined) ?? "local";
  const edit = (key: string, value: unknown) =>
    dispatch(setSubmitter(withKey(submitter, key, value)));

  return (
    <div className="p-3" data-testid="pipeline-settings">
      <h2 className="h6">Submitter</h2>
      <SelectField
        label="Runs jobs with"
        value={
          (SUBMITTER_TYPES as readonly string[]).includes(submitterType)
            ? (submitterType as (typeof SUBMITTER_TYPES)[number])
            : "local_proc"
        }
        options={SUBMITTER_TYPES}
        onChange={(type) => dispatch(setSubmitter({ ...NEW_SUBMITTER[type] }))}
      />
      {submitterType === "local_proc" ? (
        <>
          <TextField
            label="Working directory"
            value={submitter.working_directory as string | undefined}
            onChange={(value) => edit("working_directory", value)}
            help="Used when you run the exported file yourself. A run started from this page gets a directory chosen by the server instead."
          />
          <NumberField
            label="Worker processes"
            min={1}
            value={submitter.number_processes as number | undefined}
            onChange={(value) => edit("number_processes", value)}
          />
          <NumberField
            label="Timeout (seconds)"
            min={0}
            value={submitter.timeout as number | undefined}
            onChange={(value) => edit("timeout", value)}
            help="Empty for no timeout."
          />
          <CheckField
            label="Run in this process"
            checked={Boolean(submitter.use_same_proc)}
            onChange={(value) => edit("use_same_proc", value || undefined)}
            help="Easier to debug, and faster for small jobs."
          />
        </>
      ) : (
        <RawEditor
          label="Submitter settings"
          data={submitter}
          onChange={(next) => dispatch(setSubmitter(next))}
        />
      )}

      <h2 className="h6 mt-4">Host</h2>
      <SelectField
        label="Starts on"
        value={
          (HOST_TYPES as readonly string[]).includes(hostType)
            ? (hostType as (typeof HOST_TYPES)[number])
            : "local"
        }
        options={HOST_TYPES}
        onChange={(type) => dispatch(setHost(NEW_HOST[type]))}
        help="Runs started from this page are local only."
      />
      {host && hostType !== "local" && (
        <RawEditor
          label="Host settings"
          data={host}
          onChange={(next) => dispatch(setHost(next))}
        />
      )}

      <h2 className="h6 mt-4">Variables</h2>
      <p className="small text-secondary">
        Available to all jobs as <code>%{"{name}"}</code>.
      </p>
      <RawEditor
        label="Variables"
        data={variables ?? {}}
        onChange={(next) =>
          dispatch(
            setVariables(Object.keys(next).length > 0 ? next : undefined),
          )
        }
      />
    </div>
  );
}
