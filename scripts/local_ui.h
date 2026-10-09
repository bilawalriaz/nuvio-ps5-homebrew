/* Nuvio title-local browser assets. SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef NUVIO_LOCAL_UI_H
#define NUVIO_LOCAL_UI_H
#include <stddef.h>

/* Caller owns the socket. Return HTTP status, or -1 for an incomplete transfer.
 * root is a trusted installed title directory. Every child component is opened
 * without following symlinks. hook is inserted after the HTML head opening. */
int nuvio_local_ui_send(int fd, const char *root, const char *method,
                        const char *target, const char *hook, size_t hook_len);
#endif
