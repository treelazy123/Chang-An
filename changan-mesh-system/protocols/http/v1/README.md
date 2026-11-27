# Local terminal HTTP / WebSocket v1

The independent terminal communicates directly with UGV Service; no cloud simulator
or terminal MQTT connection is involved. Default: `http://127.0.0.1:8080`.
The default binding is loopback. Jetson may bind one explicit LAN address and allow configured peers through `[service].http_host` and `[service].http_allowed_peers`. The same peer and Host checks apply to all v1 routes, including MCI. Browser Origin requests are rejected. The server binds the caller to the stable local
operator `http-local`; packet fields cannot select another owner or administrator.
Persisted tasks retain their owner; state files are not rewritten automatically.

## HTTP

- `GET /api/v1/health`: v, root_id, broker_connected, mode.
- `POST /api/v1/requests`: one JSON v1 business request; returns one JSON reply.
- `GET /api/v1/nodes/catalog`: persisted administrator registration and last node
  observation. Observations are history, never evidence that a device is live now.
- `POST /api/v1/nodes/{node_id}/admission`: msg_id, deadline_unix, trust_status
  (pending/trusted/revoked), expected_revision. Also available as node.admission
  via the common request endpoint with target=node_id. The server owns caller identity.

Admission is managed inside UGV Service. Only registered nodes owned by this root
can be managed; granting requires an existing valid client certificate. Revision
conflicts and conflicting request IDs are rejected. A durable intent precedes the
atomic inventory change, allowing an interrupted change to be reconciled on retry.
The reply includes trust_status, admission_revision, broker_acl_applied=false and
broker_acl_reload_required=true. A pending ACL file is generated; no production
Broker reload or disconnect is performed. Revocation blocks new backend dispatch
but does not imply that an already-running physical task stopped.

Requests use the existing operation names and business fields described in
[`protocols/v1`](../../v1/README.md): list, command, task.create/get/list/control/update/events.
The HTTP envelope has `v:1`, `type`, `msg_id`, `deadline_unix`; the server binds node_id.
Deadline is at most 60 seconds into the future. The adapter does not manufacture a
new request ID or deadline on retry. JSON duplicate keys and non-finite values are rejected.
Request limit is 16 KiB. The physical-node command limit is 1024 bytes for
upgraded nodes and 512 bytes for legacy nodes.

List results aggregate the existing node pages into one `nodes` response with
`more:false`. Task/event pagination retains cursor/more semantics. Protocol errors
return the existing `type:error` body; malformed HTTP JSON uses HTTP 400. Queue
overload returns service_busy. On request_timeout_query_state, query the task ID;
the operation might already have been persisted. No mutation is automatically retried.
UGV_RECEIVED means persisted acceptance, not execution completion.

## Capability diagnostics

Capability diagnostics additionally expose `POST/GET /api/v1/capability-tests`,
`GET /api/v1/capability-tests/BATCH` and `GET /api/v1/capability-tests/BATCH/export`.
The independent terminal uses these additive v1 HTTP endpoints for measurement
batches; existing operations continue through their existing MCI adapter.
See [capability measurement v1](../../capability-measure/v1/README.md) for fields,
idempotency, persistence and the one-way latency upper-bound interpretation.

## WebSocket

`GET /api/v1/events?cursor=0` upgrades to a read-only event stream:

- `task.event`: durable cursor plus task_id/state/state_seq/revision/progress etc.
  Events are scoped to http-local. Reconnect with the last processed cursor; history
  is read from SQLite, including while the local Broker is unavailable.
- `nodes.snapshot`: current observed node list and broker_connected. Valid node
  observations and Broker connection changes wake streams immediately; a two-second
  fallback refresh covers expiry and other changes. Updates may be coalesced and
  are not a durable stream. No inference of physical parents is added.

Client text messages close the stream; use HTTP for operations. A connection has
heartbeat and bounded messages; clients can also recover via task.events HTTP queries.
The independent HTTP adapter reconnects event streams and deduplicates cursors.

Node commands still use local Mosquitto mTLS and existing boot/revision/op-sequence
checks. Cloud identity, wireless-layer access blocking and data-transfer protocols
are not implemented by this local adapter.
# Micro父节点选择扩展

POST /api/v1/requests支持type=node.parent.get及node.parent，通用v/msg_id/deadline_unix规则不变。
查询传target；修改另外传mode（auto/prefer/fixed）、parent（auto时null）、expected_revision。
回复type=node.parent.reply，包含target、revision、mode、parent及state；有配置时包含实际BSSID。
查询结果的revision用于下一次修改，不能用准入授权版本替代。
node.parent的请求ID持久化去重；修改超时或结果uncertain时先查询，不自动重发。
nodes列表及WS nodes.snapshot中的Micro行附带parent_policy，区分配置接收与实际生效。
详见[父节点选择](../../../docs/operations.md#parent-selection)。
