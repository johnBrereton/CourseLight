import { useId, useState } from "react";
import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import { formatPercent, requiredPercent } from "../../shared/grades/format.js";
import { ScoreBar } from "./ScoreBar.jsx";

function Calculator({ projection }) {
  const [target, setTarget] = useState(projection.target);
  const [overrides, setOverrides] = useState({});
  const inputId = useId();
  const remaining = projection.work.filter((item) => item.percent == null);
  const secured = projection.work.reduce((sum, item) => sum + (item.percent ?? 0) * item.weight / 100, 0);
  const remainingWeight = remaining.reduce((sum, item) => sum + item.weight, 0);
  const validTarget = target !== "" && Number.isFinite(Number(target)) && Number(target) >= 0 && Number(target) <= 100;
  const needed = validTarget && remainingWeight > 0 ? (Number(target) - secured) / remainingWeight * 100 : null;
  const baseline = needed == null ? 0 : Math.max(0, Math.min(100, needed));
  const score = (item) => overrides[item.name] ?? baseline;
  const projected = secured + remaining.reduce((sum, item) => sum + score(item) * item.weight / 100, 0);
  const neededOn = (selected) => (Number(target) - secured - remaining.reduce((sum, item) =>
    item === selected ? sum : sum + score(item) * item.weight / 100, 0)) / selected.weight * 100;
  return <>
    <div className="target-overview">
      <div className="target-estimate" aria-live="polite" aria-atomic="true"><span>Projected final</span>
        <strong>{validTarget ? formatPercent(projected) : "—"}<small>%</small></strong></div>
      <label className="target-input" htmlFor={inputId}>Your target<span><input id={inputId} type="number" min="0" max="100" step="0.1"
        value={target} aria-invalid={!validTarget} onChange={(event) => setTarget(event.target.value)} />%</span></label>
    </div>
    {validTarget && remaining.length > 0 && <>
      <div className="target-chart" aria-label="Adjust estimated scores">
        <div className="score-axis" aria-hidden="true"><span>100</span><span>50</span><span>0</span></div>
        <ul className="score-bars">{remaining.map((item, index) => {
          const required = neededOn(item);
          const detail = required > 100 ? ">100% needed" : required <= 0 ? "0% needed" : `${requiredPercent(required)}% needed`;
          return <ScoreBar key={item.name} item={item} value={score(item)} needed={detail} index={index}
            onChange={(value) => setOverrides((previous) => ({ ...previous, [item.name]: value }))} />;
        })}</ul>
      </div>
      <div className="target-actions">
        <button type="button" onClick={() => setOverrides({})}>Reset</button></div>
    </>}
    <details className="grade-details"><summary>Syllabus & assumptions</summary>
      <p role="status">{!validTarget ? "Enter a target from 0 to 100%." : remainingWeight === 0 ? "All scores in this scenario are released." :
      needed > 100 ? `Target exceeds the ${formatPercent(secured + remainingWeight)}% maximum.` :
      needed <= 0 ? "Your released scores already cover this target." :
      `${requiredPercent(needed)}% average needed across the remaining ${formatPercent(remainingWeight)}% of your grade.`}</p>
      <p>“Needed” holds your other bar estimates fixed.</p>
      <p>{projection.explanation}</p>
      {projection.assumptions.length > 0 && <ul>{projection.assumptions.map((note) => <li key={note}>{note}</li>)}</ul>}
      <dl className="target-weights">{projection.work.map((item) => <div key={item.name}>
        <dt>{item.name}<small>{item.percent == null ? "Unresolved" : `${formatPercent(item.percent)}% released`}</small></dt>
        <dd>{formatPercent(item.weight)}%</dd></div>)}</dl>
      <p>Uses fixed weights and 0–100% on unresolved work. The target is a percentage, not a letter-grade cutoff. Estimates stay in this view.</p>
      <a href={projection.source_url} target="_blank" rel="noopener noreferrer">Read syllabus ↗</a>
    </details>
  </>;
}

export function GradeTarget({ view }) {
  return <GlassSurface className="grade-card target-card">
    <header className="grade-heading"><div><h1>What you need</h1><p className="grade-course">{view.course_name}</p></div></header>
    {view.projection ? <Calculator projection={view.projection} /> : <>
      <p className="grade-note">{view.projection_notice}</p>
      {view.syllabi.map((syllabus) => <a className="grade-link" key={syllabus.module_id} href={syllabus.url} target="_blank" rel="noopener noreferrer">{syllabus.title} ↗</a>)}
    </>}
  </GlassSurface>;
}
