import { useEffect, useState } from "react";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";
import { CourseLightHeader } from "../../shared/components/CourseLightHeader.jsx";
import { DegreeProgress } from "./DegreeProgress.jsx";
import { readDegreeProgressResult } from "./tool-result.js";

export function DegreeProgressApp({ bridge, onTeardown }) {
  const [state, setState] = useState({ status: "loading", view: null });
  useEffect(() => bridge.start({
    appName: "CourseLight Degree Progress",
    onResult(result) {
      try { setState({ status: "ready", view: readDegreeProgressResult(result) }); }
      catch { setState({ status: "error", view: null }); }
    },
    onError() { setState({ status: "error", view: null }); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme;
    },
    onTeardown,
  }), [bridge, onTeardown]);
  return <GlassProvider><main className="planner degree-panel" aria-label="Degree progress">
    <CourseLightHeader />
    {state.status === "loading" && <p className="degree-message" role="status">Reading your degree progress…</p>}
    {state.status === "error" && <p className="degree-message" role="alert">Degree progress couldn’t load. Ask ChatGPT to check your Lehigh connection and try again.</p>}
    {state.status === "ready" && <DegreeProgress view={state.view} />}
  </main></GlassProvider>;
}
