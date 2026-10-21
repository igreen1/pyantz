/** The jobs which can be added, to search, click, or drag onto the board. */

import { useEffect, useMemo, useRef, useState } from "react";
import { useAddJob } from "../hooks/useAddJob";
import { useAppSelector } from "../store/hooks";
import { selectAddJobBlock } from "../store/slices/graphSlice";
import { groupOf } from "../model/groups";
import { JOB_DRAG_TYPE } from "./JobBoard";
import "./Palette.css";

export default function Palette() {
  const addJob = useAddJob();
  const { items, descriptions, status, error } = useAppSelector(
    (state) => state.availableJobs,
  );
  const blocked = useAppSelector(selectAddJobBlock);
  const focusRequests = useAppSelector((state) => state.uiOptions.focusSearch);
  const [search, setSearch] = useState("");
  const searchBox = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (focusRequests > 0) searchBox.current?.focus();
  }, [focusRequests]);

  const groups = useMemo(() => {
    const words = search.toLowerCase().split(/\s+/).filter(Boolean);
    const found = new Map<string, { name: string; description: string }[]>();
    items.forEach((name, index) => {
      const description = descriptions[index] ?? "";
      const text = `${name} ${description}`.toLowerCase();
      if (!words.every((word) => text.includes(word))) return;
      const group = groupOf(name);
      found.set(group, [...(found.get(group) ?? []), { name, description }]);
    });
    return [...found.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [items, descriptions, search]);

  return (
    <aside className="palette" aria-label="Jobs">
      <input
        ref={searchBox}
        type="search"
        className="form-control form-control-sm"
        placeholder="Search jobs"
        aria-label="Search jobs"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {blocked && (
        <p role="status" className="palette-note text-warning-emphasis">
          {blocked}
        </p>
      )}
      {(status === "loading" || status === "idle") && (
        <p role="status" className="palette-note">
          Loading jobs…
        </p>
      )}
      {status === "failed" && (
        <p role="alert" className="palette-note text-danger">
          Error loading jobs: {error}
        </p>
      )}
      {status === "succeeded" && groups.length === 0 && (
        <p className="palette-note">No job matches.</p>
      )}
      <div className="palette-list">
        {groups.map(([group, jobs]) => (
          <section key={group} aria-label={group}>
            <h2 className="palette-group">{group}</h2>
            <ul>
              {jobs.map(({ name, description }) => (
                <li key={name}>
                  <button
                    type="button"
                    className="palette-job"
                    draggable={!blocked}
                    disabled={blocked !== null}
                    title={description}
                    onDragStart={(event) => {
                      event.dataTransfer.setData(JOB_DRAG_TYPE, name);
                      event.dataTransfer.effectAllowed = "copy";
                    }}
                    onClick={() => addJob(name)}
                  >
                    <strong>{name.split(".").at(-1)}</strong>
                    <span className="palette-job-path">{name}</span>
                    <span className="palette-job-description">
                      {description}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </aside>
  );
}
