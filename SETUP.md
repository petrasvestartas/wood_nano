# Development environment — wood_nano

Python bindings for the `wood` C++ library, built with nanobind + scikit-build-core.
Installing this repo from source **compiles C++**, so it is by far the slowest of
the three to set up (the first build fetches protobuf/abseil and takes several
minutes; `build/` reached 1.4 GB here).

Requires Python **3.13** (pinned in `.python-version`; the package floor is 3.12).
The system Python here is 3.14, so let `uv` supply the right one rather than using
`python3 -m venv`.

## Setup (run once)

```bash
cd wood_nano
uv venv                                   # reads .python-version -> CPython 3.13
uv pip install nanobind scikit-build-core numpy pytest ninja cmake
uv pip install --no-build-isolation -e .  # compiles the extension (slow the first time)
```

`--no-build-isolation` is required: it makes scikit-build-core reuse the
nanobind/cmake you just installed instead of fetching its own copies into an
isolated build environment.

## Activate

```bash
source .venv/bin/activate
```

Or skip activation entirely and prefix commands with `uv run`.

## Rebuild after C++ changes

```bash
uv pip install --no-build-isolation -e .
```

An editable install does **not** recompile on import — rerun the command above
after touching any `.cpp`/`.h`. For a clean rebuild, `rm -rf build/` first (this
also discards the fetched protobuf/abseil, so the next build is slow again).

## Verify

```bash
uv run python -c "import wood_nano; print(wood_nano.__version__)"
uv run pytest
uv run python examples_session_py/<script>.py
```

## Where the C++ comes from

`CMakeLists.txt` resolves two external sources, first hit wins:

| Dependency | Resolution |
|---|---|
| `wood` | the sibling checkout `../wood` when `../wood/src/joinery_solver/wood_main.cpp` exists; otherwise a clone of `petrasvestartas/wood@main`. |
| `session_cpp` | `-DSESSION_CPP_LOCAL=<dir>` / the `SESSION_CPP_LOCAL` environment variable; then the sibling `../session_cpp` (a checkout or a symlink to one); otherwise a clone of `petrasvestartas/session_cpp@main`. Same order as `wood/CMakeLists.txt`. |

Because this repo sits in `wood_project/` next to `wood/` and `session_cpp/`, **your local
checkouts are what get compiled** - edits there appear here after a rebuild, and `wood` and
`wood_nano` always compile the same kernel. Move the folders apart and you silently switch
to the GitHub `main` clones instead. `../README.md` has the one-command update
(`update_session.sh`) and the per-repo commands.

The build stamps what it compiled into the package:

```bash
uv run python -c "import wood_nano; print(wood_nano.__wood_sha__, wood_nano.__session_sha__)"
```

## Notes

- `build/` is gitignored — delete it freely.
- `.venv/` self-ignores: uv writes a `.gitignore` containing `*` inside it, so it
  never shows up in `git status` even though `.gitignore` does not mention it.
- Wheels are abi3 tagged `cp312`: one wheel covers 3.12, 3.13, 3.14+. Rhino 8
  (Python 3.9) is deliberately unsupported.
