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

## Network status (optional v1 fields)

`telemetry.payload`, successful ping/status ACK `payload`, and each list row's
`status` share the same status object. Existing `role`, `topology`, `level`, heap
and uptime fields remain unchanged. Mesh `level` is the device-reported level;
zero means no established Mesh level. The following additive fields are optional:

| Field | Meaning |
| --- | --- |
| `sta_ip`, `ap_ip`, `gateway`, `netmask` | IPv4 dotted-decimal addresses from the corresponding netif; absent when not assigned |
| `sta_mac`, `ap_mac` | Device interface MAC addresses, colon-separated hex |
| `parent_connected` | Whether the STA interface is associated with an upstream AP |
| `parent_bssid` | Associated upstream AP MAC, present only when connected |
| `rssi`, `channel` | Upstream signal in dBm and current Wi-Fi primary channel |
| `associated_children` | Wi-Fi AP associated client count, including non-Mesh clients; not a count of live MQTT peers |

List rows additionally expose `online` (last presence declaration, or null),
`status_age_s` (UGV monotonic seconds since the last non-retained telemetry, or
null), and `status_current_boot` (telemetry matches the presence boot). Only
`ready` combines presence, capabilities, boot matching and freshness. A false
`ready` does not by itself prove physical disconnection. Old status can remain
visible as a historical snapshot; it must not be presented as live telemetry.

Mesh tree edges match a child's `parent_bssid` to a unique parent's `ap_mac`.
Do not infer edges from role names, IP subnets, configured chain topology or
consecutive levels. Unreported, external, duplicate and cyclic relationships
are shown separately. Host-local `status.execution_host:local` is not a Mesh
wireless node. Missing fields from old firmware remain unknown. No new request
types, identities or ACL privileges are introduced. List replies still page one
node at a time under the 1024-byte frame budget.

UGV C6 radio diagnostics use the existing CRC-protected `MUX1` USB control
channel. The host advertises support with `READY` channel 255, token 0, empty
payload, `seq=1`. Only after this negotiation does the firmware send optional
type 10 `NETWORK` reports (channel 255, token/seq 0, current session epoch).
Payload is compact JSON `{v:1,type:"network",node_id,payload:<network status>}`,
at most 512 bytes. Heap, uptime and topology-name fields are omitted to fit.
No ACK or automatic retry is added; a report is sent every five seconds.
Old hosts send READY seq=0 and receive no new frame type; old firmware ignores
the added READY sequence and continues byte forwarding as before.

The bridge accepts reports only for its current USB epoch and configured
`--ugv-id` (default `ugv-001`) and atomically writes the ignored local snapshot
`runtime/ugv-network.json`. Reset/disconnect invalidates it. This diagnostic
file confers no MQTT or device permissions. A local UGV list row includes it as
`status.network_status:{status,age_s,fresh}`, fresh for less than 12 seconds.
`status.execution_host:local` and the list row's task-service `ready` retain
their meaning; the radio has independent freshness. The car shows a radio node
only when this optional report exists. A missing UGV radio report must not be
replaced with host IPs or guessed wireless links.

## Generic tasks

Only `kind:diagnostics` is currently supported. Create does not start. Config: duration_s 1..3600; period_ms 200..10000. Update is allowed only in CREATED and increments revision. Control supports start/pause/resume/cancel. One active task per target; separate nodes run independently. Request deduplication, durable command_id, per-task op_seq, boot binding and expiry reject stale command replays. Submission/received ACK does not establish successful execution.

States include CREATED, QUEUED, DISPATCHING, ACCEPTED, RUNNING, pause/resume/cancel pending, PAUSED, RECONCILING, UNKNOWN and terminal SUCCEEDED/FAILED/CANCELLED. Restart/offline recovery reconciles state rather than replaying start. Events are cursor-paginated; one payload per page fits the C6 frame budget.

`frames.json` contains fixed frame vectors, including fragmented-stream decoding targets and a task request. Tests verify identical encoded bytes and decoded JSON against the independent car implementation when present. These examples are fixtures, not live commands.
