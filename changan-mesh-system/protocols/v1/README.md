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

`kind:diagnostics` runs on C6 or the UGV host. The host additionally supports `network_diagnostics` and `task_monitor`; see [host services](../../docs/host-services.md). Create does not start. Common config: duration_s 1..3600; period_ms 200..10000. Network diagnostics requires probe_node; monitoring requires watch_task_id and accepts stale_after_s (default 10, 1..3600). New kinds require the configured UGV target, never a C6 target. Update is allowed only in CREATED and increments revision. Control supports start/pause/resume/cancel. One active task per physical node; the two new host kinds each have their own execution slot. Request deduplication, durable command_id, per-task op_seq, boot binding and expiry reject stale command replays. Submission/received ACK does not establish successful execution.

`list` optionally accepts `scope:services` to discover the two host services, using the existing `nodes` one-row-per-frame reply envelope. Omitted scope retains the node listing. Service rows include service_id, node_id, agent_type, service_type, capabilities, operations, availability, task_status, task_id and boot_id. This is query-based discovery, not a new peer announcement protocol. Valid executor feedback is recorded as optional feedback_at in task views; task event journal entries may include bounded result snapshots for GUI recovery. Legacy node results remain limited to 240 bytes; host-service result summaries allow 320 bytes, with the full 1024-byte reply limit still enforced.

States include CREATED, QUEUED, DISPATCHING, ACCEPTED, RUNNING, pause/resume/cancel pending, PAUSED, RECONCILING, UNKNOWN and terminal SUCCEEDED/FAILED/CANCELLED. Restart/offline recovery reconciles state rather than replaying start. Events are cursor-paginated; one payload per page fits the C6 frame budget.

`frames.json` contains fixed frame vectors, including fragmented-stream decoding targets and a task request. Tests verify identical encoded bytes and decoded JSON against the independent car implementation when present. These examples are fixtures, not live commands.

## Historical task deletion

`task.control` also supports `op:delete` with task_id and expected_revision, preserving the existing root gateway whitelist. Only terminal tasks (SUCCEEDED/FAILED/CANCELLED/REJECTED/EXPIRED) can be deleted; unfinished monitor references reject deletion with task_in_use_by_monitor. Owner checks apply; local-console retains administrative access. The reply is task.reply with stage:DELETED, deleted:true, task_id and state_seq, without a task object. Duplicate delete requests remain idempotent.

Deletion atomically removes the task, its operations and historical task events, retaining a minimal DELETED event for cursor clients, a deleted-ID tombstone and request fingerprints. Old mutation reply caches are replaced with deleted results; old creates cannot restore a deleted task. Deleted IDs cannot be reused. Deleted task.get/filtered task.events return task_not_found. Clients must remove DELETED task entries and ignore late snapshots for those IDs. Task listing cursors remain monotonic after deleting the highest task row. Device NVS and executor journals are not erased; late feedback for missing tasks is ignored.

## ESP32 workflow tests

The additional task kinds patrol (micro_uav role) and anomaly_review (uav role) require config.execution_mode=esp32_test. These are ESP32 workflow tests, not flight/controller operations. Each enrolled node advertises its role's kind, task_operations, execution_mode, task_status and active task_id in capabilities; state/identity changes refresh the retained declaration. Service IDs use actual node_id/patrol and node_id/anomaly-review. The directory also lists configured but unannounced instances as unavailable/firmware_required, with execution_mode=not_reported.

patrol config: area_id and point_ids contain 1–12 ASCII ID characters, 1–3 unique points; point_duration_s defaults to3 (1–60), anomaly_point defaults to0 (0 disables, otherwise1-based index). anomaly_review config: event_id, test_verdict (confirmed/cleared/inconclusive, default inconclusive), duration_s (default5, 1–60). Unknown fields and implicit/physical modes are rejected. Backend validates the worst-case512-byte task.command before storing create/update.

Workflow task.event result.mode is esp32_test. Patrol results contain stage, point, done, total and optional event_id. Exactly one test incident may be produced per patrol; event_id equals source task_id. Backend derives incident area/point from the validated config and stores it only after accepting authenticated, boot/operation/sequence-bound feedback. Review results contain event_id, stage and verdict; the successful verdict must match the configured test_verdict. Result summaries retain the240-byte node limit.

task.events with scope:incidents returns one incident per page using an independent cursor; optional task_id filters source_task_id. Omitted scope retains task-history behavior. Incidents include event_id, source_task_id, node_id, area_id, point_id, created, test:true and execution_mode:esp32_test, filtered by owner. Review creation requires an authorized incident. Deleting a source task with unfinished review references fails task_in_use_by_review; independent incident snapshots remain after permitted historical task deletion.

Firmware persists the v2 journal under m1_task/journal_v2, migrates the old v1 journal without erasing it, and reports nonterminal tasks as UNKNOWN after restart. No automatic mission or workflow restart is performed. See [workflow setup and acceptance](../../docs/esp32-workflows.md).
