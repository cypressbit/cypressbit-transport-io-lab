# CLAUDE_NOTES.md

Build notes for the CypressBit Transportation I-O Modeling Lab.
This file records AI-assisted implementation decisions, deviations, and known gaps
for the benefit of future developers and reviewers.

---

## Build Information

- **Build date:** 2026-06-24
- **Instructions source:** `CypressBit_Transportation_IO_Modeling_Lab_Instructions.md`
- **Implementation approach:** Staged build (12 discrete stages, one per session)

---

## Architecture Decisions

### Package layout
Using a `src/` layout (`src/cb_transport_io_lab/`). This prevents accidental imports
of the uninstalled package during development and is the current Python packaging
best practice. `tool.setuptools.packages.find` is set to `where = ["src"]`.

### Data models
**Pydantic v2** is used throughout. The v2 API differs from v1 in several ways:
- `model_validator` replaces `@validator`
- Field validation uses `Field(gt=0)` etc.
- `model_dump()` replaces `dict()`

### Dashboard API
**Shiny Express API** (`from shiny.express import input, output, render, ui`) is used
rather than the traditional `App(ui, server)` pattern. Express is more concise and
idiomatic for single-file dashboards. The file is self-contained with module-level
`@render` decorators.

### Charts
**matplotlib** is used for all dashboard charts instead of Plotly. This avoids any
CDN dependency (Shiny's CSP blocks external scripts) and keeps the Docker image
smaller. Charts are rendered via `@render.plot`.

### CLI module
The CLI entry point is `cb_transport_io_lab.cli:main`. The module supports both
`cb-io-lab <command>` (installed script) and `python -m cb_transport_io_lab.cli
<command>` (module execution).

### Numerical safeguards
- `MIN_OUTPUT_THRESHOLD = 1.0` (dollar) prevents division-by-zero in A matrix
- `MAX_CONDITION_NUMBER = 1e12` detects near-singular `(I - A)` matrices
- `numpy.linalg.solve` is used for scenario calculations (more stable than explicit
  inverse multiplication); `numpy.linalg.inv` is used only to expose L for docs

### Induced effects
The induced-effect method is a simplified **Type I.5 approximation**:
labor income → marginal consumption share → household final demand vector → L @ f.
This is NOT a validated RIMS II or IMPLAN-style Type II multiplier. It is labeled
as a prototype throughout the code and documentation.

---

## Structure Deviations from Spec

None. All files and directories from Section 3 of the instructions are present.

---

## Known Limitations

_(To be filled in during Stage 12 — Verify)_

- [ ] No official BEA, BLS, or FHWA data — synthetic data only
- [ ] Induced effects are simplified; not cross-validated against established multipliers
- [ ] No regional disaggregation (national-level model only)
- [ ] Mypy type checking may show warnings in dashboard code (Shiny's dynamic patterns)
- [ ] Dockerfile not tested in a live container registry environment
- [ ] Section 508 compliance not formally verified — design intentions only
- [ ] Additional items to be added after Stage 12 verification run

---

## Files Not Matching Spec

_(To be filled in after all stages complete)_

None identified so far.
