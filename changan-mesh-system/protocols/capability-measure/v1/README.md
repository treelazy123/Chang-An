# Capability application receipt measurement v1

The receiver is UGV Service. The node measures the interval from entry into its
capability publication routine to matching an application receipt on that node's
monotonic clock. The interval includes payload construction, MQTT enqueue, the
existing MQTT/TLS/Mesh/root-USB/Broker path, Service validation and durable commit,
the return path, and node command processing. It excludes the later result upload
and the terminal's display/query time. It is named
`capability_receipt_rtt_upper_bound`, not an exact one-way latency or RTT/2.

An interval <=800000 microseconds proves that the receiver accepted the capability
within 800ms. A greater interval does not prove a one-way violation. Missing,
interrupted and timed-out records are never counted as zero or as success.

## Existing MQTT topics, additive fields

The normal retained `mesh/v1/nodes/NODE/capabilities` payload gains:

```json
{"cap_measure_v":1,"boot_id":"0123456789abcdef","cap_id":"0123456789abcdef-00000001","cap_seq":1,"sent_us":1234567}
```

Existing v/type/node_id, task_role, operations, task_types, task_status and optional
task_id/execution_mode remain. `cap_id` is boot ID plus an eight-digit lowercase
hex sequence; it is not reused during a boot, including MQTT reconnects.
`sent_us` is a node monotonic timestamp, not UTC. Test announcements also echo
`batch_id` and `probe_id`, both 32 lowercase hexadecimal characters.

Upgraded nodes publish spontaneous announcements in the [node MCI envelope](../../mci/v1/node-capabilities.md).
Probe responses to `cap.request` still use the legacy fields and are published
without retain so that the latest spontaneous MCI announcement remains cached.
The Service accepts both formats and preserves the received envelope for evidence.

UGV Service first uses the existing topic/body registry validation and inventory
authorization. Only live, non-retained deliveries are eligible. It stores the
original announcement and receipt token before publishing QoS1, non-retained on
the existing `mesh/v1/nodes/NODE/commands` topic:

```json
{"v":1,"type":"cap.receipt","target":"uav-001","boot_id":"0123456789abcdef","cap_id":"0123456789abcdef-00000001","cap_seq":1,"receipt_token":"0123456789abcdef0123456789abcdef"}
```

An identical duplicate announcement receives the same token and increments a
duplicate counter. Reusing the same node/cap_id with different contents is rejected.
PUBACK is not an application receipt. Cache delivery alone is not a live sample.

The node matches pending cap_id, boot_id, sequence and a 32-hex receipt token.
It uploads QoS1/non-retained `cap.result` on the existing telemetry topic:

```json
{"v":1,"type":"cap.result","node_id":"uav-001","boot_id":"0123456789abcdef","cap_id":"0123456789abcdef-00000001","cap_seq":1,"receipt_token":"0123456789abcdef0123456789abcdef","confirmed_us":1254567,"elapsed_us":20000}
```

Service checks the token, source, boot, sequence, and exact equality
`confirmed_us - sent_us == elapsed_us`. The pending receipt window is 2000000us.
Timeout reports have `error:"receipt_timeout"` and omit elapsed_us, confirmed_us
and receipt_token. Pending storage is bounded to eight records; overflow never
overwrites a pending interval. Unmeasured announcements remain unconfirmed.
Results that cannot yet enter the MQTT outbox are retried without changing their
measured endpoint. Disconnect clears pending state; no interval crosses sessions.

Test requests are QoS1/non-retained command-topic messages:

```json
{"v":1,"type":"cap.request","target":"uav-001","boot_id":"0123456789abcdef","batch_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","probe_id":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","deadline_unix":1795600000}
```

The node requires the current boot, target identity, trusted clock and a valid
deadline no more than 60s ahead. The last 16 probe IDs are deduplicated. Service
only associates the first valid announcement with an active matching probe;
late/repeated requests never create extra successful planned samples. This
diagnostic does not create, start or alter physical tasks or change capabilities.

## Local HTTP v1 contract

These additive loopback endpoints use the same native-client/Origin restrictions
as the existing v1 adapter. There is no terminal MQTT identity or serial access.

- `POST /api/v1/capability-tests`: batch_id (32 lowercase hex), distinct nodes
  (1–16), count per node (1–100, default30), period_ms (200–10000, default1000).
  Same batch ID/config returns its saved state; different content conflicts.
- `GET /api/v1/capability-tests`: latest 50 batch headers.
- `GET /api/v1/capability-tests/BATCH`: complete bounded batch details and summary.
- `GET /api/v1/capability-tests/BATCH/export?format=jsonl|csv`: all planned records,
  including original announcement and result JSON. JSONL begins with a summary.

Only ready, authorized, root-scoped remote nodes advertising cap_measure_v=1 can
start a test. Exactly count×nodes planned records are persisted before dispatch.
One batch runs at a time; one request per node can be in flight. The period is a
minimum dispatch interval, not a guaranteed announcement rate. There is no
automatic request retry. Host timeout is five seconds from dispatch, including
result return. Service restart marks all WAIT/SENT/RECEIVED rows INTERRUPTED and
never automatically resumes them. Closing the terminal does not stop Service.

States: WAIT, SENT, RECEIVED, PASS, UPPER_BOUND_EXCEEDED, TIMEOUT, ERROR, NOT_READY,
INTERRUPTED. PASS is the sole proved-within-800ms state. The proved percentage uses
all planned records as denominator. Average/P95/maximum only include confirmed
PASS/UPPER_BOUND_EXCEEDED intervals; all failures and missing samples remain visible.
Classification uses integer microseconds, including the exact 800000us boundary.
`summary.registered` counts distinct planned samples whose valid announcement was
actually stored; it is separate from planned total and confirmed receipt count.
In records, sent/received/registered are host epoch seconds (dispatch/accepted
callback/registration); sent_us and confirmed_us are node monotonic microseconds.
Only the two node timestamps may be subtracted for this measurement.

Persistent tables cap_batches, cap_probes and cap_announcements share the existing
task SQLite database. Raw normal announcements are recorded independently of test
batches. Threshold is fixed at800ms. HTTP results identify the metric explicitly;
old firmware/API availability errors must not be replaced by fabricated timing.

This instrumentation trusts the enrolled node's firmware clock report. It is not
an independent hardware time analyzer. It does not claim millisecond UTC clock
synchronization, peer-to-peer dissemination, terminal-render latency or actual
hardware acceptance from host protocol substitutes.
