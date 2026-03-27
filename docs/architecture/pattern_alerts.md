# Legacy Pattern Alerts

## Status

This document is archived. Pattern-alert concepts came from the earlier immune-system product framing and are no longer part of the primary MVP story.

## What Still Carries Forward

Some ideas from the old alert system influenced the current control plane:

- repeated unsafe behavior should escalate
- explanations should remain visible to the operator
- intervention state must be auditable

Those ideas now surface as:

- risk explanations
- approval requirements
- block decisions
- quarantine enforcement

## Current Replacement

For the active behavior model, use:

- [System Overview](system_overview.md)
- [Auth Control Plane Requirements](../planning/specs/auth-control-plane/requirements.md)
