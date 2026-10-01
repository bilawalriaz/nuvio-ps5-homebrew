#!/usr/bin/env python3
"""ELF validation for PS5 payloads, plus build-id extraction.

Why this exists, and why it is stricter than `file`:

elfldr derives the size of an incoming payload from the ELF **section headers**
(`ps5-payload-dev/elfldr`, `elfldr.c` `elfldr_read()`):

    size = ehdr.e_shoff + ehdr.e_shnum * sizeof(Elf64_Ehdr);
    buf  = malloc(size);
    memcpy(buf, &ehdr, sizeof(ehdr));      /* 64 bytes */

If a payload has been stripped, `e_shoff` and `e_shnum` are both 0, so `size` is
0, `malloc(0)` hands back a zero-sized block, and that 64-byte memcpy overflows
it inside the loader's process. Sending a stripped payload is therefore not merely
useless -- it can corrupt the loader.

So: a payload is rejected unless it has section headers. See docs/KNOWN_ISSUES.md
KI-002.

This module has no third-party dependencies. If `pyelftools` happens to be
installed, `describe()` adds section-level detail, but nothing requires it.
"""

from __future__ import annotations

import os
import struct
import sys
from dataclasses import dataclass, field

ELF_MAGIC = b"\x7fELF"
EM_X86_64 = 62
ET_EXEC = 2
ET_DYN = 3

BUILD_ID_MARKER = b"PS5HBD-BUILD-ID:"

# Refuse anything implausibly large for a payload before we try to send it.
MAX_PAYLOAD_BYTES = 256 * 1024 * 1024


class ElfError(Exception):
    """The file exists but is not a payload we are willing to send."""


@dataclass
class ElfInfo:
    path: str
    size: int
    elf_class: int
    data_encoding: int
    e_type: int
    e_machine: int
    e_entry: int
    e_shoff: int
    e_shnum: int
    build_id: str | None = None
    section_names: list[str] = field(default_factory=list)

    @property
    def type_name(self) -> str:
        return {ET_EXEC: "ET_EXEC", ET_DYN: "ET_DYN"}.get(self.e_type, f"0x{self.e_type:x}")

    @property
    def machine_name(self) -> str:
        return "EM_X86_64" if self.e_machine == EM_X86_64 else f"0x{self.e_machine:x}"

    def summary(self) -> str:
        bits = f"{self.size:,} bytes"
        deps = f"{self.type_name} {self.machine_name} entry=0x{self.e_entry:x}"
        build = f" build_id={self.build_id}" if self.build_id else " build_id=<not found>"
        return f"{os.path.basename(self.path)}: {bits}, {deps},{build}"


def _parse_header(data: bytes, path: str) -> ElfInfo:
    if len(data) < 64:
        raise ElfError(f"{path}: too small to be an ELF ({len(data)} bytes)")
    if data[:4] != ELF_MAGIC:
        raise ElfError(f"{path}: bad magic {data[:4]!r} (expected {ELF_MAGIC!r})")

    elf_class = data[4]
    data_encoding = data[5]
    if elf_class != 2:
        raise ElfError(f"{path}: not a 64-bit ELF (EI_CLASS={elf_class})")
    if data_encoding != 1:
        raise ElfError(f"{path}: not little-endian (EI_DATA={data_encoding})")

    (e_type, e_machine) = struct.unpack_from("<HH", data, 16)
    (e_entry,) = struct.unpack_from("<Q", data, 24)
    (e_shoff,) = struct.unpack_from("<Q", data, 40)
    (e_shnum,) = struct.unpack_from("<H", data, 60)

    info = ElfInfo(
        path=path,
        size=len(data),
        elf_class=elf_class,
        data_encoding=data_encoding,
        e_type=e_type,
        e_machine=e_machine,
        e_entry=e_entry,
        e_shoff=e_shoff,
        e_shnum=e_shnum,
    )

    idx = data.find(BUILD_ID_MARKER)
    if idx >= 0:
        start = idx + len(BUILD_ID_MARKER)
        end = data.find(b"\x00", start)
        if end < 0:
            end = start + 128
        raw = data[start:end]
        try:
            candidate = raw.decode("ascii")
        except UnicodeDecodeError:
            candidate = None
        if candidate and candidate.isprintable():
            info.build_id = candidate

    return info


