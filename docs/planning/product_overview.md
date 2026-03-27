# Chorus Product Overview

## Vision

Chorus should be the safest way to let AI agents act on behalf of a user across real tools like Gmail, GitHub, calendars, and internal systems.

## Problem Statement

Most agent products still treat authorization as an afterthought. They let agents operate with broad permissions, weak human review, and poor visibility into what was attempted, what was approved, and what was blocked. That becomes dangerous as soon as agents can send messages, modify repositories, or perform other high-impact actions.

Chorus solves that by placing a control plane between the user, the agent, and the provider integration.

## Primary Users

1. Individuals who want safe delegated help from assistant-style agents
2. Teams operating multiple specialized agents with different permission boundaries
3. Developers building secure agent workflows on top of provider APIs
4. Hackathon judges evaluating practical patterns for authorized AI actions

## Product Principles

- **Least privilege first**: agents receive narrowly scoped capabilities instead of broad ambient access
- **Human control stays visible**: approvals, blocks, and quarantine events are first-class UI states
- **Safe defaults win**: deterministic policy checks still work when model enrichment or providers fail
- **Auditability is mandatory**: every action request, decision, and execution outcome must be explainable

## Core MVP Features

- Auth0-compatible login seam with a mock-first local mode
- Token Vault adapter seam for delegated provider access
- Connected account registry for Gmail and GitHub
- Agent registry with per-agent capability grants
- Deterministic policy engine with provider-specific constraints
- Gemini-backed risk explanation layer
- Approval queue for medium-risk actions
- Quarantine escalation for repeated blocked behavior
- Audit timeline with realtime dashboard updates

## Active Demo Story

The current MVP demonstrates:

1. an automatically allowed Gmail draft
2. a GitHub issue that requires approval
3. a GitHub pull request merge that is blocked and then escalates to quarantine

This is the active product direction reflected in the [Auth Control Plane spec](specs/auth-control-plane/requirements.md), [design](specs/auth-control-plane/design.md), and [tasks](specs/auth-control-plane/tasks.md).

## Success Criteria

- Users can see which accounts are connected and what scopes they expose.
- Each agent’s permissions are visible and editable.
- Sensitive actions pause in an approval queue instead of executing immediately.
- Repeated violations escalate cleanly into quarantine.
- The demo can be launched locally with a single documented command.

## Legacy Context

The older conflict-prediction and immune-system concepts are still useful as historical context for the risk and intervention language, but they are no longer the main product story for Chorus.
