# Vendored components

This directory preserves the previously working local component copies and their licenses, patches and version metadata. Firmware loads it through EXTRA_COMPONENT_DIRS; Component Manager remains disabled.

`vendor-lock.json` records provenance and pre-port source hashes; only directory locations changed during this migration. `mqtt-source-lock.json` records the esp-mqtt archive. Port modifications already present in the original source are preserved. See the Git baseline and `docs/migration-source-manifest.json` for the actual migrated source hashes.

Do not run an automatic dependency update during structural refactors. IDF 6.1 compatibility is limited to the current ESP32-C6 Wi-Fi use; the shared SDK is not patched in place.
