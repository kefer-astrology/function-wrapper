# Licensing

## Current license: GNU AGPL v3 (unchanged)

This repository is licensed under the GNU Affero General Public License v3
(`LICENSE`). Attribution: `NOTICE`. Third-party packages and data:
`THIRD_PARTY_NOTICES.md`.

## Planned: MIT

The target is MIT, matching `tauri-application` and `kefer-contracts`.
**The license has not been changed.** Removing Kerykeion/Swiss Ephemeris (done
in August 2026) removed the dependency reason for AGPL, but it does not by
itself make existing code MIT. Relicensing requires every copyright holder of
the current code to agree. Status of the Phase 1 audit:

| Requirement | Status |
|---|---|
| No GPL/AGPL runtime dependency | **Met.** Runtime is MIT/BSD/Apache/PSF/MPL-2.0 (unmodified) + ODbL data. GPL appears only in build tools (PyInstaller, bootloader exception) and the optional Kivy UI extra (docutils, pycairo LGPL/MPL). |
| No copied AGPL/GPL code | **Met** as far as Git history shows: Kerykeion was imported as a library (never vendored; no Kerykeion/Swiss Ephemeris source or author headers ever committed). Replacement routines are textbook derivations or ports from the MIT Rust implementation by the same author. |
| Consent of all copyright holders | **Open.** 99 % of surviving lines by Kube Kubow (two Git identities, to be confirmed as one person). 3 trivial lines (an import, 2 blank lines) survive from the 2023 prototype by Daniel Bajaja; written relicensing consent is still recommended. |
| No employer / third-party claims | **Open.** To be confirmed by the author. |
| AI-assisted contributions | ~5 % of surviving lines come from commits co-authored by an AI assistant; no third-party rights are known, policy to be documented. |
| Third-party data in this repo | `source/*.bsp` (JPL, public domain), `source/mpc_bodies.dat` (MPC, acknowledgement), `source/starfisher_sample.sfs` (third-party format test fixture) — **excluded** from any relicensing. |

Earlier published versions remain available under their original licenses
(GPL-3.0 until 2025-03-20, AGPL-3.0 afterwards); relicensing affects new
versions only.

## Rights holder

Copyright is held by the contributors. A grant of economic rights to the
Kefer Astrology nonprofit is planned; see
`kefer-contracts/governance/CONTRIBUTOR-AGREEMENT-DRAFT.md` (draft, not in
effect).
