# ATLAS Preparation Service

Clean Architecture package for Phase 5 — Intelligent Data Preparation.

## Responsibilities

- Generate cleaning plans from Phase 4 profiling outputs
- Build versioned, replayable cleaning recipes
- Human-in-the-loop approve / reject before mutating catalog versions
- Persist cleaned datasets as new immutable dataset versions

## API

Mounted under `/v1/preparation/*`.

## Agent

`agents/data_cleaning` re-exports `atlas_preparation.application.agent`.
