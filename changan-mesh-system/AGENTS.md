# Repository work rules

- Active main repository: this directory. Do not develop in `D:/changan/changan-mesh-lab` or overwrite the preserved source `D:/esp/mesh_lite_node`.
- One ESP-IDF 6.1 project in `firmware/`; role applications in `firmware/apps/`; reusable code in `firmware/components/`.
- Current architecture only: `ugv_root` level 1, `ugv` level 2, `uav` level 3, `micro_uav` level 4. Root ID is `ugv-root`; inventory is schema 2 in `config/nodes.json`.
- The independent terminal uses local HTTP/WebSocket to UGV Service. Node control/status uses MQTT/TLS via the root USB tunnel. Do not reintroduce terminal serial/MQTT ingress, a PC Mesh root, or alternate TCP application transports. Cloud/5G and the separate data channel remain future work.
- UGV runtime belongs to `host/src/changan_ugv/`. Keep `tools/` for administration and compatibility launchers.
- Independent car terminal lives in `../changan-car-terminal`; communicate through versioned protocol contracts, not cross-repo runtime imports.
- Current scope is generic M1 diagnostics task management. No scenario, flight, camera, UWB or media APIs without a new request.
- User runs firmware builds and flashing. Do not build/flash unless explicitly instructed later. Host regressions and `lab.py --dry-run` are allowed.
- Use `uv sync --locked`, `uv run --locked python tools/run_tests.py`. Isolated integration tests may start a temporary Broker; never restart production services or occupy COM ports for structural checks.
- Preserve enrolled identities and private keys; never regenerate or overwrite them during deployment. The project owner explicitly approved committing existing `secrets/` credentials and `changan-runtime/` deployment files on 2026-11-16. Keep credential build caches, controller locks, live `runtime/`, `build/`, and `.venv/` untracked.
