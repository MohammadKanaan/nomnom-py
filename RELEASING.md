# Releasing nomnom

This project is set up to publish to PyPI from GitHub Actions using PyPI Trusted
Publishing.

## One-Time Setup

1. Create a PyPI account for the maintainer if you do not already have one.
2. In PyPI, go to `Account settings` -> `Publishing`.
3. Add a pending trusted publisher with:
   - PyPI project name: `nomnom`
   - Owner: `MohammadKanaan`
   - Repository: `nomnom-py`
   - Workflow file: `publish.yml`
   - Environment: `pypi`
4. In GitHub, create an environment named `pypi`.
5. Require manual approval for that environment before the publish job runs.

## Release Checklist

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run mypy nomnom
uv build
uvx twine check dist/*
```

## Publish a Release

1. Update `[project].version` in `pyproject.toml`.
2. Commit the release changes.
3. Create and push a tag that matches the version:

```bash
git tag v1.0.0
git push origin v1.0.0
```

4. Approve the `pypi` environment in GitHub when the `Publish` workflow starts.
5. Confirm the release at `https://pypi.org/project/nomnom/`.

## Notes

- `dist/` should be treated as build output; rebuild it for every release.
- If you want to dry-run the pipeline before the first public release, publish to
  TestPyPI manually instead of tagging production.
