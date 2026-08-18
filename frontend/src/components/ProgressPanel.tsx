import type { ProgressInfo } from "../api/client";

interface ProgressPanelProps {
  progress: ProgressInfo | null;
  onCancel: () => void;
}

export default function ProgressPanel({
  progress,
  onCancel,
}: ProgressPanelProps) {
  const pct = progress ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <section className="progress-panel" aria-busy="true">
      <div className="progress-head">
        <h2 className="progress-title">
          <span className="progress-dot" aria-hidden="true" />
          Searching flights...
        </h2>
        <span className="progress-percent">{pct}%</span>
      </div>

      <div
        className="progress-bar-track"
        role="progressbar"
        aria-label="Search progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>

      <div className="progress-meta" aria-live="polite">
        {progress ? (
          <p className="progress-message">{progress.message}</p>
        ) : (
          <p className="progress-message">Starting search...</p>
        )}
        {progress && (
          <span className="progress-count">
            {progress.current} / {progress.total}
          </span>
        )}
      </div>

      <button className="btn btn-secondary" onClick={onCancel}>
        Cancel
      </button>
    </section>
  );
}
