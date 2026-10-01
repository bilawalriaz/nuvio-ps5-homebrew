"""Produce reviewable unified patches from verified upstream archives."""
import difflib,io,tarfile
from pathlib import Path


def write_patch(archive,source,destination):
    output=[]
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            relative=Path(*Path(member.name).parts[1:])
            if member.isfile() and relative.suffix in ('.c','.h','.cpp','.hpp','.js','.json','.sh'):
                target=source/relative
                if not target.is_file():continue
                original=tar.extractfile(member).read()
                changed=target.read_bytes()
                if original==changed:continue
                try:
                    before=original.decode().splitlines(keepends=True);after=changed.decode().splitlines(keepends=True)
                except UnicodeDecodeError:continue
                output.extend(difflib.unified_diff(before,after,fromfile='a/'+str(relative),tofile='b/'+str(relative)))
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(''.join(output))
