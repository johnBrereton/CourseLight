import { useId } from "react";
import { formatPercent } from "../../shared/grades/format.js";

export function ScoreBar({ item, value, needed, onChange, index }) {
  const id = useId();
  return <li className={`score-column score-color-${index % 4}`}>
    <output className="score-value" htmlFor={id}>{formatPercent(value)}<span>%</span></output>
    <div className="score-track" style={{ "--score": `${value}%` }}>
      <div className="score-fill" aria-hidden="true"><span className="score-grip" /></div>
      <input id={id} className="score-slider" type="range" min="0" max="100" step="0.1" value={value}
        aria-orientation="vertical" aria-label={item.name} aria-valuetext={`${formatPercent(value)} percent`}
        aria-describedby={`${id}-detail`} onChange={(event) => onChange(Number(event.target.value))} />
    </div>
    <label className="score-label" htmlFor={id}>{item.name}</label>
    <small>{formatPercent(item.weight)}% weight</small>
    <span id={`${id}-detail`} className="score-required">{needed}</span>
  </li>;
}
