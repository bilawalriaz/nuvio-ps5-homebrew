# Glossary

| Term | Meaning in this project |
|---|---|
| Addon | A service that supplies catalogue, metadata or stream information to Nuvio or EVO. |
| Browser state | The private stored account, profile, addon and route data for one UI origin. |
| Build receipt | The generated JSON file with native file, helper and input hashes. |
| Content version | The `contentVersion` in `sce_sys/param.json`. A console compares it to find updates. |
| Decoder | The component that converts compressed video into frames. |
| Demuxer | The component that separates audio, video and other streams from media input. |
| ELF | The executable format accepted by the configured payload loader. |
| Folder title | A native homebrew app stored as a directory below `/data/homebrew`. |
| Handoff | The transition between Nuvio in the browser and the native playback engine. |
| Helper | A fixed-purpose ELF payload that supports installation, launch or permission. |
| Host | The computer that builds the port. It no longer serves the UI. |
| Installed receipt | A preserved receipt for files that reached the console. |
| Loopback | A network address that refers to the same machine, here the console. |
| Native player | EVO's playback code that runs as the PS5 title. |
| Origin | The protocol, host and port for the Nuvio UI server. |
| Payload | A PS5 ELF program sent to the loader, separate from the native title. |
| Payload Manager | The PS5 Payload Manager homebrew tool that loads payloads from a source file. |
| Pin | A fixed source revision or release with a recorded archive hash. |
| Proxy | EVO's console service that forwards UI requests to the host. |
| Release asset | A file attached to a GitHub release. The store pins one asset per title. |
| Route | A Nuvio page identifier with its saved parameters. |
| RML | The document format that RmlUi uses for the native interface. |
| SHA-256 | The hash function used to check whether file bytes match a receipt. |
| Store catalog | The PS5 Homebrew Store catalog that lists native PS5 homebrew by title ID. |
| Watcher | The resident helper that checks Nuvio process permissions during one boot. |
