# Legacy Integration Design

## Status

This document is archived. It describes an older universal-ingestion direction for the pre-refactor Chorus platform and is not part of the active auth control plane MVP.

## Why It Still Exists

- it captures historical thinking about external system ingestion
- some language may still be useful if Chorus later exposes a broader multi-system intake layer
- it provides context for older prototype code that still exists in the repository

## Current Replacement

For the active system design, use:

- [System Overview](system_overview.md)
- [Auth Control Plane Design](../planning/specs/auth-control-plane/design.md)

## Current Default Integration Story

The current MVP does not depend on a universal Kafka ingestion layer. Instead, it focuses on:

- connected Gmail and GitHub accounts
- explicit agent capability grants
- approval-aware action execution
- audit and quarantine visibility in the dashboard
