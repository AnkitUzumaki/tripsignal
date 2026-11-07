# Design decisions and evidence semantics

## Product boundary

The prototype focuses on US air routes and serves a curated list of major US airports. It treats a trip as a route-level screening task and does not imply carrier-specific knowledge.

## Source states

| State | Meaning in this app |
| --- | --- |
| `data` | The source returned a usable response for this airport or route. |
| `clear` | The source returned successfully and reported no matching hazard or notice in its coverage. This is not a guarantee of normal operations. |
| `no_data` | The source returned an empty payload or had no data for the requested time window, so it could not report clear conditions. |
| `failed` | The request or response parsing failed and there was no cached response to use. |
| `unsupported` | The source returned HTTP 404 for the requested location/endpoint. |
| `stale` | A previous response was used after a live request failed; its age is shown. |

An empty alert result is not treated as proof of safe conditions. A source failure is not converted into a low score. If every signal is unknown, the score is withheld and the verdict is “Insufficient evidence.”

## Risk index

Each evidence item has a severity for triage. The scoring layer only counts the strongest signal in each broad family (weather, operations), reducing duplicate score inflation when NWS, TAF, and SIGMET data describe overlapping weather. The displayed index and thresholds are heuristic and need calibration against historic outcomes before being used as probability or policy.

Recommendations are linked to the signal titles that triggered them. They prompt airline confirmation and review; they do not recommend a particular alternate airport or assert that a traveler should rebook.

## Timing assumptions

The user supplies a local departure time and estimated duration. The app resolves both airports through IANA time zones, computes approximate arrival, and checks weather in a two-hour buffer around departure and arrival. TAF parsing covers common change groups and flight categories; unparsed source text is not classified as clear. SIGMET matching uses sampled points along a great-circle approximation with a 50 NM geometry buffer. This does not represent an airline's actual track, altitude, routing, or delay.

## Cache and offline demo

Successful public responses are cached under `data/cache/` with a configured TTL. If refresh fails, an older response may be used and is labelled stale with its age. The offline fixture is a separate deterministic mode with fabricated sample evidence; it does not reuse cached live observations.

## AI disclosure

AI assistance was used to review the design and help implement the prototype. The source adapters and heuristic rules require human validation. The prototype has not been calibrated, operationally approved, or assessed for real traveler decisions.
