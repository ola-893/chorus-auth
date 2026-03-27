# Chorus Coding Standards

## Python Standards
### Formatting & Style
- Follow PEP 8.
- Maximum line length is 88 characters (Black formatter default).
- Use type hints for all function and method signatures.
- Use descriptive variable names; avoid single-letter names except in trivial loops.

### Error Handling
- Use specific exception classes, never bare `except:` clauses.
- Log exceptions with appropriate context (`logger.exception` for unexpected errors in try/except blocks).
- For the Gemini API, wrap calls and handle `genai.errors.APIError` and `genai.errors.APIConnectionError` specifically.

### Documentation
- Use Google-style docstrings for all public modules, classes, and functions.
- Document the "why" for complex business logic, not just the "what".

## TypeScript/React Standards
### Component Structure
- Use functional components with TypeScript.
- Define props interfaces directly above the component.
- Destructure props in the function signature.
- Keep components focused; split into smaller components if exceeding ~150 lines.

### State Management
- Use `useState` for local component state.
- Use `useReducer` for complex state logic.
- For global state shared across the dashboard, prefer React Context or a simple state management library over heavy solutions.

## General
- **Commit Messages**: Use conventional commits format (`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`).
- **Comments**: Comment code that is not immediately obvious. Avoid comments that just repeat the code.