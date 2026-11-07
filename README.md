# TripSignal

TripSignal is a small, dependency-free prototype for screening a U.S. air route for public disruption signals. It combines weather and aviation operations feeds into an evidence-led brief, shows source coverage and freshness, and suggests cautious next steps.

The displayed score is a **rule-based directional risk index**. It is not a calibrated probability, a flight-specific status, or a guarantee of normal operations. TripSignal is an exploration prototype and is not intended for operational or safety-critical decisions.

## Features

- U.S. route input from a curated list of major airports, with airport-local time zones.
- Estimated departure and arrival weather windows based on a user-entered flight duration.
- Evidence from the National Weather Service (NWS), Aviation Weather Center (AWC), FAA NAS Status, and Open-Meteo.
- Visible source status, observation timestamps, evidence links, and stale-cache labels.
- A deterministic offline fixture for demos when live feeds are unavailable.
- Explainable heuristic scoring with source families to limit obvious duplicate counting.

## Quick start

Requirements: Python 3.10 or later and internet access for live assessments. The application uses only the Python standard library; it requires no API key or third-party package.

```sh
git clone https://github.com/AnkitUzumaki/tripsignal.git
cd tripsignal
python3 -m venv --without-pip .venv
cp .env.example .env
```

Edit `.env` and replace the placeholder `CONTACT_EMAIL` with an address you control. Then start the local server:

```sh
./run.sh
```

Open <http://127.0.0.1:8000>. Choose the origin, destination, travel date, local departure time, and estimated flight duration. The default route is JFK → SFO. Stop the server with Ctrl-C.

To use the offline demo, select **Use offline demo fixture** in the interface. Fixture evidence is fabricated and labelled in the app; fixture mode makes no live source requests.

### Configuration

The launcher reads `.env` automatically. Environment variables can also be set in the shell:

```sh
HOST=127.0.0.1 PORT=8000 CONTACT_EMAIL=you@example.com ./run.sh
```

`CONTACT_EMAIL` is used in identifying API request headers where a provider asks for client identification. Optional behavior such as source timeouts, cache lifetime, and score thresholds is in [`config/settings.json`](config/settings.json).

Keep the server bound to loopback for local use. Python's built-in HTTP server is suitable for a local demonstration only; it is not hardened for internet-facing deployment.

## How an assessment works

1. The service resolves the selected airports and converts the departure time to UTC using each airport's IANA time zone.
2. It estimates arrival using the duration supplied by the user.
3. Provider adapters fetch airport weather, alerts, TAFs, route SIGMETs, and FAA notices where supported.
4. The service records each source's result state and evidence separately. A failed or empty source is not silently treated as clear.
5. The scoring layer considers the strongest relevant evidence in broad weather and operations families, then links suggested next steps to the evidence that triggered them.

See [design decisions](docs/DECISIONS.md), [source notes](docs/SOURCES.md), and the [demo walkthrough](docs/DEMO.md) for implementation choices and interpretation details.

## Project structure

```text
app.py                     Application entry point
travelrisk/
  config.py                Settings and static data loading
  server.py                HTTP routes and request bounds
  service.py               Assessment orchestration
  time_windows.py          Local-time and UTC window conversion
  scoring.py               Heuristic index and evidence-linked actions
  http_client.py           Request timeouts and stale disk cache
  models.py                Evidence and source-status records
  providers/               External-source adapters
  fixtures.py              Offline deterministic fixture mode
data/
  airports.json            Supported airports and IANA time zones
  fixtures/                Fabricated demo assessment
config/settings.json       Timeouts, cache TTL, and index thresholds
static/                    HTML, CSS, and JavaScript interface
docs/                      Design, source, and demo documentation
```

## Data handling and security

- Do not commit `.env`, credentials, personal data, or runtime cache contents.
- `.env.example` contains placeholders only. Set a valid contact address before making live requests.
- Live responses may be cached under `data/cache/`. Cached fallback evidence is labelled stale with its age.
- The app does not request or store traveler names, ticket numbers, or airline account credentials.
- The local server has no authentication or access control. Do not expose it to a public network.

Report suspected security issues privately as described in [SECURITY.md](SECURITY.md).

## Current limitations

- Airport coverage is a curated list of U.S. airports; global airport resolution is out of scope.
- The departure and arrival weather windows are approximate, using a two-hour buffer around each estimated time. The selected duration is not a flight schedule.
- SIGMET matching samples a great-circle route with an approximate corridor. This is not a filed route, altitude-aware analysis, or full aviation weather briefing.
- TAF interpretation handles common forecast change groups conservatively; raw source text remains available for inspection.
- FAA XML matching is conservative and is not a validated operational event model.
- Public feeds can be delayed, unavailable, changed, or rate limited. A successful empty result only describes the source's coverage, not whether a trip will operate normally.
- The index has not been calibrated or back-tested against flight outcomes. Correlated inputs can still describe the same underlying weather.
- There is no carrier-specific flight status, schedule, NOTAM interpretation, alert delivery, monitoring, authentication, or production deployment configuration.

## Contributing

This is a compact prototype. Bug reports and focused improvements are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) for local development conventions. Before extending a source integration, check its current documentation and usage limits.

## License

No license has been selected. Until one is added, the repository is publicly viewable, but reuse and redistribution are not granted by an open-source license.
