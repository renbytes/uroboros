# Uroboros: Adversarial Co-Evolutionary Software Agent

![logo](docs/logo.jpg)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blueviolet)](https://python-poetry.org/)
[![E2B](https://img.shields.io/badge/sandbox-E2B-orange)](https://e2b.dev/)
[![Docker](https://img.shields.io/badge/container-docker-blue)](https://www.docker.com/)

**Uroboros** is an autonomous software engineering system capable of recursive self-improvement. It implements the "Adversarial Co-Evolution" paradigm, where a **Builder Agent** (Actor) and a **Tester Agent** (Adversary) compete in an infinite loop to generate robust, verified code.

> [Uroboros](https://en.wikipedia.org/wiki/Ouroboros) is an ancient image of a snake eating itself, representing the core behavior of this system: code that writes itself, and critiques itself in a recursive loop.

## Core Architecture

The system operates on the **Uroboros Loop**:

1. **Actor (The Builder):** Generates code solutions and tools. It uses **Voyager-style Memory** (Vector DB) to retrieve past skills and avoid repeating mistakes.
2. **Adversary (The Critic):** Generates "Killer Tests" designed to break the Actor's code. It targets edge cases, boundary conditions, and logic flaws.
3. **Arbiter (The Judge):** Runs the code and tests in a secure, isolated **Firecracker MicroVM** (via [E2B](https://github.com/e2b-dev/E2B)). It provides the ground truth signal (Pass/Fail/Crash).
4. **Evolver (The Optimizer):** Analyzes failure patterns and rewrites the system prompts to improve future performance.

## Quick Start

### Prerequisites

* **Python 3.11+**
* **[Poetry](https://github.com/python-poetry/poetry)** (Dependency Manager)
* **[Docker](https://www.docker.com/)** (Optional, for containerized runs)
* **API Keys:** [OpenAI](https://openai.com/api/) (`gpt-5-mini` recommended) and [E2B](https://github.com/e2b-dev/E2B).

### 1. Installation

```bash
# Clone the repository
git clone git@github.com:renbytes/uroboros.git
cd uroboros

# Install dependencies via Poetry
# Note: This installs numpy<2.0.0 to ensure ChromaDB compatibility
poetry install
```

### 2. Configuration

Copy the template and add your secrets.

```bash
cp .env.example .env
```

Required `.env` variables:

```ini
OPENAI_API_KEY=sk-...
E2B_API_KEY=e2b_...
ACTOR_MODEL=gpt-5-mini
ADVERSARY_MODEL=gpt-5-mini
DEBUG=true  # Set to 'true' to save full debugging artifacts
```

### 3. Verify Infrastructure (Smoke Test)

Run this script to ensure your E2B sandbox connection is working:

```bash
poetry run python scripts/smoke_test.py
```

**Expected Output:** 🎉 Infrastructure is HEALTHY.

## Usage

### Run a Single Task

To assign a specific coding challenge to the agent:

```bash
poetry run python -m uroboros.main --task "Write a Flask API with a /users endpoint backed by SQLite."
```

### Run the Autonomous Loop

To let the agent generate its own curriculum and evolve indefinitely:

```bash
poetry run python -m uroboros.main --loop
```

## Debugging & Artifacts

If `DEBUG=true` is set in your `.env`, the system saves detailed artifacts for every step of the loop in:

```
data/intermediate_debugging/<task_id>/
```

Files generated:

* `_task_definition.txt`: What the agent was asked to do.
* `_actor_reasoning.md`: The Builder's internal monologue.
* `_actor_generated_code_X.py`: The raw code patches.
* `_adversary_attack_plan.md`: The logic behind the attack.
* `_adversary_test_code_X.py`: The generated "Killer Tests".
* `_attempt_X_failure_log.log`: Combined stdout/stderr from the sandbox failure.

## Troubleshooting

### Common Issues

#### 1. ImportError or ModuleNotFoundError in Sandbox

**Cause:** The test file tries to import the solution file, but Python's path isn't set correctly in the VM.

**Fix:** The Arbiter now runs tests using `python -m pytest .`, which adds the current directory to `sys.path`.

#### 2. Command exited with code 2 (Syntax Error)

**Cause:** The LLM included Markdown fences (` ```python `) or conversational text inside the code file.

**Fix:** The `clean_code_block` utility now strips markdown, and prompts explicitly forbid conversational filler in the `content` field.

#### 3. AttributeError: np.float_ was removed

**Cause:** Incompatibility between ChromaDB (v0.4.x) and NumPy 2.0.

**Fix:** `pyproject.toml` pins `numpy = "<2.0.0"`. Run `poetry lock && poetry install` if you see this.

#### 4. BadRequestError: Invalid parameter: 'response_format' ...

**Cause:** Using an older model (like `gpt-4-turbo` or `gpt-3.5`) that doesn't support "Structured Outputs" (`json_schema`).

**Fix:** Ensure `ACTOR_MODEL=gpt-4o` in your `.env`.

#### 5. TypeError: 'Sandbox' object does not support asynchronous context manager

**Cause:** Using the synchronous `Sandbox` class instead of `AsyncSandbox` or using incorrect SDK v1 syntax.

**Fix:** The codebase now strictly uses `AsyncSandbox.create()` and `sandbox.commands.run()`.

## Testing

To run the internal unit and integration tests for the agent framework itself:

```bash
# Run all tests
poetry run pytest

# Run model connectivity check
poetry run pytest tests/integration/test_llm_connectivity.py
```

## License

MIT License.