# M1 wire contract v1

The car and UGV repositories own separate implementations. This directory defines the contract; neither production program imports source from the other repository.

## Serial framing

Eight-byte network-order header `!4sHH`: magic `MLT1`, UTF-8 JSON byte length, CRC16-CCITT (`binascii.crc_hqx(payload, 0xffff)`). JSON is compact UTF-8; duplicate object keys and non-finite numbers are rejected. Payload maximum: 1024 bytes; car/node commands: 512 bytes. Firmware root binds the source node ID; the car cannot self-authorize a different source.

Envelope: integer `v:1`, `type`, request `msg_id`. Request and ACK IDs must match. MQTT uses the JSON payload without the serial header. Current operations: list/ping/status/echo and task.create/get/list/control/update/events. Required business fields vary per operation; do not treat timestamps or task_id as universally mandatory on legacy messages.

## MQTT over mutual TLS

- `mesh/v1/terminals/<root>/requests`, `responses`, `events`
- `mesh/v1/nodes/<node>/commands`, `acks`, `presence`, `capabilities`, `telemetry`
- `mesh/v1/nodes/<node>/task_commands`, `task_events`
- `mesh/v1/clock`

Per-certificate ACLs come from administrator inventory. Presence/capabilities may be retained; command/task traffic is not retained. A fresh boot-matched presence, capability and telemetry makes a node ready. `uptime_ms` is device-local monotonic uptime, not UTC.

## Generic tasks

Only `kind:diagnostics` is currently supported. Create does not start. Config: duration_s 1..3600; period_ms 200..10000. Update is allowed only in CREATED and increments revision. Control supports start/pause/resume/cancel. One active task per target; separate nodes run independently. Request deduplication, durable command_id, per-task op_seq, boot binding and expiry reject stale command replays. Submission/received ACK does not establish successful execution.

States include CREATED, QUEUED, DISPATCHING, ACCEPTED, RUNNING, pause/resume/cancel pending, PAUSED, RECONCILING, UNKNOWN and terminal SUCCEEDED/FAILED/CANCELLED. Restart/offline recovery reconciles state rather than replaying start. Events are cursor-paginated; one payload per page fits the C6 frame budget.

`frames.json` contains fixed frame vectors, including fragmented-stream decoding targets and a task request. Tests verify identical encoded bytes and decoded JSON against the independent car implementation when present. These examples are fixtures, not live commands.
