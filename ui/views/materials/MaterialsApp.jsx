import { useEffect, useState } from "react";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";
import { MaterialGroup } from "./MaterialGroup.jsx";
import { readMaterialsResult } from "./tool-result.js";

export function MaterialsApp({ bridge, onTeardown }) {
  const [state, setState] = useState({ status: "loading", view: null });
  useEffect(() => bridge.start({
    appName: "CourseLight Study Materials",
    onResult(result) {
      try { setState({ status: "ready", view: readMaterialsResult(result) }); }
      catch { setState({ status: "error", view: null }); }
    },
    onError() { setState({ status: "error", view: null }); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme;
    },
    onTeardown,
  }), [bridge, onTeardown]);
  return <GlassProvider><main className="planner materials-panel" aria-label="Study materials">
    {state.status === "loading" && <p className="materials-message" role="status">Gathering study materials…</p>}
    {state.status === "error" && <p className="materials-message" role="alert">Materials couldn’t load. Ask ChatGPT to check CourseSite and try again.</p>}
    {state.status === "ready" && (state.view.groups.length ? <div className="materials-stack">
      {state.view.groups.map((group, index) => <MaterialGroup key={`${state.view.course_id}-${index}-${group.title}`} group={group} />)}
    </div> : <p className="materials-message">No study materials returned. Try another topic or open CourseSite.</p>)}
  </main></GlassProvider>;
}
