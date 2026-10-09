#ifndef NUVIO_BOOTSTRAP_H
#define NUVIO_BOOTSTRAP_H
#include <stddef.h>
/* Caller owns an already nonblocking fd. Transfers the fixed ELF and requires a complete promotion
 * response. All I/O shares one bounded deadline. */
int nuvio_bootstrap_transfer(int fd, const unsigned char *payload, size_t length);
int nuvio_bootstrap(void);
const char *nuvio_bootstrap_stage(void);
#endif
