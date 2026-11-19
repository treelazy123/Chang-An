#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

/* Maximum bytes the frame queue will buffer per frame. */
#ifndef IMAGE_FRAME_MAX
#define IMAGE_FRAME_MAX 32768
#endif

/* Static embedded asset (see image_assets.gen.h); internal to this component. */
typedef struct {
    const char *name;
    const uint8_t *data;
    size_t len;
} image_asset_t;

/* One queued frame. The producer fills `id` (a filename-safe token, ideally with a
 * file extension) and the bytes; the transport (mqtt_serial) streams it in chunks. */
typedef struct {
    char id[33];
    uint8_t *data;
    size_t len;
} image_frame_t;

/* Call once from a task context before any other API. */
void image_upload_init(void);

/* Producer: enqueue a copy of [data, data+len) under `id`. When the queue is full
 * the oldest frame is dropped so the newest frame always wins (video semantics).
 * Returns false only on invalid input or allocation failure. */
bool image_upload_enqueue(const char *id, const uint8_t *data, size_t len);

/* Seed the queue from the embedded static images (self-test mode when no video
 * frame source is connected; a no-op on non-leaf builds where none are embedded). */
void image_upload_prime(void);

/* Consumer: pop the oldest frame (non-blocking; NULL when empty). The caller owns
 * the result and must pass it to image_upload_release() once done streaming it. */
image_frame_t *image_upload_pop(void);
void image_upload_release(image_frame_t *frame);

size_t image_upload_queued(void);
