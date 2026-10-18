import { createContext, useContext, useEffect, useState } from "react";
import { Glass } from "@samasante/liquid-glass";
import "./glass-surface.css";

const darkOptics = {
  strength: 0.08, dispersion: 0, frost: 6,
  saturate: 1.05, specular: 1.15, sheen: 0.45, bend: 0.55, brightness: 0,
};

// Light backgrounds need less white specular lift to retain visible glass depth.
const lightOptics = { ...darkOptics, frost: 2, saturate: 1, specular: 0.6, sheen: 0.3 };

const GlassPreferences = createContext({ plain: false, dark: false });

export function GlassProvider({ children }) {
  const [plain, setPlain] = useState(false);
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const preference = window.matchMedia(
      "(prefers-reduced-transparency: reduce), (forced-colors: active)",
    );
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    const root = document.documentElement;
    const update = () => {
      setPlain(preference.matches);
      setDark(root.dataset.theme ? root.dataset.theme === "dark" : systemTheme.matches);
    };
    const themeObserver = new MutationObserver(update);
    themeObserver.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
    update();
    preference.addEventListener("change", update);
    systemTheme.addEventListener("change", update);
    return () => {
      preference.removeEventListener("change", update);
      systemTheme.removeEventListener("change", update);
      themeObserver.disconnect();
    };
  }, []);

  return <GlassPreferences.Provider value={{ plain, dark }}>{children}</GlassPreferences.Provider>;
}

export function GlassSurface({ children, className = "", style, ...props }) {
  const { plain, dark } = useContext(GlassPreferences);
  const classes = `glass-surface ${className}`;
  if (plain) return <div {...props} className={classes} style={style}>{children}</div>;
  return <Glass {...props} className={classes} style={{ display: "block", ...style }} optics={dark ? darkOptics : lightOptics}>
    {/* A non-null child keeps decorative surfaces in the library’s material mode. */}
    {children ?? <></>}
  </Glass>;
}
