/** The actions on the whole pipeline: new, open, save, undo, redo. */
import { useRef, useState } from "react";
import {
  ConfigImportError,
  configToGraph,
  graphToConfig,
} from "../model/convert";
import { classifyParams } from "../model/classify";
import { defaultPipeline, emptyLevel } from "../model/graph";
import { copyText, downloadText, readFileText } from "../services/files";
import { useAppDispatch, useAppSelector, useAppStore } from "../store/hooks";
import {
  loadPipeline,
  redo,
  selectCanRedo,
  selectCanUndo,
  undo,
} from "../store/slices/graphSlice";
import { showNotice } from "../store/slices/uiSlice";

export default function Toolbar() {
  const dispatch = useAppDispatch();
  const store = useAppStore();
  const canUndo = useAppSelector(selectCanUndo);
  const canRedo = useAppSelector(selectCanRedo);
  const [dialog, setDialog] = useState<"open" | "save" | "new" | null>(null);

  const startNew = () => {
    dispatch(
      loadPipeline({ level: emptyLevel(), pipeline: defaultPipeline() }),
    );
    setDialog(null);
  };

  return (
    <div
      className="toolbar d-flex gap-2 align-items-center"
      role="toolbar"
      aria-label="Pipeline"
    >
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        onClick={() => {
          const { root } = store.getState().graph;
          if (root.nodes.length === 0) startNew();
          else setDialog("new");
        }}
      >
        New
      </button>
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        onClick={() => setDialog("open")}
      >
        Import JSON
      </button>
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        onClick={() => setDialog("save")}
      >
        Export JSON
      </button>
      <span className="toolbar-separator" />
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        disabled={!canUndo}
        onClick={() => dispatch(undo())}
        title="Undo (Ctrl+Z)"
      >
        Undo
      </button>
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        disabled={!canRedo}
        onClick={() => dispatch(redo())}
        title="Redo (Ctrl+Y)"
      >
        Redo
      </button>

      {dialog === "new" && (
        <Dialog title="Start a new pipeline?" onClose={() => setDialog(null)}>
          <p>The jobs on the board are discarded. You can undo this.</p>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={startNew}
          >
            Discard and start new
          </button>
        </Dialog>
      )}
      {dialog === "open" && <ImportDialog onClose={() => setDialog(null)} />}
      {dialog === "save" && <ExportDialog onClose={() => setDialog(null)} />}
    </div>
  );
}

function Dialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="dialog-backdrop">
      <div
        className="dialog card"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onKeyDown={(event) => {
          if (event.key === "Escape") onClose();
        }}
      >
        <div className="card-header d-flex justify-content-between align-items-center">
          <strong>{title}</strong>
          <button
            type="button"
            className="btn-close"
            aria-label="Close"
            onClick={onClose}
          />
        </div>
        <div className="card-body">{children}</div>
      </div>
    </div>
  );
}

function ImportDialog({ onClose }: { onClose: () => void }) {
  const dispatch = useAppDispatch();
  const schemas = useAppSelector((state) => state.jobSchemas);
  const [text, setText] = useState("");
  const [problems, setProblems] = useState<string[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  // nested jobs are told apart from other parameters by the schemas
  const ready = schemas.status === "succeeded" || schemas.status === "failed";

  const open = () => {
    let config: unknown;
    try {
      config = JSON.parse(text);
    } catch (error) {
      setProblems([`This is not valid JSON: ${(error as Error).message}`]);
      return;
    }
    try {
      const imported = configToGraph(config, (fn) =>
        classifyParams(schemas.schemas[fn]),
      );
      dispatch(loadPipeline(imported));
      dispatch(
        showNotice({
          kind: "info",
          text: `Opened ${imported.level.nodes.length} job${imported.level.nodes.length === 1 ? "" : "s"}.`,
        }),
      );
      onClose();
    } catch (error) {
      setProblems(
        error instanceof ConfigImportError ? error.problems : [String(error)],
      );
    }
  };

  return (
    <Dialog title="Import JSON" onClose={onClose}>
      {!ready && (
        <p role="status" className="small text-warning-emphasis">
          The job schemas are still loading. Importing needs them to find the
          jobs inside jobs.
        </p>
      )}
      <input
        ref={fileInput}
        type="file"
        accept=".json,application/json"
        aria-label="Choose a file"
        className="form-control form-control-sm mb-2"
        onChange={async (event) => {
          const file = event.target.files?.[0];
          if (file) setText(await readFileText(file));
        }}
      />
      <label htmlFor="import-text" className="form-label small">
        or paste the config
      </label>
      <textarea
        id="import-text"
        className="form-control font-monospace"
        rows={12}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setProblems([]);
        }}
      />
      {problems.length > 0 && (
        <ul role="alert" className="text-danger small mt-2">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      <button
        type="button"
        className="btn btn-primary btn-sm mt-2"
        disabled={!ready || text.trim() === ""}
        onClick={open}
      >
        Open
      </button>
    </Dialog>
  );
}

function ExportDialog({ onClose }: { onClose: () => void }) {
  const dispatch = useAppDispatch();
  const { root, pipeline } = useAppSelector((state) => state.graph);
  const [includeLayout, setIncludeLayout] = useState(false);
  const text = JSON.stringify(
    graphToConfig(root, pipeline, { includeLayout }),
    null,
    2,
  );

  return (
    <Dialog title="Export JSON" onClose={onClose}>
      <textarea
        readOnly
        aria-label="Exported config"
        data-testid="export-text"
        className="form-control font-monospace"
        rows={14}
        value={text}
      />
      <div className="form-check mt-2">
        <input
          id="include-layout"
          type="checkbox"
          className="form-check-input"
          checked={includeLayout}
          onChange={(event) => setIncludeLayout(event.target.checked)}
        />
        <label htmlFor="include-layout" className="form-check-label small">
          Include where the jobs are on the board (the key{" "}
          <code>x-pyantz-ui</code>, which pyantz ignores)
        </label>
      </div>
      <div className="d-flex gap-2 mt-2">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => downloadText("pipeline.json", text)}
        >
          Download
        </button>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={async () => {
            const copied = await copyText(text);
            dispatch(
              showNotice(
                copied
                  ? { kind: "info", text: "Copied to the clipboard." }
                  : {
                      kind: "error",
                      text: "The browser did not allow copying.",
                    },
              ),
            );
          }}
        >
          Copy
        </button>
      </div>
    </Dialog>
  );
}
