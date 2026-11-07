# Contributing

Thanks for considering an improvement. Keep changes focused and preserve the prototype's central behavior: show the evidence, source coverage, timestamps, assumptions, and uncertainty alongside any risk summary.

## Local setup

1. Use Python 3.10 or later.
2. Clone the repository and create the environment described in the README.
3. Copy `.env.example` to `.env` and set `CONTACT_EMAIL` before requesting live data.
4. Run `./run.sh` and exercise the relevant live or offline-demo path.

The application currently uses the Python standard library only. Avoid adding dependencies unless they provide clear value and are documented.

## Change guidelines

- Keep provider-specific parsing inside the corresponding adapter.
- Keep missing, failed, unsupported, clear, and stale source states distinct.
- Keep recommendations cautious and tied to visible evidence.
- Do not describe the heuristic index as a probability or guarantee.
- Update the relevant documentation when behavior, source usage, assumptions, or configuration changes.
- Never commit secrets, `.env`, runtime cache data, or personal travel information.

## Pull requests

Describe the user-visible change, the source or logic affected, assumptions introduced, and how you checked it. Include screenshots for meaningful interface changes and avoid including live personal or sensitive data.
