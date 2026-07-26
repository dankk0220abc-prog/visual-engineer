import argparse
import hashlib
import os
import stat
from pathlib import Path


def fingerprint(root: Path) -> str:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise SystemExit("Fingerprint target must be a directory")
    digest = hashlib.sha256()
    stack = [resolved]
    while stack:
        directory = stack.pop()
        children = sorted(os.scandir(directory), key=lambda item: item.name)
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(resolved).as_posix()
            metadata = child.stat(follow_symlinks=False)
            file_type = stat.S_IFMT(metadata.st_mode)
            digest.update(relative.encode("utf-8"))
            digest.update(f":{file_type}:{stat.S_IMODE(metadata.st_mode)}:".encode())
            if stat.S_ISDIR(metadata.st_mode):
                digest.update(b"directory")
                stack.append(path)
            elif stat.S_ISLNK(metadata.st_mode):
                digest.update(os.readlink(path).encode("utf-8"))
            elif stat.S_ISREG(metadata.st_mode):
                with path.open("rb") as source:
                    for block in iter(lambda: source.read(64 * 1024), b""):
                        digest.update(block)
            else:
                digest.update(f"special:{metadata.st_rdev}".encode())
            digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args()
    print(fingerprint(arguments.root))


if __name__ == "__main__":
    main()
