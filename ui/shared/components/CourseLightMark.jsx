export function CourseLightMark({ className = "" }) {
  return (
    <svg className={className} viewBox="0 0 28 34" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path className="bulb-globe" d="M9.5 23v-1.8c0-3.1-4.5-4.7-4.5-10.2a9 9 0 0 1 18 0c0 5.5-4.5 7.1-4.5 10.2V23Z" />
      <path className="bulb-highlight" d="M8.5 11A5.5 5.5 0 0 1 14 5.5" />
      <path className="bulb-filament" d="m10.5 12.5 3.5 3.5 3.5-3.5M14 16v7" />
      <path d="M9.5 26.5h9M10.5 29.5h7M12.5 32h3" />
    </svg>
  );
}
