import { useId } from "react";
import clsx from "clsx";

interface DateRangeFieldProps {
  start: string;
  end: string;
  onStartChange: (v: string) => void;
  onEndChange: (v: string) => void;
}

export default function DateRangeField({
  start,
  end,
  onStartChange,
  onEndChange,
}: DateRangeFieldProps) {
  const startId = useId();
  const endId = useId();
  const invalid = start && end && start > end;

  return (
    <div className="field-row">
      <div className="field">
        <label className="field-label" htmlFor={startId}>
          Start Date
        </label>
        <input
          id={startId}
          type="date"
          className="field-input"
          value={start}
          onChange={(e) => onStartChange(e.target.value)}
        />
      </div>
      <div className="field">
        <label className="field-label" htmlFor={endId}>
          End Date
        </label>
        <input
          id={endId}
          type="date"
          className={clsx("field-input", invalid && "field-input--error")}
          value={end}
          onChange={(e) => onEndChange(e.target.value)}
        />
        {invalid && (
          <span className="field-error">End must be on or after start</span>
        )}
      </div>
    </div>
  );
}
