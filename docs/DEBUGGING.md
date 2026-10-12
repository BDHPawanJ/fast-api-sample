# Debugging

The API runs in a container, and you debug it from your editor by
**attaching** to [debugpy](https://github.com/microsoft/debugpy), which runs
alongside the server. There is nothing to start in "debug mode": the dev
server always has the debugger available, and you attach and detach whenever
you like.

- [Quick start (VS Code)](#quick-start-vs-code)
- [How it works](#how-it-works)
- [Debugging the API](#debugging-the-api)
- [Debugging startup code](#debugging-startup-code)
- [Debugging tests](#debugging-tests)
- [Host window or dev container?](#host-window-or-dev-container)
- [Other editors](#other-editors)
- [Tips and known behaviour](#tips-and-known-behaviour)
- [Troubleshooting](#troubleshooting)

---

## Quick start (VS Code)

1. Start the stack: `make up`.
2. Open the **Run and Debug** view and choose **Attach: app container**
   (from `.vscode/launch.json`), then press F5.
3. Set a breakpoint, for example in `app/api/routes/health.py`.
4. Send a request: `curl http://localhost:8000/v1/health`. Execution stops at
   your breakpoint, with variables, the call stack and the debug console
   available.

Detach with the disconnect button; the server keeps running.

---

## How it works

```text
VS Code ──DAP──► localhost:5678 ──► debugpy (container)
                                      └─ uvicorn reloader (process 1)
                                           ├─ multiprocessing resource tracker
                                           └─ uvicorn worker  ← your code runs here
```

- `docker/dev/start.sh` starts uvicorn **under debugpy**:
  `python -m debugpy --listen 0.0.0.0:5678 -m uvicorn ... --reload`.
- With `--reload`, uvicorn runs your code in a **worker subprocess** and
  replaces it each time you save. debugpy follows subprocesses, and the
  launch configuration sets `"subProcess": true`, so VS Code attaches to each
  worker automatically, including the new one after every reload. You don't
  need to reattach after saving a file.
- Breakpoints you set in the editor use your local paths; `pathMappings` in
  `launch.json` translates them to the container's `/app`.
- Port 5678 is published to **127.0.0.1 only**. A debugger can run arbitrary
  code in the process, so it must not be reachable from other machines.

---

## Debugging the API

Use **Attach: app container**:

```jsonc
{
  "name": "Attach: app container",
  "type": "debugpy",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 },
  "pathMappings": [{ "localRoot": "${workspaceFolder}", "remoteRoot": "/app" }],
  "subProcess": true,
  "justMyCode": true
}
```

- Attach before or after sending requests; breakpoints apply from the moment
  you attach.
- `justMyCode: true` keeps the debugger out of FastAPI, Starlette and
  SQLAlchemy internals. To step into library code, set it to `false` (or use a
  copy of the configuration).
- Uncaught exceptions are mostly turned into HTTP responses by the
  application's error handlers, so they may not pause the debugger. To stop
  where an error is raised, enable **Raised Exceptions** in the Breakpoints
  panel, or put a breakpoint in the handler in `app/api/errors.py`.
- While stopped, the **Debug Console** evaluates expressions in the current
  frame (for example `cart.total_quantity` or `product.is_low_stock()`).

---

## Debugging startup code

Code that runs while the app starts (settings in
`app/infrastructure/config.py`, the lifespan hook in `app/api/lifespan.py`,
module-level code) runs before you can normally attach. Make the server wait
for the debugger instead:

```bash
docker compose stop app
DEBUGPY_WAIT=1 docker compose up app      # blocks until a debugger attaches
```

Attach with **Attach: app container**; startup continues and stops at your
breakpoints. When you're done, press Ctrl+C and run `make up` to return to
normal behaviour.

Run these commands from a terminal on your machine. In the dev container,
VS Code is attached to the `app` container itself, so stopping it disconnects
the window; it reconnects once the container is back.

---

## Debugging tests

**With a host `.venv`** (see
[DEVELOPMENT.md → First-time setup](DEVELOPMENT.md#4-create-the-host-environment-recommended)),
the simplest way is the VS Code test explorer: set a breakpoint and choose
**Debug Test** on a test or file. pytest runs on your machine against the
database container (start it with `make up`), and no port or attach step is
involved.

**In a container**, tests run in their own container, waiting for a debugger
on port **5679**:

```bash
make test-debug ARGS="tests/test_domain.py"
make test-debug ARGS="tests/test_products.py::TestProductEndpoints::test_update_product_success"
```

Then run **Attach: tests in container**. pytest starts as soon as you
attach; set breakpoints first. When the tests finish, the container exits and
the debug session ends.

- `justMyCode` is `false` for tests, so you can step into application code,
  fixtures and libraries.
- `ARGS` takes any pytest arguments.
- **Coverage is turned off for debug runs.** pytest-cov installs its own
  tracer, which stops debugger breakpoints from firing, so `make test-debug`
  passes `--no-cov`, and the test explorer does the same (`.vscode/settings.json`).
  If you run `uv run pytest` under a debugger yourself, add `--no-cov`.

In the dev container, `make` and `docker` aren't available in the integrated
terminal (it is a shell inside the container). There, either use the test
explorer's **Debug Test** action, which needs no port, or run the equivalent
of `make test-debug` directly and then attach:

```bash
python -m debugpy --listen 0.0.0.0:5679 --wait-for-client -m pytest --no-cov tests/test_domain.py
```

---

## Host window or dev container?

You don't need the dev container to debug. The API always runs in a
container, and the debugger attaches to it over a port, so a normal VS Code
window works the same way. Both setups use the same `launch.json`:

| | Host window | Dev container |
|---|---|---|
| Debugger connects to | `localhost:5678` on your machine (published port) | `localhost:5678` inside the container |
| Path mapping | your repo path → `/app` | `/app` → `/app` (`${workspaceFolder}` is `/app`) |
| Code completion, type checking | Full with a host `.venv` (`uv sync`) | Full: uses `/opt/venv` |
| Debug a test from the test explorer | Yes, with a host `.venv` | Yes |
| `make test-debug` / `DEBUGPY_WAIT=1` | From the integrated terminal | From a terminal on your machine |

Choose whichever you prefer; see
[DEVELOPMENT.md → Editing in VS Code](DEVELOPMENT.md#editing-in-vs-code).

---

## Other editors

Any editor that speaks the Debug Adapter Protocol can attach. Configure it to:

- connect to `localhost:5678` (API) or `localhost:5679` (tests),
- use the host `.venv` as the project interpreter, for completion and to run
  tests under its own debugger,
- map your repository directory to `/app`,
- follow subprocesses, if the client supports it. Otherwise breakpoints only
  work in the first worker; restart the app container after code changes, or
  run the server without `--reload` while debugging.

**PyCharm (Professional)** can instead use the container as its interpreter
(add a *Docker Compose* interpreter for the `app` service) and run and debug
with its own debugger, without the attach step.

**Neovim** (`nvim-dap` with `nvim-dap-python`) and similar clients use an
`attach` configuration with the same host, port and path mapping.

---

## Tips and known behaviour

- **A breakpoint on the first line of a multi-line statement can stop twice**,
  for example on `return HealthStatus(` followed by arguments on later lines.
  Python 3.12+ reports that line again when it returns from evaluating the
  arguments to make the call. Press continue, or put the breakpoint on a
  single-line statement.
- **Async code** steps normally; `await` points may jump to other tasks if
  several requests are in flight. Send one request at a time while stepping.
- **Bytecode is kept out of the repo in the container**
  (`PYTHONPYCACHEPREFIX=/tmp/pycache`). Compiled files created on the host
  record host paths; if the container loaded them (pytest does this for test
  modules), breakpoints would never match. Don't remove this setting.
- **The reload watcher only watches `app/`.** Changes in `tests/`,
  `alembic/` or configuration don't restart the server.
- **Performance:** expect requests to run slower while a debugger is
  attached, especially with `justMyCode: false`. Detach when you're done.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Connection refused" on attach | The API container isn't running or is still starting: `make up`, then `make logs` |
| Breakpoint is hollow / "unverified" | The file isn't under the mapped root, or `localRoot` is wrong. Check `pathMappings`; in the host window `${workspaceFolder}` must be the repo root |
| Attached, breakpoint verified, never hit | The line doesn't run for that request, or the client didn't follow the worker subprocess: check `"subProcess": true`. In VS Code's **Call Stack** panel you should see the reloader and two subprocesses |
| Breakpoints in tests never hit | You attached to 5678 (the API) instead of 5679, or the test container image is older than the Dockerfile: `make build` |
| Startup breakpoints are skipped | Use `DEBUGPY_WAIT=1` as described in [Debugging startup code](#debugging-startup-code) |
| Port 5678 already in use | Another app container or debug session holds it: `docker ps`, and stop the extra container |
| Debugger stops inside library code unexpectedly | A **Raised Exceptions** or **Uncaught Exceptions** breakpoint is enabled; disable it in the Breakpoints panel |
