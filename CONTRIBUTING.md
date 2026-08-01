# Contributing to SafeRouteAI

We welcome contributions! This project spans embedded firmware (C++), backend services (Python), frontend visualization (TypeScript/React), and simulation tooling (Python).

## Getting Started

1. Read the [README](README.md) to understand the architecture.
2. Check [ROADMAP.md](ROADMAP.md) for planned work.
3. Look for issues labeled `good-first-issue` or `help-wanted`.
4. Set up the development environment per [docs/setup.md](docs/setup.md).

## Development Workflow

### 1. Fork & Branch

```bash
git checkout -b feat/my-feature
```

Use branch prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`.

### 2. Code Style

| Language | Conventions |
|----------|-------------|
| C++ (firmware) | `snake_case` functions, `PascalCase` types, `UPPER_CASE` defines |
| Python (backend/simulator) | PEP 8, `snake_case`, type hints required |
| TypeScript (frontend) | ESLint + Prettier config provided |

### 3. Testing

Run all tests before submitting:

```bash
./scripts/run-all-tests.sh
```

| Test Suite | Location | Command |
|------------|----------|---------|
| Backend Python | `tests/backend/` | `python -m pytest tests/backend/` |
| Firmware C++ (on-device) | `test/firmware/` | `pio test --environment esp32dev` |
| Simulator | `tests/simulator/` | `python -m pytest tests/simulator/` |
| Integration | `tests/integration/` | `python -m pytest tests/integration/` |

### 4. Commit Messages

```
<type>(<scope>): <short description>

<body (optional)>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`
Scopes: `firmware`, `backend`, `frontend`, `simulator`, `dashboard`, `docs`, `infra`

### 5. Pull Request Process

1. Update documentation if you change behavior.
2. Add or update tests for new functionality.
3. Ensure all tests pass.
4. Update CHANGELOG.md under `[Unreleased]`.
5. Request review from a maintainer.

## Architecture Decisions

Significant design decisions should be documented. See [docs/architecture.md](docs/architecture.md)
for the current architecture documentation.

## Safety-Critical Changes

Changes affecting evacuation routing, sensor fusion, or fail-safe logic require:
- Formal review by two contributors
- Additional integration tests
- Hardware-in-the-loop validation if available

## Questions?

Open a [Discussion](https://github.com/your-org/SafeRouteAI/discussions) or
file an issue for bugs and feature requests.