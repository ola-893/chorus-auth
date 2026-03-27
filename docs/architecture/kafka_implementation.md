# Legacy Kafka Implementation

## Status

This document is archived. Kafka is not part of the default auth control plane MVP path.

## Historical Context

Earlier Chorus experiments used Kafka as part of a broader event-streaming architecture for agent message ingestion and conflict monitoring. That work remains in the repository for reference, but it is no longer required to run the seeded delegated-action demo.

## Current Default Path

The active control plane uses:

- FastAPI request handling
- SQLite persistence
- optional Redis live fanout
- mock-first Gmail and GitHub provider adapters

If Kafka is revisited later, it should return as an optional extension rather than a required demo dependency.
