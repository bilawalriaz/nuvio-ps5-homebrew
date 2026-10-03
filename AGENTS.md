# Agent guidance

Read README.md, docs/ARCHITECTURE.md and docs/VALIDATION.md before changes.
Read docs/WRITING.md before editing documentation.

The target is a retail PS5 on firmware 13.60 with an active jailbreak and ELF loader.
Do not update the firmware.
Do not develop exploits.
Do not assume Linux, a replacement OS or hypervisor access.
Source inspection and compilation do not establish console execution.

Keep the title identity PPSA99997.
Keep persistent console writes under /data.
Require an explicit console address.
Do not scan for a console.
Do not invent offsets or platform symbols.
Read the actual SDK declarations and examples before using APIs.
Do not strip payload ELFs.
Keep the browser UI served from the console. Never require a network host for it.

Never commit owner configuration, addon URLs, credentials, logs or generated binaries.
Never commit Sony modules or console dumps.
The runtime comes from independently authored source, not extracted Sony code.
Preserve source pins, locally recorded checksums, attribution and GPL notices.

Run make check after an edit batch.
Build changed native code.
Record hardware hashes, environment versions and observed results in docs/VALIDATION.md.
Keep failed results and pending tests explicit.
