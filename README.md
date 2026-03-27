# Chorus Multi-Agent Immune System

**A real-time safety layer for decentralized multi-agent systems that predicts and prevents emergent failures before they cascade.**

---

## 📚 Documentation Center

We have reorganized our documentation to make it easier to navigate.

### 🏗️ [Architecture](docs/architecture/system_overview.md)
*   [**System Overview**](docs/architecture/system_overview.md): High-level design, components, and data flow.
*   [**Integration Design**](docs/architecture/integration_design.md): Universal API and Dashboard expansion.
*   [**Pattern Alerts**](docs/architecture/pattern_alerts.md): Implementation of the pattern detection system.
*   [**Kafka Buffering**](docs/architecture/kafka_implementation.md): Resilience and message buffering strategies.

### 📐 [Standards](docs/standards/structure.md)
*   [**Project Structure**](docs/standards/structure.md): Repository layout and organization principles.
*   [**Coding Standards**](docs/standards/coding.md): Python and React style guides.
*   [**API Standards**](docs/standards/api.md): REST design and error handling.
*   [**Testing Standards**](docs/standards/testing.md): Testing pyramid and mocking strategies.
*   [**Technology Stack**](docs/standards/technology.md): Approved technologies and libraries.

### 🚀 [Deployment](docs/deployment/guide.md)
*   [**Deployment Guide**](docs/deployment/guide.md): Comprehensive guide for Docker, Kubernetes, and local setups.
*   [**Readiness Checklist**](docs/deployment/readiness.md): Verification steps for production.
*   [**Environment Variables**](docs/deployment/environment_variables.md): Full configuration reference.
*   [**Troubleshooting**](docs/deployment/troubleshooting.md): Common issues and fixes.

### 💻 [Development](docs/development/backend.md)
*   [**Backend Guide**](docs/development/backend.md): Python/FastAPI architecture and setup.
*   [**Frontend Guide**](docs/development/frontend.md): React dashboard development.
*   [**CLI Dashboard**](docs/development/cli_dashboard.md): Terminal-based monitoring tools.
*   [**Testing Guide**](docs/development/testing.md): Integration, unit, and property-based testing strategies.
*   [**Performance**](docs/development/performance.md): Optimization and benchmarking.

### 🎓 [Guides & Demos](docs/guides/demos.md)
*   [**Demo Guide**](docs/guides/demos.md): How to run the various demos (Executive, Technical, Hackathon).
*   [**Hackathon Submission**](docs/guides/hackathon.md): Summary of the submission package and innovation highlights.

### 📝 [Planning](docs/planning/product_overview.md)
*   [**Product Overview**](docs/planning/product_overview.md): Vision, problem statement, and key features.
*   [**Feature Specs**](docs/planning/specs/): Detailed specifications for various system components.
*   [**PRD: Universal Interface**](docs/planning/prd_universal_interface.md)
*   [**TDD: Universal Interface**](docs/planning/tdd_universal_interface.md)

---

## ⚡ Quick Start

### Run the Full Demo
```bash
./run_frontend_demo.sh
```

### Run the Interactive Menu
```bash
./demo_scenarios.sh
```

---

## 🏆 Project Highlights
*   **Predicts Conflicts**: Uses **Google Gemini 3 Pro** for game theory analysis.
*   **Prevents Failures**: Real-time quarantine via **Redis** trust scoring.
*   **Observability**: Integrated with **Datadog** and **Confluent Kafka**.
*   **Voice Alerts**: Critical incident narration via **ElevenLabs**.

---
*Chorus Team - December 2025*