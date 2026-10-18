import { useEffect, useRef, useState } from "react";
import { loadMaps, locate, withTimeout } from "./mapkit.js";

export function MapCanvas({ places, token, theme, emptyMessage = "No locations to show" }) {
  const container = useRef(null);
  const cache = useRef(new Map());
  const [runtime, setRuntime] = useState(null);
  const [status, setStatus] = useState("loading");
  const [missing, setMissing] = useState([]);

  useEffect(() => {
    if (!token) return;
    let disposed = false, map, api;
    const failed = () => { if (!disposed) setStatus("error"); };
    setStatus("loading");
    withTimeout(loadMaps(token)).then(loaded => {
      if (disposed) return;
      api = loaded;
      api.addEventListener("error", failed);
      map = new api.Map(container.current, { showsUserLocation: false, showsUserLocationControl: false });
      setRuntime({ api, map });
    }).catch(failed);
    return () => {
      disposed = true;
      api?.removeEventListener("error", failed);
      map?.destroy();
      cache.current.clear();
      setRuntime(null);
    };
  }, [token]);

  useEffect(() => { if (runtime) runtime.map.colorScheme = theme || "adaptive"; }, [runtime, theme]);

  useEffect(() => {
    if (!runtime) return;
    const { api, map } = runtime;
    const controller = new AbortController();
    let disposed = false;
    setStatus("loading");
    setMissing([]);
    map.removeAnnotations([...map.annotations]);
    (async () => {
      const pins = [], unavailable = [];
      let requestFailed = false;
      for (const place of places) {
        if (disposed) return;
        let coordinate = cache.current.get(place.query);
        if (!coordinate) {
          try { coordinate = await locate(api, place, controller.signal); }
          catch {
            requestFailed = true;
          }
          if (coordinate) cache.current.set(place.query, coordinate);
        }
        if (disposed) return;
        if (coordinate) pins.push(new api.MarkerAnnotation(coordinate, { title: place.name, color: "#85652f" }));
        else unavailable.push(place.name);
      }
      if (pins.length) map.showItems(pins);
      setMissing(unavailable);
      setStatus(pins.length || !places.length ? "ready" : requestFailed ? "error" : "unresolved");
    })().catch(() => { if (!disposed) setStatus("error"); });
    return () => { disposed = true; controller.abort(); };
  }, [runtime, places]);

  const message = !places.length ? emptyMessage : !token ? "Apple Maps isn’t connected yet" : status === "loading" ? "Finding campus buildings…"
    : status === "error" ? "Apple Maps couldn’t load" : status === "unresolved" ? "No building matches confirmed" : null;
  return <div className="map-canvas-wrap">
    <div ref={container} className="map-canvas" aria-label="Campus building map" />
    {message && <div className="map-placeholder" role="status">
      <svg width="36" height="36" viewBox="0 0 32 32" fill="none" aria-hidden="true"><circle cx="16" cy="16" r="13" stroke="currentColor" strokeWidth="1.4"/><path d="m21 10-3 8-8 4 4-9 7-3Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>
      <strong>{message}</strong>
      {places.length > 0 && <span>{!token ? "Connect Apple Maps to see your course locations." : status === "error" ? "Check the map token and host permissions." : status === "unresolved" ? "These locations couldn’t be verified with Apple Maps." : ""}</span>}
    </div>}
    {status === "ready" && missing.length > 0 && <p className="map-unresolved" role="status">Location unconfirmed: {missing.join(" · ")}</p>}
  </div>;
}
