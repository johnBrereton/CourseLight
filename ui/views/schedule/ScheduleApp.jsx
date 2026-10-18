import { useEffect, useState } from "react";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";
import { readScheduleResult } from "./tool-result.js";
import { Schedule } from "./Schedule.jsx";

export function ScheduleApp({ bridge, onTeardown }) {
  const [state, setState] = useState({ status: "loading", view: null, revision: 0 });
  useEffect(() => bridge.start({
    appName: "CourseLight Schedule",
    onResult(result) {
      try {
        const view = readScheduleResult(result);
        setState((previous) => ({ status: "ready", view, revision: previous.revision + 1 }));
      } catch { setState((previous) => ({ ...previous, status: "error", view: null })); }
    },
    onError() { setState((previous) => ({ ...previous, status: "error", view: null })); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme;
    },
    onTeardown,
  }), [bridge, onTeardown]);
  return <GlassProvider><main className="planner schedule-panel" aria-label="Class schedule">
    {state.status === "loading" && <p className="schedule-empty" role="status">Reading your schedule…</p>}
    {state.status === "error" && <div className="schedule-empty" role="alert">
      <h2>The schedule couldn’t load.</h2><p>Ask ChatGPT to check Banner or your Lehigh sign-in and try again.</p>
    </div>}
    {state.status === "ready" && <Schedule key={state.revision} view={state.view} />}
  </main></GlassProvider>;
}
