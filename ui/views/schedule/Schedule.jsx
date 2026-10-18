import { useState } from "react";
import { WeeklyGrid } from "../../shared/schedule/WeeklyGrid.jsx";
import { ClassDetails } from "../../shared/schedule/ClassDetails.jsx";

export function Schedule({ view }) {
  const [optionIndex, setOptionIndex] = useState(0);
  const [selected, setSelected] = useState(null);
  const option = view.options[optionIndex];
  const proposed = view.mode === "proposed";
  return (
    <>
      {view.options.length > 1 && <nav className="schedule-options" aria-label="Potential schedules">
        {view.options.map((item, index) => <button type="button" key={item.id}
          aria-pressed={index === optionIndex} onClick={() => { setOptionIndex(index); setSelected(null); }}>
          {item.label}
        </button>)}
      </nav>}
      {option && option.sections.length > 0 ?
        <WeeklyGrid sections={option.sections} onSelect={setSelected} /> :
        <div className="schedule-empty">
          <h3>{proposed ? "No schedules match yet." : "No registered classes returned."}</h3>
          <p>{proposed ? "Ask ChatGPT to adjust the courses or schedule preferences."
            : "Check the selected term or your registration in Banner."}</p>
        </div>}
      {selected && <ClassDetails key={selected.crn} section={selected} proposed={proposed} onClose={() => setSelected(null)} />}
    </>
  );
}
