# Apple Maps setup

The course map and study-room view share `ui/shared/maps/MapCanvas.jsx` and Apple's
official `@apple/mapkit-loader`. The class tool reads Banner once. The browser
uses verified campus coordinates when available, otherwise searches public
building names, and drops pins on confirmed matches. Course chips
show or hide their buildings locally. There is no timetable or route calculation.
Course titles, instructors, class times, account identities and device location
are not sent to Apple. Ambiguous or unmatched buildings remain unresolved.

## Configure the local token

1. Create a **MapKit JS** token in [Apple Developer → Maps tokens](https://developer.apple.com/help/account/service-configurations/maps-tokens/).
2. Restrict it to the actual web origins where the widget runs. The local review
   uses `127.0.0.1`. ChatGPT's default widget origin is
   `https://web-sandbox.oaiusercontent.com`; verify the actual iframe origin when
   connecting. For a dedicated origin, configure `APPLE_MAPS_WIDGET_DOMAIN` and
   restrict the token to that host instead. The MCP tunnel URL is not the map's origin.
3. Set `APPLE_MAPS_TOKEN=` in the ignored `.env`. Use a browser web token, never
   an Apple `.p8` signing key. Existing process environment variables take
   precedence. Restart the MCP process after editing the environment.
4. Refresh the connected plugin's tools/resources, then ask to map your classes.
   `show_course_map(term, on_date)` shows course buildings for the selected week.

The token is returned in tool-result `_meta["courselight/mapkit"]` for the
component only. It is not included in structured content, text fallbacks,
generated bundles, source HTML, or the model transcript. The bridge passes
metadata as the second argument to `onResult`.

Only Apple MapKit subdomains are allowlisted for scripts, assets and requests.
The host controls worker/blob and WebAssembly policy, which MapKit needs. Local
rendering does not establish ChatGPT sandbox compatibility. Blocked scripts,
expired tokens, timeouts and unresolved buildings show a map status. No token
means no Apple SDK load or API request.

## Course locations

`lehigh._meetings` retains separate building and room fields from Banner. The
schedule adapter passes them to `course_map/service.py`. Meeting start/end dates
are applied; holidays and cancellations are not checked. Buildings are shared
between courses, so a pin remains visible while any selected course uses it.
The small building catalog in `buildings.py` comes from [Lehigh’s official
campus map](https://www2.lehigh.edu/map), checked October 18, 2026. Other buildings
use conservative Apple searches. Coordinates are cached only while the component
is mounted. Nothing is booked,
registered or saved.

## 25Live handoff

See `../study_rooms/README.md`. The study-room resource and React view are ready;
the reservation tool remains unregistered until the real provider reader is
passed in. This scaffold never creates a booking or reports a fake one.

## References

- [Apple Maps token setup](https://developer.apple.com/documentation/mapkitjs/creating-a-maps-token)
- [Official loader and CSP requirements](https://developer.apple.com/documentation/mapkitjs/loading-the-latest-version-of-mapkit-js)
- [ChatGPT component metadata](https://developers.openai.com/plugins/reference)
