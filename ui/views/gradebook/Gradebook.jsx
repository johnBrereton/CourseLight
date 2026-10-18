import { useState } from "react";
import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import { formatPercent } from "../../shared/grades/format.js";

function GradeTile({ item }) {
  const released = item.percent != null || !["—", "Not released"].includes(item.display_score);
  return <li className={`grade-tile${released ? "" : " is-ungraded"}`}>
    <a href={item.url} target="_blank" rel="noopener noreferrer" title={item.name}>
      <span className="grade-tile-name">{item.name}</span>
      <strong>{!released ? "—" : item.percent == null ? item.display_score : `${formatPercent(item.percent)}%`}</strong>
      <small>{item.percent != null && item.display_score.includes("/") ? item.display_score : released ? item.status : "Not released"}</small>
    </a>
  </li>;
}

export function Gradebook({ view }) {
  const [site, setSite] = useState(view.sources.find((source) => source.items.length)?.site ?? view.sources[0].site);
  const source = view.sources.find((item) => item.site === site);
  const items = source.items.filter((item) => item.kind === "assessment");
  const total = source.items.find((item) => item.kind === "course" && item.percent != null);
  const categories = source.items.filter((item) => item.kind === "category");
  return <GlassSurface className="grade-card">
    <header className="grade-heading"><div><h1>Grades</h1><p className="grade-course">{view.course_name}</p></div>
      {total && <div className="grade-reported"><strong>{formatPercent(total.percent)}%</strong><small>Reported total</small></div>}
    </header>
    <div className="grade-sites" role="group" aria-label="Grade source">{view.sources.map((item) =>
      <button type="button" key={item.site} aria-pressed={site === item.site} onClick={() => setSite(item.site)}>{item.name}</button>
    )}</div>
    {source.match_note && <p className="grade-note">{source.course_name} · {source.match_note}</p>}
    {source.notice && <p className="grade-note" role="status">{source.notice}</p>}
    {items.length ? <ul className="grade-grid">{items.map((item) => <GradeTile key={item.ref} item={item} />)}</ul> :
      !source.notice && <p className="grade-note">No grades have been returned yet.</p>}
    <footer className="grade-grid-footer"><span>— Not released</span>
      {source.url && <a href={source.url} target="_blank" rel="noopener noreferrer">Open {source.name} ↗</a>}
    </footer>
    {categories.length > 0 && <details className="grade-details"><summary>Category totals</summary>
      <dl className="grade-categories">{categories.map((item) => <div key={item.ref}>
        <dt>{item.name}</dt><dd>{item.percent == null ? item.display_score : `${formatPercent(item.percent)}%`}</dd>
      </div>)}</dl></details>}
  </GlassSurface>;
}
