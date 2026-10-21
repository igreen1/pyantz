/** A message which goes away by itself. */
import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { clearNotice } from "../store/slices/uiSlice";

const SHOWN_FOR_MS = 8000;

export default function Notice() {
  const dispatch = useAppDispatch();
  const notice = useAppSelector((state) => state.uiOptions.notice);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => dispatch(clearNotice()), SHOWN_FOR_MS);
    return () => clearTimeout(timer);
  }, [notice, dispatch]);

  if (!notice) return null;
  return (
    <div
      className={`notice alert alert-${notice.kind === "error" ? "danger" : "info"} d-flex gap-3 align-items-start`}
      role={notice.kind === "error" ? "alert" : "status"}
    >
      <span>{notice.text}</span>
      <button
        type="button"
        className="btn-close"
        aria-label="Dismiss"
        onClick={() => dispatch(clearNotice())}
      />
    </div>
  );
}