def validate(path: str, *, require_sections: bool = True) -> ElfInfo:
    """Validate a payload artifact, raising ElfError with a specific reason."""
    if not os.path.exists(path):
        raise ElfError(f"{path}: does not exist")
    if os.path.isdir(path):
        raise ElfError(f"{path}: is a directory")

    size = os.path.getsize(path)
    if size == 0:
        raise ElfError(f"{path}: is empty (0 bytes)")
    if size > MAX_PAYLOAD_BYTES:
        raise ElfError(
            f"{path}: {size:,} bytes exceeds the {MAX_PAYLOAD_BYTES:,}-byte payload limit"
        )

    with open(path, "rb") as fh:
        data = fh.read()

    info = _parse_header(data, path)

    if info.e_machine != EM_X86_64:
        raise ElfError(
            f"{path}: wrong machine ({info.machine_name}); PS5 payloads are x86-64. "
            "Did you build for the host by mistake?"
        )
    if info.e_type not in (ET_DYN, ET_EXEC):
        raise ElfError(f"{path}: unexpected ELF type {info.type_name}")

    if require_sections and (info.e_shoff == 0 or info.e_shnum == 0):
        raise ElfError(
            f"{path}: has no section headers (e_shoff={info.e_shoff}, e_shnum={info.e_shnum}).\n"
            "  The loader derives the transfer length from them, so this payload would be\n"
            "  mis-framed and can corrupt the loader's heap. Do not strip payloads.\n"
            "  See docs/KNOWN_ISSUES.md KI-002."
        )

    if require_sections:
        if info.e_shoff < 64:
            raise ElfError(f"{path}: section headers overlap the ELF header")
        if struct.unpack_from("<H", data, 58)[0] != 64:
            raise ElfError(f"{path}: section header entry size must be 64")
        end = info.e_shoff + info.e_shnum * 64
        if end > len(data):
            raise ElfError(
                f"{path}: section header table runs past EOF "
                f"(declared end {end}, file size {len(data)})"
            )

    if require_sections:
        # Mirror elfldr's framing, including sections located after the table.
        # Trailing bytes would become stdin for the spawned payload.
        framed_end = end
        for i in range(info.e_shnum):
            off = info.e_shoff + i * 64
            kind = struct.unpack_from("<I", data, off + 4)[0]
            section_off, section_size = struct.unpack_from("<QQ", data, off + 24)
            if kind == 8:  # SHT_NOBITS occupies memory, not file bytes.
                continue
            section_end = section_off + section_size
            if section_end > len(data):
                raise ElfError(f"{path}: section {i} runs past EOF")
            framed_end = max(framed_end, section_end)
        if framed_end != len(data):
            raise ElfError(f"{path}: trailing bytes outside loader framing")

    info.section_names = _section_names(data, info)
    return info


def _section_names(data: bytes, info: ElfInfo) -> list[str]:
    """Best-effort section names. Purely informational, never required."""
    try:
        (e_shstrndx,) = struct.unpack_from("<H", data, 62)
        if e_shstrndx == 0 or e_shstrndx >= info.e_shnum:
            return []
        off = info.e_shoff + e_shstrndx * 64
        (strtab_off,) = struct.unpack_from("<Q", data, off + 24)
        (strtab_size,) = struct.unpack_from("<Q", data, off + 32)
        strtab = data[strtab_off : strtab_off + strtab_size]

        names: list[str] = []
        for i in range(info.e_shnum):
            s = info.e_shoff + i * 64
            (name_off,) = struct.unpack_from("<I", data, s)
            if name_off >= len(strtab):
                continue
            end = strtab.find(b"\x00", name_off)
            raw = strtab[name_off:end if end >= 0 else len(strtab)]
            names.append(raw.decode("ascii", "replace"))
        return names
    except Exception:
        return []


def describe(path: str) -> str:
    """Detailed, human-readable report."""
    info = validate(path)
    lines = [
        f"path            {info.path}",
        f"size            {info.size:,} bytes",
        f"class           ELF64, little-endian",
        f"type            {info.type_name}",
        f"machine         {info.machine_name}",
        f"entry           0x{info.e_entry:x}",
        f"section headers {info.e_shnum} at offset 0x{info.e_shoff:x}",
        f"build id        {info.build_id or '<not found>'}",
    ]
    if info.section_names:
        wanted = ("sha256", "protocol", "ps5util", "main", "text", "rodata", "bss")
        present = [n for n in info.section_names if any(w in n for w in wanted)]
        if present:
            lines.append(f"notable sections {', '.join(present[:8])}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        print("\nusage: elfcheck.py [--quiet] [--build-id] PAYLOAD.elf [...]")
        return 0 if len(argv) >= 2 else 2

    quiet = "--quiet" in argv
    build_id_only = "--build-id" in argv
    paths = [a for a in argv[1:] if not a.startswith("--")]

    if not paths:
        print("elfcheck.py: no payload given", file=sys.stderr)
        return 2

    failed = 0
    for path in paths:
        try:
            info = validate(path)
        except ElfError as exc:
            print(f"FAIL {exc}", file=sys.stderr)
            failed += 1
            continue

        if build_id_only:
            print(info.build_id or "")
            continue
        if quiet:
            print(info.summary())
        else:
            print(describe(path))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
