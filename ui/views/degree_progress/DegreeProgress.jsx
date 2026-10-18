import { GlassSurface } from "../../shared/components/GlassSurface.jsx";

const percentage = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const gpa = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 3 });
const date = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

function ProgressRing({ progress, label, name = label }) {
  const progressText = progress == null ? "—" : percentage.format(progress);
  return <div className="completion-ring" role="progressbar" aria-label={`${name} completion`}
    aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress ?? undefined}
    aria-valuetext={progress == null ? "Completion unavailable" : `${progressText}% complete`}>
    <svg viewBox="0 0 180 180" aria-hidden="true">
      <circle className="ring-track" cx="90" cy="90" r="76" />
      {progress > 0 && <circle className="ring-value" cx="90" cy="90" r="76" pathLength="100"
        strokeDasharray={`${progress} 100`} transform="rotate(-90 90 90)" />}
    </svg>
    <div className="ring-label" aria-hidden="true"><strong>{progressText}{progress != null && <span>%</span>}</strong>
      <span>{label}</span></div>
  </div>;
}

export function DegreeProgress({ view }) {
  const majors = view.majors.length ? view.majors : [{ name: "Major", completion_percent: null }];
  return <GlassSurface className="degree-card">
    <header className="degree-heading"><h1>Degree progress</h1>
      {view.degrees.length > 0 && <p>{view.degrees.join(" · ")}</p>}
    </header>
    <div className="degree-metrics">
      <div className="progress-metric"><ProgressRing progress={view.completion_percent} label="Degree" /></div>
      {majors.map((major, index) => <div className="progress-metric" key={`${major.name}-${index}`}>
        <ProgressRing progress={major.completion_percent} label="Major" name={major.name} />
        {majors.length > 1 && <p className="major-name">{major.name}</p>}
      </div>)}
    </div>
    <div className="degree-gpa"><span>Cumulative GPA</span>
      <strong>{view.cumulative_gpa == null ? "—" : gpa.format(view.cumulative_gpa)}</strong>
    </div>
    <footer className="degree-footer"><span>{view.audit_date ? <>Audit · <time dateTime={view.audit_date}>{date.format(new Date(`${view.audit_date}T00:00:00Z`))}</time></> : "Audit date unavailable"}</span>
      <a href={view.source_url} target="_blank" rel="noopener noreferrer">Degree Works ↗</a>
    </footer>
  </GlassSurface>;
}
