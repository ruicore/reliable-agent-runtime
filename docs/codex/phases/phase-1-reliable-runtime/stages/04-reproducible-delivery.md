---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST04
status: complete
blocked_by: null
implementation_authorized: true
human_readable: false
---

# Stage 04: Reproducible Delivery

Purpose: turn verified behavior into an independently reproducible, reviewable public release candidate without expanding product scope.

Scope: PH1-D01..D06. Complete machine and human reports, canary redaction, repeatable full fault matrix, English reproduction instructions, clean Python 3.13/3.14 verification, and dependency/provenance/history/package/privacy review.

Implementation covers versioned minimized machine reports, concise human summaries,
safe representations and canary redaction, repeatable fault-signature tests,
English reproduction instructions, and `uv` verification on Python 3.13 and
3.14. Reports preserve independent-observation and unverified-boundary facts
without claiming them from Runtime state alone.

Local command/results record: [Stage 04 validation](../stage-04-validation.md).

Exit: AC-15, AC-16, AC-18 and the complete AC-01..18 regression pass; local
public-candidate gates pass; claims retain simulation and unverified boundaries.

This exit establishes Phase 1 validation readiness. Commit and push remain
ordinary repository operations; release and publication still require separate
explicit authorization.
