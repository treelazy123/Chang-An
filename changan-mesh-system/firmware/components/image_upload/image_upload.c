#include "image_upload.h"
#include "image_assets.gen.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include <stdlib.h>
#include <string.h>

#define IMAGE_QUEUE_LEN 4

static QueueHandle_t queue;

void image_upload_init(void) {
    if (queue == NULL) {
        queue = xQueueCreate(IMAGE_QUEUE_LEN, sizeof(image_frame_t *));
    }
}

static image_frame_t *frame_alloc(const char *id, const uint8_t *data, size_t len) {
    image_frame_t *frame = calloc(1, sizeof(*frame));
    if (!frame) { return NULL; }
    frame->data = malloc(len);
    if (!frame->data) { free(frame); return NULL; }
    memcpy(frame->data, data, len);
    frame->len = len;
    strncpy(frame->id, id, sizeof(frame->id) - 1);
    frame->id[sizeof(frame->id) - 1] = '\0';
    return frame;
}

bool image_upload_enqueue(const char *id, const uint8_t *data, size_t len) {
    if (queue == NULL || id == NULL || data == NULL || len == 0 || len > IMAGE_FRAME_MAX) {
        return false;
    }
    image_frame_t *frame = frame_alloc(id, data, len);
    if (!frame) { return false; }
    /* Drop the oldest frame when full so the newest one always wins. */
    while (xQueueSend(queue, &frame, 0) != pdTRUE) {
        image_frame_t *old = NULL;
        if (xQueueReceive(queue, &old, 0) != pdTRUE) {
            image_upload_release(frame);
            return false;
        }
        image_upload_release(old);
    }
    return true;
}

void image_upload_prime(void) {
    for (size_t i = 0; i < IMAGE_ASSET_COUNT; i++) {
        image_upload_enqueue(IMAGE_ASSETS[i].name, IMAGE_ASSETS[i].data, IMAGE_ASSETS[i].len);
    }
}

image_frame_t *image_upload_pop(void) {
    if (queue == NULL) { return NULL; }
    image_frame_t *frame = NULL;
    if (xQueueReceive(queue, &frame, 0) != pdTRUE) { return NULL; }
    return frame;
}

void image_upload_release(image_frame_t *frame) {
    if (frame == NULL) { return; }
    free(frame->data);
    free(frame);
}

size_t image_upload_queued(void) {
    return queue == NULL ? 0 : (size_t)uxQueueMessagesWaiting(queue);
}
