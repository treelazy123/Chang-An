# Mesh discovery control v1

Existing root advertisements retain message name `changan_ugv_mqtt_v1` and fields
`node_id`, `ip`, `ap_ip`, `broker`, `epoch`, `generation`, `port`.

The optional JSON action `changan_ugv_mqtt_query_v1` requests a fresh advertisement
from the immediate parent using the existing Mesh control transport:

```json
{"root_id":"ugv-root","node_id":"uav-001"}
```

`root_id` must match the configured managed root. `node_id` describes the requester
and does not authenticate it. A query only wakes/coalesces discovery work; it never
grants admission, dispatches tasks or changes relay/STA authorization. Leaves do
not answer queries. Application messages continue over the existing MQTT/TLS path.

A parent replies by broadcasting its current root advertisement to children. An
intermediate parent without a live cache requests it upstream; old/expired caches
must not be sent. Root generates new advertisement generations. Relays preserve
root epoch/generation and never refresh cache age for duplicates of the same pair.

After obtaining an IP, a node with no valid service cache requests at most twice
per second for eight seconds. Parents coalesce queries, bound broadcasts to at
most ten per second and enter a 500ms advertisement period for eight seconds.
Steady-state periodic advertisement remains 3000ms and cache TTL remains 15000ms.
Lost queries/replies can fall back to periodic advertisements. Old firmware may
ignore the query action; no MQTT/HTTP/WS envelope change is required.

Discovery is a locator, not a trust anchor. Existing broker certificate name,
client mTLS, inventory/ACL checks and parent-proof validation remain required.
