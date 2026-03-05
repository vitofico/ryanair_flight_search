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
    <div className="progress-panel">
      <h2>Searching flights...</h2>
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      {progress ? (
        <p className="progress-label">{progress.message}</p>
      ) : (
        <p className="progress-label">Starting search...</p>
      )}
      <button className="btn btn-secondary" onClick={onCancel}>
        Cancel
      </button>
    </div>
  );
}
