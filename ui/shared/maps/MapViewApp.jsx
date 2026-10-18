import { useEffect, useState } from "react";
import { GlassProvider } from "../components/GlassSurface.jsx";
import { CourseLightHeader } from "../components/CourseLightHeader.jsx";

export function MapViewApp({ bridge, readResult, View, name, onTeardown }) {
  const [state, setState] = useState({ status: "loading" });
  const [theme, setTheme] = useState();
  useEffect(() => bridge.start({
    appName: name,
    onResult(result, metadata) {
      try {
        const token = metadata?.["courselight/mapkit"]?.token;
        setState({ status: "ready", view: readResult(result),
          token: typeof token === "string" && token.length <= 8192 ? token : "" });
      } catch { setState({ status: "error" }); }
    },
    onError() { setState({ status: "error" }); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) {
        document.documentElement.dataset.theme = context.theme;
        setTheme(context.theme);
      }
    }, onTeardown,
  }), [bridge, name, readResult, onTeardown]);
  return <GlassProvider><main className="planner map-panel" aria-label={name}>
    <CourseLightHeader />
    {state.status === "loading" && <p className="map-message" role="status">Loading your map…</p>}
    {state.status === "error" && <p className="map-message" role="alert">The map data couldn’t load. Ask ChatGPT to check the connection and try again.</p>}
    {state.status === "ready" && <View view={state.view} token={state.token} theme={theme} />}
  </main></GlassProvider>;
}
