import { useId, useLayoutEffect, useRef, useState } from "react";
import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import chevron from "../../shared/assets/icons/chevron-down.svg";

function fileMeta(item) {
  if (!item.filename) return "CourseSite resource";
  const extension = item.filename.split(".").pop().toUpperCase();
  const type = /^[A-Z0-9]{1,8}$/.test(extension) ? extension : "File";
  if (item.size == null) return type;
  const size = item.size < 1000000 ? `${Math.max(1, Math.round(item.size / 1000))} KB` : `${(item.size / 1000000).toFixed(1)} MB`;
  return `${type} · ${size}`;
}

export function MaterialGroup({ group }) {
  const [open, setOpen] = useState(false);
  const headerRef = useRef(null);
  const contentRef = useRef(null);
  const [materialHeight, setMaterialHeight] = useState(0);
  useLayoutEffect(() => {
    // Keep the glass at its natural size while the disclosure reveals it.
    const measure = () => setMaterialHeight(headerRef.current.offsetHeight + contentRef.current.offsetHeight);
    const observer = new ResizeObserver(measure);
    observer.observe(headerRef.current);
    observer.observe(contentRef.current);
    measure();
    return () => observer.disconnect();
  }, []);
  const panelId = useId();
  const buttonId = useId();
  return <article className={`material-group${open ? " is-open" : ""}`} style={{ "--material-height": `${materialHeight}px` }}>
    <GlassSurface className="material-glass" aria-hidden="true" />
    <h2 className="material-heading" ref={headerRef}>
      <button id={buttonId} className="material-toggle" type="button" aria-expanded={open}
        aria-controls={panelId} onClick={() => setOpen(!open)}>
        <span className="material-label"><span className="material-title">{group.title}</span>
          <span className="material-count">{group.items.length} {group.items.length === 1 ? "material" : "materials"}</span>
        </span>
        <img className="material-chevron" src={chevron} alt="" aria-hidden="true" />
      </button>
    </h2>
    <div id={panelId} className="material-disclosure" role="region" aria-labelledby={buttonId} aria-hidden={!open} inert={!open}>
      <div className="material-content"><div className="material-content-inner" ref={contentRef}>
        {group.items.length ? <ul className="material-list">
          {group.items.map((item, index) => <li className="material-row" key={`${item.module_id}-${index}`}>
            <div className="material-info">
              <a className="material-name" href={item.source_url} target="_blank" rel="noopener noreferrer">{item.name}</a>
              <span className="material-meta" title={item.filename ?? item.section}>{fileMeta(item)}</span>
              {group.items.some((other) => other !== item && other.module_id === item.module_id) && <span className="material-filename">{item.filename}</span>}
            </div>
            <a className="material-action" href={item.download_url ?? item.source_url} target="_blank" rel="noopener noreferrer"
              aria-label={`${item.download_url ? "Download" : "Open"} ${item.filename ?? item.name}`}>
              {item.download_url ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M5 16v4h14v-4" /></svg> : null}
              {item.download_url ? "Download" : "Open"}
            </a>
          </li>)}
        </ul> : <p className="material-notice">No accessible materials in this group.</p>}
        {group.notice && <p className="material-notice" role="note">{group.notice}</p>}
      </div></div>
    </div>
  </article>;
}
