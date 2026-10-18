import { useEffect, useState } from "react";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";
import { readCoursesResult } from "../courses/tool-result.js";
import { DeadlineTimeline } from "./DeadlineTimeline.jsx";

export function DeadlinesApp({ bridge, onTeardown }) {
  const [state, setState] = useState({ status: "loading", view: null });
  useEffect(() => bridge.start({
    appName: "CourseLight Deadlines",
    onResult(result) {
      try { setState({ status: "ready", view: readCoursesResult(result) }); }
      catch { setState({ status: "error", view: null }); }
    },
    onError() { setState({ status: "error", view: null }); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme;
    },
    onTeardown,
  }), [bridge, onTeardown]);
  return <GlassProvider><main className="planner deadlines-panel" aria-label="Assignment deadline timeline">
    {state.status === "loading" && <p className="timeline-message" role="status">Reading deadlines…</p>}
    {state.status === "error" && <p className="timeline-message" role="alert">Deadlines couldn’t load. Ask ChatGPT to check CourseSite and try again.</p>}
    {state.status === "ready" && <DeadlineTimeline view={state.view} />}
  </main></GlassProvider>;
}
