import { useEffect, useState } from "react";
import { GlassProvider } from "../components/GlassSurface.jsx";

export function GradeViewApp({ bridge, onTeardown, name, readResult, View }) {
  const [state, setState] = useState({ status: "loading", view: null, revision: 0 });
  useEffect(() => bridge.start({
    appName: `CourseLight ${name}`,
    onResult(result) {
      try {
        const view = readResult(result);
        setState((previous) => ({ status: "ready", view, revision: previous.revision + 1 }));
      } catch { setState((previous) => ({ ...previous, status: "error", view: null })); }
    },
    onError() { setState((previous) => ({ ...previous, status: "error", view: null })); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme;
    },
    onTeardown,
  }), [bridge, onTeardown, name, readResult]);
  return <GlassProvider><main className="planner grade-panel" aria-label={name}>
    {state.status === "loading" && <p className="grade-message" role="status">Loading {name.toLowerCase()}…</p>}
    {state.status === "error" && <p className="grade-message" role="alert">This view couldn’t load. Ask ChatGPT to check the course and try again.</p>}
    {state.status === "ready" && <View key={state.revision} view={state.view} />}
  </main></GlassProvider>;
}
