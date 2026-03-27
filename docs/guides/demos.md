# Chorus Demo Guide

This guide covers all demonstration scenarios for the Chorus Multi-Agent Immune System.

## 🚀 Quick Start

### 1. Full Frontend Demo (Recommended)
**Experience the complete system visualization.**

```bash
./run_frontend_demo.sh
```
*   **What you see:** A Cyberpunk-themed React dashboard with live agent trust scores, real-time conflict prediction, and system health metrics.
*   **Technology:** React, WebSocket, FastAPI.

### 2. Interactive Menu
**Choose from a list of available demos.**

```bash
./demo_scenarios.sh
```

### 3. Backend-Only Simulation
**Focus on core logic without the GUI.**

```bash
python backend/comprehensive_demo.py --mode full
```

---

## 🎬 Demo Scenarios

### Executive Demo (3 Minutes)
**Focus:** Business value, ROI, and high-level prevention.
**Run:** `python demo_presentations/scenarios/executive_demo.py`
**Narrative:** "Prevent million-dollar outages with AI-powered prediction."

### Technical Demo (10 Minutes)
**Focus:** Architecture, Gemini integration, Kafka streaming.
**Run:** `python demo_presentations/scenarios/technical_demo.py`
**Narrative:** "Production-ready multi-agent safety with cutting-edge AI."

### Hackathon Pitch (5 Minutes)
**Focus:** Innovation and Partner Integrations (Google, Datadog, Confluent, ElevenLabs).
**Run:** `python demo_presentations/scenarios/hackathon_demo.py`

---

## 🖥️ Frontend Dashboard Details

The frontend provides a real-time window into the conflict prediction engine.

### Key Features
*   **Trust Score**: Updated instantly via WebSocket.
*   **Visual Status**: Agents flash red when quarantined.
*   **System Health**: Live check of Redis and Gemini API status.

### Troubleshooting
*   **"WebSocket Disconnected"**: Ensure backend port 8000 is open.
*   **No Agents**: Wait 1-2 seconds for the simulation to initialize.

---

## 🛠️ CLI Dashboard

For a lightweight, terminal-based view of the system.

```bash
cd backend
python demo_cli_dashboard.py
```

**Features:**
*   Live ASCII progress bars for resource usage.
*   Color-coded trust scores.
*   Real-time conflict alerts.
