# Performance Guide

The auth control plane MVP favors clarity and reliability over speculative optimization.

## Current Priorities

- Fast page hydration for the dashboard
- Low-latency action request handling for mock provider flows
- Predictable seeded demo startup
- Safe fallback behavior when Gemini is unavailable

## Current Strategy

- SQLite keeps the local persistence path simple and portable.
- The in-process event broker keeps local websocket fanout simple.
- Provider adapters are mock-first, so execution stays deterministic in demo mode.
- The frontend refetches compact datasets instead of maintaining a complex client cache.

## When To Optimize

Only optimize after one of these shows up:

- slow dashboard load with realistic demo data
- delayed approval resolution in the local loop
- websocket fanout lag
- provider execution bottlenecks in live mode

## What Not To Prioritize For The MVP

- Kafka throughput tuning
- external APM instrumentation as a demo dependency
- voice pipeline latency
- deep graph analytics for the older immune-system experiments
