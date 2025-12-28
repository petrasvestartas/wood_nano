# PyPI Publishing

## One-Time Setup

Configure Trusted Publisher at https://pypi.org/manage/project/wood_nano/settings/publishing/:

| Field | Value |
|-------|-------|
| Owner | `petrasvestartas` |
| Repository name | `wood_nano` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

## Release

1. Update version in `src/wood_nano/__init__.py`
2. Run:
```bash
git add -A && git commit -m "Release v0.3.5" && git tag v0.3.5 && git push origin main --tags
```
