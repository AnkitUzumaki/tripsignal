# Data sources

TripSignal uses public feeds to provide context for a route and estimated travel window. Source availability, schemas, terms, and limits can change; the links below are the authoritative starting points for current usage details. The app is not affiliated with these providers.

| Source | Use in TripSignal | Coverage and interpretation | Documentation |
| --- | --- | --- | --- |
| National Weather Service (NWS) | Point hourly forecasts and active alerts near the origin and estimated destination windows | U.S. point forecasts and alert coverage. A point alert/forecast does not describe the full route or guarantee airport operating conditions. | [API documentation](https://www.weather.gov/documentation/services-web-api) |
| Aviation Weather Center (AWC) | Airport TAF text and active SIGMET GeoJSON | TAF is shown with a conservative estimated-window interpretation. SIGMET route matching is approximate and does not model the filed route, altitude, or aircraft. The integration uses the combined SIGMET endpoint; deprecated individual endpoints are not used. | [Data API](https://aviationweather.gov/data/api/) · [API changelog](https://aviationweather.gov/data/api/#changelog) |
| FAA NAS Status | Current National Airspace System status notices matched conservatively to selected airport codes | The public status feed is a broad operational snapshot. Airport matching is not equivalent to flight-specific delay or cancellation status. | [NAS Status](https://nasstatus.faa.gov/) |
| Open-Meteo | Independent hourly weather context near each airport | Secondary model context only. It is not a flight-delay prediction and may overlap with NWS/AWC evidence. | [API documentation](https://open-meteo.com/en/docs) |

## Request behavior

- Configure `CONTACT_EMAIL` in `.env` so request headers can identify this client where a provider requests it. Do not put a personal address into `.env.example`.
- Provider adapters use finite timeouts and the shared request client. Respect provider policies and rate limits; this prototype does not promise a particular polling cadence or service level.
- Successful responses may be cached locally. A stale cached response is labelled with its age and is not presented as a fresh live observation.
- A source can report usable data, a clear result within its coverage, no data for the requested window, failure, unsupported coverage, or stale cached data. These states are intentionally distinct.

## Interpreting combined evidence

Multiple feeds can describe the same weather system. TripSignal groups evidence into broad families and uses the strongest item in a family for the simple index to reduce obvious duplication. This does not establish statistical independence or eliminate all double counting. The index is an uncalibrated ranking aid, not a probability or operational decision.

Historical airport statistics, earthquake data, and air-quality readings are excluded from the headline assessment because they do not establish that this specific trip will be disrupted.
