# Repository work rules

- Active main repository: this directory. Do not develop in `D:/changan/changan-mesh-lab` or overwrite the preserved source `D:/esp/mesh_lite_node`.
- One ESP-IDF 6.1 project in `firmware/`; role applications in `firmware/apps/`; reusable code in `firmware/components/`.
- UGV runtime belongs to `host/src/changan_ugv/`. Keep `tools/` for administration and compatibility launchers.
- Independent car terminal lives in `../changan-car-terminal`; communicate through versioned protocol contracts, not cross-repo runtime imports.
- Current scope is generic M1 diagnostics task management. No scenario, flight, camera, UWB or media APIs without a new request.
- User runs firmware builds and flashing. Do not build/flash unless explicitly instructed later. Host regressions and `lab.py --dry-run` are allowed.
- Use `uv sync --locked`, `uv run --locked python tools/run_tests.py`. Isolated integration tests may start a temporary Broker; never restart production services or occupy COM ports for structural checks.
- Preserve all enrolled identities and private keys. `secrets/`, `runtime/`, `build/`, `.venv/` must remain untracked.
