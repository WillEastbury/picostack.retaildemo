#define _GNU_SOURCE

#include "picowal_api.h"
#include "picowal_retail.h"
#include "picowal_store_fs.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static picowal_fs_store_t g_fs;
static picowal_store_t g_store;
static picowal_retail_t g_retail;
static char g_json[PICOWAL_RETAIL_JSON_MAX];
static bool g_ready;

static const char *json_or_error(picowal_search_status_t status) {
    if (status == PICOWAL_SEARCH_OK) return g_json;
    snprintf(g_json, sizeof(g_json), "{\"error\":\"retail operation failed\",\"status\":%d}", (int)status);
    return g_json;
}

int demo_init(const char *root) {
    if (!root || !*root) return 0;
    if (!picowal_store_fs_open(&g_fs, root, &g_store)) return 0;
    picowal_api_set_store(&g_store);
    picowal_retail_init(&g_retail, 8, 9, 100, 10, 200);
    g_ready = true;
    return 1;
}

const char *demo_ingest(void) {
    if (!g_ready) {
        snprintf(g_json, sizeof(g_json), "{\"error\":\"demo not initialized\"}");
        return g_json;
    }
    picowal_search_status_t status = picowal_retail_ingest_demo(&g_retail);
    if (status != PICOWAL_SEARCH_OK) return json_or_error(status);
    snprintf(g_json, sizeof(g_json), "{\"ingested\":true}");
    return g_json;
}

const char *demo_products(void) {
    if (!g_ready) {
        snprintf(g_json, sizeof(g_json), "{\"error\":\"demo not initialized\"}");
        return g_json;
    }
    return json_or_error(picowal_retail_products_json(&g_retail, g_json, sizeof(g_json)));
}

const char *demo_product(const char *id) {
    if (!g_ready) {
        snprintf(g_json, sizeof(g_json), "{\"error\":\"demo not initialized\"}");
        return g_json;
    }
    return json_or_error(picowal_retail_product_json(&g_retail, id ? id : "", g_json, sizeof(g_json)));
}

const char *demo_search(const char *query) {
    if (!g_ready) {
        snprintf(g_json, sizeof(g_json), "{\"error\":\"demo not initialized\"}");
        return g_json;
    }
    return json_or_error(picowal_retail_search_json(&g_retail, query ? query : "", g_json, sizeof(g_json)));
}

const char *demo_recommend(const char *id) {
    if (!g_ready) {
        snprintf(g_json, sizeof(g_json), "{\"error\":\"demo not initialized\"}");
        return g_json;
    }
    return json_or_error(picowal_retail_recommend_json(&g_retail, id ? id : "", g_json, sizeof(g_json)));
}

const char *demo_event(const char *visitor_id, const char *event_type, const char *product_id) {
    if (!g_ready) {
        snprintf(g_json, sizeof(g_json), "{\"error\":\"demo not initialized\"}");
        return g_json;
    }
    picowal_search_status_t status = picowal_retail_record_event(
        &g_retail, 11,
        visitor_id ? visitor_id : "demo",
        event_type ? event_type : "detail-page-view",
        product_id ? product_id : "");
    if (status != PICOWAL_SEARCH_OK) return json_or_error(status);
    snprintf(g_json, sizeof(g_json), "{\"accepted\":true}");
    return g_json;
}
