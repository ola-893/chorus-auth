# Legacy CLI Dashboard

## Status

This document is archived. The terminal dashboard described here belonged to the earlier conflict-prediction experiments and is not part of the active auth control plane MVP.

## Current Operator Surface

The default operator experience is now the React dashboard launched by:

```bash
./run_frontend_demo.sh
```

That dashboard exposes the active control-plane concepts directly:

- connected accounts
- agent capability grants
- approval queue
- action timeline
- quarantine state

## When To Use The CLI Material

Only use the older CLI dashboard code if you are intentionally exploring or reviving the archived prediction-engine path.
