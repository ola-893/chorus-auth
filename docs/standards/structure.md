# Chorus Project Structure
This workspace follows clean architecture principles. When creating new files and folders, maintain consistency with established patterns.

## AI Assistant Guidelines
- Always check existing project structure before creating new files
- Use listDirectory tool to understand current organization
- Follow established naming conventions in the project
- Keep related functionality grouped together
- Create minimal, focused implementations

## Organization Principles
- **Separation of Concerns**: Keep different types of code in appropriate directories
- **Consistency**: Use the same naming patterns throughout the project
- **Clarity**: Use descriptive names that indicate purpose and functionality
- **Modularity**: Group related functionality into cohesive modules

## Repository Layout
```
chorus-multi-agent-immune/
├── backend/
│ ├── src/
│ │ ├── prediction_engine/
│ │ │ ├── gemini_client.py
│ │ │ ├── game_theory/
│ │ │ ├── models/
│ │ │ └── simulator.py
│ │ ├── firewall/
│ │ ├── mapper/
│ │ ├── integrations/
│ │ └── api/
│ ├── tests/
│ └── requirements.txt
├── frontend/
│ ├── src/
│ │ ├── components/
│ │ │ ├── dashboard/
│ │ │ ├── causal_graph/
│ │ │ └── alerts/
│ │ ├── hooks/
│ │ └── services/
│ └── package.json
├── infrastructure/
│ ├── terraform/
│ ├── docker/
│ └── scripts/
├── docs/
├── examples/
└── .github/workflows/
```


## Naming Conventions
- **snake_case** for Python files, directories, variables, and functions
- **PascalCase** for Python classes, React components, and TypeScript interfaces
- **camelCase** for JavaScript/TypeScript variables and functions
- **kebab-case** for configuration files and URLs

## Import Patterns
### Python
Standard library imports first, then third-party, then local imports. Group with blank lines.

### TypeScript/React
React imports first, then third-party libraries, then local components and hooks.

## Architectural Decisions
1.  **Modular Monolith**: Single codebase with clear internal boundaries for hackathon development speed.
2.  **Event-Driven Core**: Confluent Kafka is the central nervous system for all agent communications.
3.  **External State**: Redis for fast, ephemeral state (trust scores); Cloud Storage for durable quarantine logs.
4.  **Dependency Direction**: Lower-level modules (e.g., `gemini_client`) do not depend on higher-level modules (e.g., `api`).