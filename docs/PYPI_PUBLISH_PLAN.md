# PyPI Publish Plan

Single living plan for getting `hatchup-payment-service-integration` onto PyPI and keeping subsequent releases automated. Append context here as steps land.

## Goal

Publish the Python SDK to PyPI under the name **`hatchup-payment-service-integration`** with tag-driven, OIDC-authenticated releases from GitHub Actions. No long-lived API tokens stored in CI.

## Status snapshot (2026-06-04)

- Package builds cleanly: `dist/hatchup_payment_service_integration-0.5.0-*` already produced via `just build`, but [pyproject.toml](../pyproject.toml) now declares `version = "1.1.5"`.
- [_version.py](../src/hatchup_psip/_version.py) hard-codes `"1.1.5"` and is re-exported as `hatchup_psip.__version__`.
- [CHANGELOG.md](../CHANGELOG.md) stops at `[1.1.4] — 2026-05-19`; `1.1.5` is unreleased.
- Dev status classifier still says `Development Status :: 3 - Alpha` despite v1.x line.
- No `.github/` directory — release workflow needs to be authored from scratch.

## Pre-flight

Reconcile drift before the first publish, otherwise the first PyPI artifact will ship with inconsistent metadata.

1. **Reserve the name on PyPI.** Confirm `hatchup-payment-service-integration` is unclaimed via `pip index versions hatchup-payment-service-integration` (404 expected). If squatted, fall back to `hatchup-psip` (matches the import name).
2. **Pick the first published version.** Two options:
   - Publish at `1.1.5` to keep parity with the in-repo version. Requires writing a `[1.1.5]` changelog entry that covers everything between `1.1.4` and the current `HEAD`.
   - Drop to `0.5.0` (the last version with a changelog entry) for the first PyPI release and re-cut `1.0.0` after a clean changelog catch-up. Cleaner public history but throws away the existing in-repo bumps.
   - **Recommendation:** publish `1.1.5` and write the catch-up entry — the version was already promised to internal consumers via the in-repo bump, dropping it would break anyone pinning to `>=1.0`.
3. **Bump dev status classifier** in [pyproject.toml](../pyproject.toml) from `3 - Alpha` to `4 - Beta`. SDK has shipped 1.x; alpha is misleading.
4. **Switch `_version.py` to derive from package metadata** so future bumps only touch `pyproject.toml`:
   ```python
   from importlib.metadata import version as _pkg_version
   __version__ = _pkg_version("hatchup-payment-service-integration")
   ```
5. **Verify sdist contents.** `uv build` then `tar -tzf dist/*.tar.gz` — confirm `README.md`, `LICENSE`, `CHANGELOG.md`, `src/hatchup_psip/py.typed` all included.
6. **Verify wheel contents.** `unzip -l dist/*.whl` — confirm `hatchup_psip/py.typed` is there so consumers get type info.
7. **Confirm `[project.urls]` GitHub org slug.** Currently `hatchup-io/payment-service-integration`. Repo location needs to actually match; trusted-publisher config keys off the org/repo pair.

## TestPyPI dry-run

Run this before the real publish so the first PyPI artifact is known-good.

1. Create a TestPyPI account + project; reserve the same name on TestPyPI.
2. Generate a TestPyPI API token (scoped to the project) for the dry-run only.
3. `just build`
4. `uv publish --publish-url https://test.pypi.org/legacy/ --token $TEST_PYPI_TOKEN`
5. In a fresh venv:
   ```bash
   python -m venv /tmp/psip-test && source /tmp/psip-test/bin/activate
   pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ \
               hatchup-payment-service-integration
   python -c "from hatchup_psip import PaymentServiceClient, __version__; print(__version__)"
   ```
6. Smoke-test the `[django]` extra in a second venv:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ \
               "hatchup-payment-service-integration[django]"
   python -c "from hatchup_psip.django import PSIPWebhookView; print(PSIPWebhookView)"
   ```

## Trusted Publisher (OIDC) setup

No long-lived tokens. PyPI accepts an OIDC trust relationship with a specific GitHub repo + workflow.

1. On PyPI, **register a Pending Publisher** for `hatchup-payment-service-integration` with:
   - Owner: `hatchup-io`
   - Repository: `payment-service-integration`
   - Workflow: `release.yml`
   - Environment: `pypi` (optional but recommended — gates publish behind a protected GH environment)
2. Create the matching GitHub environment (`pypi`) with required reviewers set to the release owners.
3. First successful publish from CI converts the Pending Publisher into a Trusted Publisher. After that, manual token publishes can be disabled entirely.

## Release workflow

`.github/workflows/release.yml`, triggered by pushing a `v*` git tag.

```yaml
name: Release
on:
  push:
    tags: ["v*"]
permissions: {}
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: just all
      - run: just test
      - run: just build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write   # required for OIDC
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        # No `password:` — uses OIDC trusted-publisher config
```

Tag → release flow:

```bash
# bump version + changelog entry locally
git commit -am "release: v1.1.6"
git tag v1.1.6
git push origin main --tags
# CI runs build + tests, then publish job waits for environment approval, then uploads
```

## Versioning policy

- `pyproject.toml` `version` is the single source of truth.
- Tag name matches the version with a leading `v` (e.g. `v1.1.5` → `version = "1.1.5"`).
- `_version.py` reads from `importlib.metadata.version(...)` after the pre-flight refactor; no second place to update.
- Every release must have a matching `## [X.Y.Z] — YYYY-MM-DD` block in [CHANGELOG.md](../CHANGELOG.md). Workflow can add a `check-changelog` step that greps for the tag's version to fail the build if missing.
- Pre-release suffixes (`1.2.0rc1`) acceptable for breaking-change rollouts; PyPI handles them as installable-only with `--pre`.

## Post-publish

1. Add **install badge + PyPI link** to [README.md](../README.md):
   ```markdown
   [![PyPI](https://img.shields.io/pypi/v/hatchup-payment-service-integration.svg)](https://pypi.org/project/hatchup-payment-service-integration/)
   ```
2. Verify install from real PyPI in a clean venv (same smoke as the TestPyPI step).
3. Update [launchpad-backend](../../../Launchpad/launchpad-backend/) to pin against the PyPI version instead of the editable install once the integration cycle completes. Right now `.venv/lib/.../_editable_impl_hatchup_payment_service_integration.pth` points at this checkout — fine for dev, but launchpad's production deploy should consume the published wheel.
4. Drop the TestPyPI token from local env (only the OIDC flow remains).

## Open questions

- Does the `hatchup-io` GitHub org already exist? Confirm and confirm CI / GitHub environment permissions are set so the publish job can request OIDC tokens.
- Should the release workflow also build + attach the sdist/wheel to a GitHub Release? Low-cost addition (`softprops/action-gh-release`); makes the GitHub UI a useful release index.
- Do we want a separate `[dev]` extra in `pyproject.toml`? Currently dev deps live under `[dependency-groups].dev` (uv-only). PyPI consumers can't install `pip install "...[dev]"`; for now only `[django]` is published. Leave as-is unless we want to support pip-based contributors.
