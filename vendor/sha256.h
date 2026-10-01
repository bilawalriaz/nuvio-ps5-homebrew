/* SHA-256 and HMAC-SHA-256.
 *
 * Self-contained, no dependencies, no allocation. Needed because the worker has
 * no crypto library available and the protocol uses HMAC for session binding
 * (see docs/PROTOCOL.md). Also backs the deterministic `hash` job.
 *
 * This is a straightforward FIPS 180-4 implementation. It is not
 * constant-time-hardened in general, but the MAC comparison in protocol.c uses
 * a constant-time compare, which is the part that matters here.
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

#define SHA256_DIGEST_SIZE 32
#define SHA256_BLOCK_SIZE  64

typedef struct {
  uint32_t state[8];
  uint64_t bitlen;
  uint8_t  buf[SHA256_BLOCK_SIZE];
  size_t   buflen;
} sha256_ctx;

void sha256_init(sha256_ctx *ctx);
void sha256_update(sha256_ctx *ctx, const void *data, size_t len);
void sha256_final(sha256_ctx *ctx, uint8_t out[SHA256_DIGEST_SIZE]);

/* One-shot convenience wrapper. */
void sha256(const void *data, size_t len, uint8_t out[SHA256_DIGEST_SIZE]);

typedef struct {
  sha256_ctx inner;
  uint8_t    opad[SHA256_BLOCK_SIZE];
} hmac_sha256_ctx;

void hmac_sha256_init(hmac_sha256_ctx *ctx, const void *key, size_t keylen);
void hmac_sha256_update(hmac_sha256_ctx *ctx, const void *data, size_t len);
void hmac_sha256_final(hmac_sha256_ctx *ctx, uint8_t out[SHA256_DIGEST_SIZE]);

/* One-shot HMAC. */
void hmac_sha256(const void *key, size_t keylen,
                 const void *msg, size_t msglen,
                 uint8_t out[SHA256_DIGEST_SIZE]);
