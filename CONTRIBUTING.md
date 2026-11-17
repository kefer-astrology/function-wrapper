# Contributing

## Calculations

- This package is an **independent** Skyfield implementation. It must conform
  to `kefer-contracts` (pinned in `kefer-contracts.lock`); run
  `python -m unittest discover -s tests` with the contracts available (see
  `tests/contracts_location.py`).
- Never substitute a calculation silently: unsupported engines, house
  systems, zodiac settings or approximated bodies must add a warning code
  documented in `kefer-contracts/CONVENTIONS.md`.
- Do not add GPL/AGPL dependencies or code, Swiss Ephemeris code or data, or
  Kerykeion. Runtime dependencies must be MIT-compatible; regenerate
  `THIRD_PARTY_NOTICES.md` (`python -m devtools.generate_third_party_notices`).
- Lockfiles are compiled with Python 3.11 (`pip-compile` on 3.11); supported
  Python versions are 3.11–3.14.

## Licensing of contributions

The repository is currently AGPL-3.0 with a planned move to MIT (see
`LICENSING.md`). **By submitting a contribution you license it under both the
GNU AGPL v3 and the MIT License**, so that it does not need separate consent
when the repository is relicensed. Sign off every commit (`git commit -s`,
Developer Certificate of Origin) and disclose AI-generated material with a
`Co-authored-by:` trailer.

*(Proposed policy: takes effect when the maintainers merge this file.)*
