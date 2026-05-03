default:
    @just --list

# --- Code quality ---
# Format all files
fmt:
    uv run ruff format .

# Fix linting issues
lint-fix:
    uv run ruff check . --fix

# Format and lint-fix
fix: fmt lint-fix

# Verify formatting and lint (no changes)
check:
    uv run ruff format --check .
    uv run ruff check .

# Run mypy
typecheck:
    uv run mypy src

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files

# Format, lint-fix, and verify
all: fmt lint-fix check typecheck

# --- Tests ---
# Run pytest (skips `live` integration tests by default)
test *ARGS:
    uv run pytest -m "not live" {{ARGS}}

# Run live integration tests against a local payment-system
test-live *ARGS:
    uv run pytest -m live {{ARGS}}

# Run tests with coverage report
cov *ARGS:
    uv run pytest --cov --cov-report=term-missing {{ARGS}}

# --- Build / publish ---
# Build sdist + wheel into dist/
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
