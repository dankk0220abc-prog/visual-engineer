from __future__ import annotations

import hashlib
import itertools
import os
import re
import stat
import struct
import uuid
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from visual_engineer_runner_protocol import FailureCode

_PACK_INDEX_MAGIC = b"\xfftOc"
_PACK_NAME = re.compile(r"^pack-([0-9a-f]+)$")
_HEX = frozenset("0123456789abcdef")
_OBJECT_TYPES = {1: "commit", 2: "tree", 3: "blob", 4: "tag"}
_TREE_MODES = {b"100644": "blob", b"100755": "blob", b"120000": "blob"}


class SourceObjectError(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True)
class ObjectLimits:
    max_objects: int
    max_bytes: int
    max_single_object_bytes: int
    max_pack_files: int
    max_delta_depth: int
    max_tree_depth: int
    max_tree_entries: int
    max_references: int
    max_graph_depth: int


@dataclass(frozen=True)
class ObjectRecord:
    object_type: str
    size: int


@dataclass(frozen=True)
class CheckoutManifestEntry:
    relative_path: bytes
    entry_type: str
    mode: int
    size: int
    sha256: str | None


@dataclass
class _PendingManifestDirectory:
    charged: bool = False


@dataclass(frozen=True)
class _FileSnapshot:
    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int

    @classmethod
    def from_stat(cls, metadata: os.stat_result) -> _FileSnapshot:
        return cls(
            device=metadata.st_dev,
            inode=metadata.st_ino,
            mode=metadata.st_mode,
            links=metadata.st_nlink,
            size=metadata.st_size,
            modified_ns=metadata.st_mtime_ns,
        )

    def matches(self, metadata: os.stat_result) -> bool:
        return self == self.from_stat(metadata)


@dataclass(frozen=True)
class _PackIndex:
    index_path: Path
    pack_path: Path
    index_snapshot: _FileSnapshot
    pack_snapshot: _FileSnapshot
    object_count: int
    offsets: dict[str, int]
    object_ids_by_offset: dict[int, str]
    crc_by_object_id: dict[str, int]
    pack_checksum: bytes


class SourceObjectClosure:
    """Read an exact Git object closure without invoking Git on the source."""

    def __init__(
        self,
        source_git: Path,
        *,
        object_id_hex_length: int,
        limits: ObjectLimits,
    ) -> None:
        if object_id_hex_length not in {40, 64}:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE)
        self._source_git = source_git
        self._objects = source_git / "objects"
        self._hex_length = object_id_hex_length
        self._hash_bytes = object_id_hex_length // 2
        self._hash_name = "sha1" if object_id_hex_length == 40 else "sha256"
        self._limits = limits
        self._packs_by_object_id: dict[str, _PackIndex] = {}
        self._packs: list[_PackIndex] = []
        self._verified_packs: set[Path] = set()
        self._verified_pack_bytes = 0
        self._selected_loose_snapshots: dict[Path, _FileSnapshot] = {}
        self._records: dict[str, ObjectRecord] = {}
        self._tree_heights: dict[str, int] = {}
        self._tree_entries = 0
        self._references = 0
        self._decompressed_bytes = 0
        self._scan_source_layout()

    def collect(
        self,
        root_object_id: str,
        *,
        require_fresh: Callable[[], None],
    ) -> dict[str, ObjectRecord]:
        self._require_object_id(root_object_id)
        pending: list[tuple[str, int]] = [(root_object_id, 0)]
        seen_commits: set[str] = set()
        while pending:
            require_fresh()
            object_id, ancestry_depth = pending.pop()
            if ancestry_depth > self._limits.max_graph_depth:
                self._budget_error()
            if object_id in seen_commits:
                continue
            object_type, content = self._read_object(
                object_id,
                require_fresh=require_fresh,
            )
            if object_type != "commit":
                self._source_error()
            self._record(object_id, object_type, content)
            seen_commits.add(object_id)
            tree_id, parents = self._parse_commit(content)
            self._reference(1 + len(parents))
            self._walk_tree(
                tree_id,
                depth=0,
                active=set(),
                require_fresh=require_fresh,
            )
            for parent in reversed(parents):
                pending.append((parent, ancestry_depth + 1))
        self.validate_source_unchanged()
        return dict(self._records)

    def materialize(
        self,
        destination: Path,
        closure: dict[str, ObjectRecord],
        *,
        require_fresh: Callable[[], None],
    ) -> None:
        try:
            destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as exc:
            raise SourceObjectError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        self._require_destination_directory(destination)
        self._validate_destination(destination, closure)
        storage_bytes = self._destination_storage_bytes(destination)
        for object_id in sorted(closure):
            require_fresh()
            destination_file = destination / object_id[:2] / object_id[2:]
            if destination_file.exists():
                continue
            object_type, content = self._read_object(
                object_id,
                require_fresh=require_fresh,
            )
            expected = closure[object_id]
            if object_type != expected.object_type or len(content) != expected.size:
                self._source_error()
            raw = _canonical_object(object_type, content)
            compressed = zlib.compress(raw)
            if storage_bytes + len(compressed) > self._limits.max_bytes:
                self._budget_error()
            destination_file.parent.mkdir(mode=0o700, exist_ok=True)
            self._write_new_object(destination_file, compressed)
            storage_bytes += len(compressed)
        self._validate_destination(destination, closure, require_complete=True)
        self.validate_source_unchanged()

    def validate_materialized(
        self,
        destination: Path,
        closure: dict[str, ObjectRecord],
        *,
        require_fresh: Callable[[], None],
    ) -> None:
        """Validate an exact materialized closure without repairing it."""

        require_fresh()
        self._validate_destination(destination, closure, require_complete=True)
        require_fresh()
        self.validate_source_unchanged()

    def checkout_manifest(
        self,
        root_object_id: str,
        *,
        require_fresh: Callable[[], None],
    ) -> tuple[CheckoutManifestEntry, ...]:
        self._require_object_id(root_object_id)
        object_type, content = self._read_object(
            root_object_id,
            require_fresh=require_fresh,
        )
        if object_type != "commit":
            self._source_error()
        tree_id, _parents = self._parse_commit(content)
        entry_count = [0]
        entries = self._walk_checkout_manifest(
            tree_id,
            prefix=b"",
            depth=0,
            active=set(),
            entry_count=entry_count,
            pending_directories=(),
            require_fresh=require_fresh,
        )
        self.validate_source_unchanged()
        return tuple(sorted(entries, key=lambda entry: entry.relative_path))

    def validate_source_unchanged(self) -> None:
        for path, snapshot in self._selected_loose_snapshots.items():
            self._require_snapshot(
                path,
                snapshot,
                FailureCode.REPOSITORY_UNAVAILABLE,
            )
        for pack in self._packs:
            self._require_snapshot(
                pack.index_path,
                pack.index_snapshot,
                FailureCode.REPOSITORY_UNAVAILABLE,
            )
            self._require_snapshot(
                pack.pack_path,
                pack.pack_snapshot,
                FailureCode.REPOSITORY_UNAVAILABLE,
            )

    def _scan_source_layout(self) -> None:
        self._reject_source_indirection()
        try:
            metadata = os.lstat(self._objects)
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            self._source_error()
        pack_directory: Path | None = None
        try:
            with os.scandir(self._objects) as entries:
                for entry in entries:
                    if entry.name == "info":
                        self._require_source_directory(Path(entry.path))
                        continue
                    if entry.name == "pack":
                        self._require_source_directory(Path(entry.path))
                        pack_directory = Path(entry.path)
                        continue
                    if len(entry.name) == 2 and all(character in _HEX for character in entry.name):
                        self._require_source_directory(Path(entry.path))
                        continue
                    self._source_error()
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if pack_directory is not None:
            self._scan_pack_directory(pack_directory)

    def _reject_source_indirection(self) -> None:
        forbidden = (
            self._objects / "info" / "alternates",
            self._objects / "info" / "http-alternates",
            self._source_git / "info" / "grafts",
            self._source_git / "refs" / "replace",
        )
        for path in forbidden:
            try:
                os.lstat(path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
            self._source_error()

    def _scan_pack_directory(self, pack_directory: Path) -> None:
        pack_paths: dict[str, Path] = {}
        index_paths: dict[str, Path] = {}
        auxiliary_stems: set[str] = set()
        entry_count = 0
        try:
            with os.scandir(pack_directory) as entries:
                for entry in entries:
                    entry_count += 1
                    if entry_count > self._limits.max_pack_files * 5:
                        self._budget_error()
                    path = Path(entry.path)
                    self._require_source_file(path)
                    stem = path.stem
                    match = _PACK_NAME.fullmatch(stem)
                    if match is None or len(match.group(1)) != self._hex_length:
                        self._source_error()
                    if path.suffix == ".pack":
                        pack_paths[stem] = path
                    elif path.suffix == ".idx":
                        index_paths[stem] = path
                    elif path.suffix in {".bitmap", ".keep", ".rev"}:
                        auxiliary_stems.add(stem)
                    else:
                        self._source_error()
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if set(pack_paths) != set(index_paths) or not auxiliary_stems.issubset(pack_paths):
            self._source_error()
        if len(pack_paths) > self._limits.max_pack_files:
            self._budget_error()
        catalog_objects = 0
        for stem in sorted(pack_paths):
            pack_path = pack_paths[stem]
            index_path = index_paths[stem]
            pack_snapshot = self._snapshot_source_file(pack_path)
            index_snapshot = self._snapshot_source_file(index_path)
            parsed = self._parse_pack_index(
                index_path,
                pack_path,
                index_snapshot=index_snapshot,
                pack_snapshot=pack_snapshot,
            )
            catalog_objects += parsed.object_count
            if catalog_objects > self._limits.max_objects * 8:
                self._budget_error()
            for object_id in parsed.offsets:
                if object_id in self._packs_by_object_id:
                    self._source_error()
                self._packs_by_object_id[object_id] = parsed
            self._packs.append(parsed)

    def _parse_pack_index(
        self,
        index_path: Path,
        pack_path: Path,
        *,
        index_snapshot: _FileSnapshot,
        pack_snapshot: _FileSnapshot,
    ) -> _PackIndex:
        maximum_index_bytes = (
            8 + 1024 + self._limits.max_objects * (self._hash_bytes + 16) + self._hash_bytes * 2
        )
        payload = self._read_stable_file(
            index_path,
            maximum_index_bytes,
            FailureCode.REPOSITORY_UNAVAILABLE,
            expected=index_snapshot,
        )
        if len(payload) < 8 + 1024 + self._hash_bytes * 2:
            self._source_error()
        if payload[:4] != _PACK_INDEX_MAGIC or struct.unpack(">I", payload[4:8])[0] != 2:
            self._source_error()
        expected_index_hash = hashlib.new(self._hash_name, payload[: -self._hash_bytes]).digest()
        if expected_index_hash != payload[-self._hash_bytes :]:
            self._source_error()
        fanout = struct.unpack(">256I", payload[8:1032])
        if any(left > right for left, right in itertools.pairwise(fanout)):
            self._source_error()
        object_count = fanout[-1]
        if object_count > self._limits.max_objects * 8:
            self._budget_error()
        object_ids_start = 1032
        crc_start = object_ids_start + object_count * self._hash_bytes
        offsets_start = crc_start + object_count * 4
        large_offsets_start = offsets_start + object_count * 4
        checksums_start = len(payload) - self._hash_bytes * 2
        if large_offsets_start > checksums_start:
            self._source_error()
        large_bytes = checksums_start - large_offsets_start
        if large_bytes % 8:
            self._source_error()
        large_count = large_bytes // 8
        large_offsets = (
            struct.unpack(f">{large_count}Q", payload[large_offsets_start:checksums_start])
            if large_count
            else ()
        )
        object_ids = [
            payload[
                object_ids_start + index * self._hash_bytes : object_ids_start
                + (index + 1) * self._hash_bytes
            ].hex()
            for index in range(object_count)
        ]
        if object_ids != sorted(set(object_ids)):
            self._source_error()
        calculated_fanout = [0] * 256
        for object_id in object_ids:
            calculated_fanout[int(object_id[:2], 16)] += 1
        running = 0
        for index, count in enumerate(calculated_fanout):
            running += count
            calculated_fanout[index] = running
        if tuple(calculated_fanout) != fanout:
            self._source_error()
        crc_values = struct.unpack(
            f">{object_count}I",
            payload[crc_start:offsets_start],
        )
        encoded_offsets = struct.unpack(
            f">{object_count}I",
            payload[offsets_start:large_offsets_start],
        )
        used_large: set[int] = set()
        offsets: dict[str, int] = {}
        object_ids_by_offset: dict[int, str] = {}
        for object_id, encoded in zip(object_ids, encoded_offsets, strict=True):
            if encoded & 0x80000000:
                large_index = encoded & 0x7FFFFFFF
                if large_index >= large_count:
                    self._source_error()
                used_large.add(large_index)
                offset = large_offsets[large_index]
            else:
                offset = encoded
            if offset < 12 or offset >= pack_snapshot.size - self._hash_bytes:
                self._source_error()
            if offset in object_ids_by_offset:
                self._source_error()
            offsets[object_id] = offset
            object_ids_by_offset[offset] = object_id
        if used_large != set(range(large_count)):
            self._source_error()
        pack_checksum = payload[checksums_start : checksums_start + self._hash_bytes]
        if pack_path.stem != f"pack-{pack_checksum.hex()}":
            self._source_error()
        return _PackIndex(
            index_path=index_path,
            pack_path=pack_path,
            index_snapshot=index_snapshot,
            pack_snapshot=pack_snapshot,
            object_count=object_count,
            offsets=offsets,
            object_ids_by_offset=object_ids_by_offset,
            crc_by_object_id=dict(zip(object_ids, crc_values, strict=True)),
            pack_checksum=pack_checksum,
        )

    def _read_object(
        self,
        object_id: str,
        *,
        require_fresh: Callable[[], None],
        delta_depth: int = 0,
        active: set[tuple[Path, int]] | None = None,
    ) -> tuple[str, bytes]:
        require_fresh()
        self._require_object_id(object_id)
        loose = self._objects / object_id[:2] / object_id[2:]
        try:
            os.lstat(loose)
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        else:
            loose_snapshot = self._snapshot_source_file(loose)
            previous_snapshot = self._selected_loose_snapshots.get(loose)
            if previous_snapshot is not None and previous_snapshot != loose_snapshot:
                self._source_error()
            payload = self._read_stable_file(
                loose,
                self._limits.max_single_object_bytes + 1024 * 1024,
                FailureCode.REPOSITORY_UNAVAILABLE,
                expected=loose_snapshot,
                require_single_link=True,
            )
            self._selected_loose_snapshots[loose] = loose_snapshot
            return self._parse_loose_object(
                payload,
                object_id,
                FailureCode.REPOSITORY_UNAVAILABLE,
            )
        pack = self._packs_by_object_id.get(object_id)
        if pack is None:
            self._source_error()
        return self._read_packed_object(
            pack,
            object_id,
            delta_depth=delta_depth,
            active=active or set(),
            require_fresh=require_fresh,
        )

    def _read_packed_object(
        self,
        pack: _PackIndex,
        object_id: str,
        *,
        delta_depth: int,
        active: set[tuple[Path, int]],
        require_fresh: Callable[[], None],
    ) -> tuple[str, bytes]:
        if delta_depth > self._limits.max_delta_depth:
            self._budget_error()
        self._verify_pack(pack, require_fresh=require_fresh)
        offset = pack.offsets.get(object_id)
        if offset is None:
            self._source_error()
        key = (pack.pack_path, offset)
        if key in active:
            self._source_error()
        active.add(key)
        descriptor = self._open_snapshot(pack.pack_path, pack.pack_snapshot)
        try:
            type_code, declared_size, data_offset, base = self._read_pack_entry_header(
                descriptor,
                pack,
                offset,
            )
            if declared_size > self._limits.max_single_object_bytes:
                self._budget_error()
            delta, compressed_end = self._decompress_pack_entry(
                descriptor,
                data_offset,
                pack.pack_snapshot.size - self._hash_bytes,
            )
            if compressed_end - offset > self._limits.max_single_object_bytes + 1024 * 1024:
                self._budget_error()
            if len(delta) != declared_size:
                self._source_error()
            crc = self._crc_range(descriptor, offset, compressed_end)
            if crc != pack.crc_by_object_id[object_id]:
                self._source_error()
            if type_code in _OBJECT_TYPES:
                object_type = _OBJECT_TYPES[type_code]
                content = delta
            elif type_code == 6:
                if not isinstance(base, int):
                    self._source_error()
                base_id = pack.object_ids_by_offset.get(base)
                if base_id is None:
                    self._source_error()
                base_type, base_content = self._read_packed_object(
                    pack,
                    base_id,
                    delta_depth=delta_depth + 1,
                    active=active,
                    require_fresh=require_fresh,
                )
                object_type = base_type
                content = self._apply_delta(base_content, delta)
            elif type_code == 7:
                if not isinstance(base, str):
                    self._source_error()
                base_type, base_content = self._read_object(
                    base,
                    delta_depth=delta_depth + 1,
                    active=active,
                    require_fresh=require_fresh,
                )
                object_type = base_type
                content = self._apply_delta(base_content, delta)
            else:
                self._source_error()
            if len(content) > self._limits.max_single_object_bytes:
                self._budget_error()
            if _object_id(self._hash_name, object_type, content) != object_id:
                self._source_error()
            self._require_descriptor_snapshot(descriptor, pack.pack_snapshot)
            return object_type, content
        finally:
            active.discard(key)
            os.close(descriptor)

    def _verify_pack(
        self,
        pack: _PackIndex,
        *,
        require_fresh: Callable[[], None],
    ) -> None:
        if pack.pack_path in self._verified_packs:
            self._require_snapshot(
                pack.pack_path,
                pack.pack_snapshot,
                FailureCode.REPOSITORY_UNAVAILABLE,
            )
            return
        if self._verified_pack_bytes + pack.pack_snapshot.size > self._limits.max_bytes:
            self._budget_error()
        descriptor = self._open_snapshot(pack.pack_path, pack.pack_snapshot)
        try:
            header = os.pread(descriptor, 12, 0)
            if (
                len(header) != 12
                or header[:4] != b"PACK"
                or struct.unpack(">I", header[4:8])[0] not in {2, 3}
                or struct.unpack(">I", header[8:12])[0] != pack.object_count
            ):
                self._source_error()
            digest = hashlib.new(self._hash_name)
            remaining = pack.pack_snapshot.size - self._hash_bytes
            position = 0
            while remaining:
                require_fresh()
                chunk = os.pread(descriptor, min(1024 * 1024, remaining), position)
                if not chunk:
                    self._source_error()
                digest.update(chunk)
                position += len(chunk)
                remaining -= len(chunk)
            trailer = os.pread(descriptor, self._hash_bytes, position)
            if trailer != digest.digest() or trailer != pack.pack_checksum:
                self._source_error()
            self._require_descriptor_snapshot(descriptor, pack.pack_snapshot)
        finally:
            os.close(descriptor)
        self._verified_packs.add(pack.pack_path)
        self._verified_pack_bytes += pack.pack_snapshot.size

    def _read_pack_entry_header(
        self,
        descriptor: int,
        pack: _PackIndex,
        offset: int,
    ) -> tuple[int, int, int, int | str | None]:
        position = offset
        first = self._read_pack_byte(descriptor, position, pack)
        position += 1
        type_code = (first >> 4) & 0x07
        size = first & 0x0F
        shift = 4
        current = first
        header_bytes = 1
        while current & 0x80:
            current = self._read_pack_byte(descriptor, position, pack)
            position += 1
            header_bytes += 1
            if header_bytes > 12:
                self._source_error()
            size |= (current & 0x7F) << shift
            shift += 7
        base: int | str | None = None
        if type_code == 6:
            current = self._read_pack_byte(descriptor, position, pack)
            position += 1
            distance = current & 0x7F
            base_bytes = 1
            while current & 0x80:
                current = self._read_pack_byte(descriptor, position, pack)
                position += 1
                base_bytes += 1
                if base_bytes > 12:
                    self._source_error()
                distance = ((distance + 1) << 7) | (current & 0x7F)
            if distance <= 0 or distance >= offset:
                self._source_error()
            base = offset - distance
        elif type_code == 7:
            raw_base = os.pread(descriptor, self._hash_bytes, position)
            if len(raw_base) != self._hash_bytes:
                self._source_error()
            position += self._hash_bytes
            base = raw_base.hex()
        return type_code, size, position, base

    def _decompress_pack_entry(
        self,
        descriptor: int,
        position: int,
        pack_data_end: int,
    ) -> tuple[bytes, int]:
        decompressor = zlib.decompressobj()
        output = bytearray()
        buffered = b""
        while not decompressor.eof:
            if not buffered:
                if position >= pack_data_end:
                    self._source_error()
                buffered = os.pread(descriptor, min(64 * 1024, pack_data_end - position), position)
                if not buffered:
                    self._source_error()
            maximum = self._limits.max_single_object_bytes + 1 - len(output)
            if maximum <= 0:
                self._budget_error()
            try:
                chunk = decompressor.decompress(buffered, maximum)
            except zlib.error as exc:
                raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
            output.extend(chunk)
            if len(output) > self._limits.max_single_object_bytes:
                self._budget_error()
            unconsumed = decompressor.unconsumed_tail
            unused = decompressor.unused_data if decompressor.eof else b""
            consumed = len(buffered) - len(unconsumed) - len(unused)
            if consumed <= 0 and not chunk:
                self._source_error()
            position += consumed
            buffered = unconsumed
        return bytes(output), position

    def _apply_delta(self, base: bytes, delta: bytes) -> bytes:
        source_size, position = _read_delta_varint(delta, 0)
        result_size, position = _read_delta_varint(delta, position)
        if source_size != len(base) or result_size > self._limits.max_single_object_bytes:
            self._source_error()
        output = bytearray()
        instructions = 0
        while position < len(delta):
            instructions += 1
            if instructions > self._limits.max_references:
                self._budget_error()
            opcode = delta[position]
            position += 1
            if opcode == 0:
                self._source_error()
            if opcode & 0x80:
                copy_offset = 0
                copy_size = 0
                for bit, shift in ((0x01, 0), (0x02, 8), (0x04, 16), (0x08, 24)):
                    if opcode & bit:
                        if position >= len(delta):
                            self._source_error()
                        copy_offset |= delta[position] << shift
                        position += 1
                for bit, shift in ((0x10, 0), (0x20, 8), (0x40, 16)):
                    if opcode & bit:
                        if position >= len(delta):
                            self._source_error()
                        copy_size |= delta[position] << shift
                        position += 1
                if copy_size == 0:
                    copy_size = 0x10000
                if copy_offset + copy_size > len(base):
                    self._source_error()
                output.extend(base[copy_offset : copy_offset + copy_size])
            else:
                insert_size = opcode
                if position + insert_size > len(delta):
                    self._source_error()
                output.extend(delta[position : position + insert_size])
                position += insert_size
            if len(output) > result_size:
                self._source_error()
        if len(output) != result_size:
            self._source_error()
        return bytes(output)

    def _walk_tree(
        self,
        object_id: str,
        *,
        depth: int,
        active: set[str],
        require_fresh: Callable[[], None],
    ) -> int:
        if depth > self._limits.max_tree_depth:
            self._budget_error()
        cached_height = self._tree_heights.get(object_id)
        if cached_height is not None:
            if depth + cached_height > self._limits.max_tree_depth:
                self._budget_error()
            return cached_height
        if object_id in active:
            self._source_error()
        active.add(object_id)
        object_type, content = self._read_object(
            object_id,
            require_fresh=require_fresh,
        )
        if object_type != "tree":
            self._source_error()
        self._record(object_id, object_type, content)
        entries = self._parse_tree(content)
        self._tree_entries += len(entries)
        if self._tree_entries > self._limits.max_tree_entries:
            self._budget_error()
        self._reference(len(entries))
        height = 0
        for entry_type, _mode, _name, child_id in entries:
            require_fresh()
            if entry_type == "gitlink":
                # A gitlink is inert superproject metadata. Its referenced
                # commit belongs to another object database and is neither
                # imported nor opened; submodule recursion stays disabled.
                continue
            if entry_type == "tree":
                child_height = self._walk_tree(
                    child_id,
                    depth=depth + 1,
                    active=active,
                    require_fresh=require_fresh,
                )
                height = max(height, child_height + 1)
                continue
            child_type, child_content = self._read_object(
                child_id,
                require_fresh=require_fresh,
            )
            if child_type != "blob":
                self._source_error()
            self._record(child_id, child_type, child_content)
        active.remove(object_id)
        if depth + height > self._limits.max_tree_depth:
            self._budget_error()
        self._tree_heights[object_id] = height
        return height

    def _walk_checkout_manifest(
        self,
        object_id: str,
        *,
        prefix: bytes,
        depth: int,
        active: set[str],
        entry_count: list[int],
        pending_directories: tuple[_PendingManifestDirectory, ...],
        require_fresh: Callable[[], None],
    ) -> list[CheckoutManifestEntry]:
        if depth > self._limits.max_tree_depth:
            self._budget_error()
        if object_id in active:
            self._source_error()
        active.add(object_id)
        object_type, content = self._read_object(
            object_id,
            require_fresh=require_fresh,
        )
        if object_type != "tree":
            self._source_error()
        entries: list[CheckoutManifestEntry] = []
        for entry_type, mode, name, child_id in self._parse_tree(content):
            require_fresh()
            relative_path = name if not prefix else prefix + b"/" + name
            if entry_type == "tree":
                directory_charge = _PendingManifestDirectory()
                children = self._walk_checkout_manifest(
                    child_id,
                    prefix=relative_path,
                    depth=depth + 1,
                    active=active,
                    entry_count=entry_count,
                    pending_directories=(*pending_directories, directory_charge),
                    require_fresh=require_fresh,
                )
                if children:
                    if not directory_charge.charged:
                        self._source_error()
                    entries.append(
                        CheckoutManifestEntry(
                            relative_path=relative_path,
                            entry_type="directory",
                            mode=mode,
                            size=0,
                            sha256=None,
                        )
                    )
                    entries.extend(children)
                continue
            if entry_type == "gitlink":
                self._charge_manifest_leaf(entry_count, pending_directories)
                entries.append(
                    CheckoutManifestEntry(
                        relative_path=relative_path,
                        entry_type="gitlink",
                        mode=mode,
                        size=0,
                        sha256=hashlib.sha256(b"").hexdigest(),
                    )
                )
                continue
            self._charge_manifest_leaf(entry_count, pending_directories)
            child_type, child_content = self._read_object(
                child_id,
                require_fresh=require_fresh,
            )
            if child_type != "blob":
                self._source_error()
            entries.append(
                CheckoutManifestEntry(
                    relative_path=relative_path,
                    entry_type="symlink" if mode == 0o120000 else "regular",
                    mode=mode,
                    size=len(child_content),
                    sha256=hashlib.sha256(child_content).hexdigest(),
                )
            )
        active.remove(object_id)
        return entries

    def _charge_manifest_leaf(
        self,
        entry_count: list[int],
        pending_directories: tuple[_PendingManifestDirectory, ...],
    ) -> None:
        uncharged_directories = tuple(
            directory for directory in pending_directories if not directory.charged
        )
        new_count = entry_count[0] + len(uncharged_directories) + 1
        if new_count > self._limits.max_tree_entries:
            self._budget_error()
        entry_count[0] = new_count
        for directory in uncharged_directories:
            directory.charged = True

    def _record(self, object_id: str, object_type: str, content: bytes) -> None:
        existing = self._records.get(object_id)
        record = ObjectRecord(object_type=object_type, size=len(content))
        if existing is not None:
            if existing != record:
                self._source_error()
            return
        if object_type not in {"commit", "tree", "blob"}:
            self._source_error()
        self._records[object_id] = record
        self._decompressed_bytes += len(content)
        if (
            len(self._records) > self._limits.max_objects
            or self._decompressed_bytes > self._limits.max_bytes
        ):
            self._budget_error()

    def _parse_commit(self, content: bytes) -> tuple[str, list[str]]:
        headers, separator, _message = content.partition(b"\n\n")
        if not separator or b"\0" in headers:
            self._source_error()
        tree_id: str | None = None
        parents: list[str] = []
        for line in headers.splitlines():
            if line.startswith(b"tree "):
                if tree_id is not None:
                    self._source_error()
                tree_id = self._decode_object_id(line[5:])
            elif line.startswith(b"parent "):
                parent = self._decode_object_id(line[7:])
                if parent in parents:
                    self._source_error()
                parents.append(parent)
        if tree_id is None:
            self._source_error()
        return tree_id, parents

    def _parse_tree(self, content: bytes) -> list[tuple[str, int, bytes, str]]:
        entries: list[tuple[str, int, bytes, str]] = []
        names: set[bytes] = set()
        position = 0
        while position < len(content):
            separator = content.find(b" ", position)
            terminator = content.find(b"\0", separator + 1)
            if separator <= position or terminator < 0:
                self._source_error()
            mode_bytes = content[position:separator]
            name = content[separator + 1 : terminator]
            object_start = terminator + 1
            object_end = object_start + self._hash_bytes
            if (
                not name
                or name in {b".", b".."}
                or b"/" in name
                or name.lower() == b".git"
                or object_end > len(content)
                or name in names
            ):
                self._source_error()
            names.add(name)
            if mode_bytes == b"40000":
                entry_type = "tree"
            elif mode_bytes == b"160000":
                entry_type = "gitlink"
            else:
                entry_type = _TREE_MODES.get(mode_bytes, "")
            if not entry_type:
                self._source_error()
            entries.append(
                (
                    entry_type,
                    int(mode_bytes, 8),
                    name,
                    content[object_start:object_end].hex(),
                )
            )
            position = object_end
        return entries

    def _reference(self, count: int) -> None:
        self._references += count
        if self._references > self._limits.max_references:
            self._budget_error()

    def _validate_destination(
        self,
        destination: Path,
        closure: dict[str, ObjectRecord],
        *,
        require_complete: bool = False,
    ) -> None:
        self._require_destination_directory(destination)
        found: set[str] = set()
        file_count = 0
        storage_bytes = 0
        try:
            with os.scandir(destination) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    if entry.name in {"info", "pack"}:
                        self._require_empty_destination_directory(path)
                        continue
                    if len(entry.name) != 2 or any(
                        character not in _HEX for character in entry.name
                    ):
                        self._destination_error()
                    self._require_destination_directory(path)
                    with os.scandir(path) as object_files:
                        for object_file in object_files:
                            file_count += 1
                            if file_count > self._limits.max_objects:
                                self._budget_error()
                            object_id = entry.name + object_file.name
                            self._require_object_id(object_id, destination=True)
                            object_path = Path(object_file.path)
                            payload = self._read_stable_file(
                                object_path,
                                self._limits.max_single_object_bytes + 1024 * 1024,
                                FailureCode.WORKSPACE_STATE_INVALID,
                                require_single_link=True,
                            )
                            storage_bytes += len(payload)
                            if storage_bytes > self._limits.max_bytes:
                                self._budget_error()
                            object_type, content = self._parse_loose_object(
                                payload,
                                object_id,
                                FailureCode.WORKSPACE_STATE_INVALID,
                            )
                            expected = closure.get(object_id)
                            if (
                                expected is None
                                or expected.object_type != object_type
                                or expected.size != len(content)
                                or object_id in found
                            ):
                                self._destination_error()
                            found.add(object_id)
        except OSError as exc:
            raise SourceObjectError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        if storage_bytes > self._limits.max_bytes or (require_complete and found != set(closure)):
            if require_complete and found != set(closure):
                self._destination_error()
            self._budget_error()

    def _destination_storage_bytes(self, destination: Path) -> int:
        total = 0
        for directory in os.scandir(destination):
            if len(directory.name) != 2:
                continue
            for object_file in os.scandir(directory.path):
                total += object_file.stat(follow_symlinks=False).st_size
        return total

    def _parse_loose_object(
        self,
        payload: bytes,
        expected_object_id: str,
        failure: FailureCode,
    ) -> tuple[str, bytes]:
        decompressor = zlib.decompressobj()
        try:
            raw = decompressor.decompress(
                payload,
                self._limits.max_single_object_bytes + 129,
            )
        except zlib.error as exc:
            raise SourceObjectError(failure) from exc
        if len(raw) > self._limits.max_single_object_bytes + 128:
            self._budget_error()
        if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
            raise SourceObjectError(failure)
        header, separator, content = raw.partition(b"\0")
        type_bytes, space, size_bytes = header.partition(b" ")
        if (
            not separator
            or not space
            or type_bytes not in {b"commit", b"tree", b"blob", b"tag"}
            or not size_bytes
            or not size_bytes.isdigit()
            or (len(size_bytes) > 1 and size_bytes.startswith(b"0"))
        ):
            raise SourceObjectError(failure)
        declared_size = int(size_bytes)
        if declared_size != len(content):
            raise SourceObjectError(failure)
        if declared_size > self._limits.max_single_object_bytes:
            self._budget_error()
        object_type = type_bytes.decode("ascii")
        if _object_id(self._hash_name, object_type, content) != expected_object_id:
            raise SourceObjectError(failure)
        return object_type, content

    def _write_new_object(self, destination: Path, payload: bytes) -> None:
        temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"
        descriptor: int | None = None
        temporary_exists = False
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            temporary_exists = True
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    self._destination_error()
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            try:
                os.link(temporary, destination, follow_symlinks=False)
            except FileExistsError:
                self._destination_error()
            os.unlink(temporary)
            temporary_exists = False
            directory_descriptor = os.open(
                destination.parent,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError as exc:
            raise SourceObjectError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_exists:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass

    def _read_stable_file(
        self,
        path: Path,
        max_bytes: int,
        failure: FailureCode,
        *,
        expected: _FileSnapshot | None = None,
        require_single_link: bool = False,
    ) -> bytes:
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise SourceObjectError(failure) from exc
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or (require_single_link and before.st_nlink != 1)
                or before.st_size > max_bytes
                or (expected is not None and not expected.matches(before))
            ):
                raise SourceObjectError(failure)
            payload = bytearray()
            while len(payload) < before.st_size:
                chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(payload)))
                if not chunk:
                    raise SourceObjectError(failure)
                payload.extend(chunk)
            after = os.fstat(descriptor)
            if not _FileSnapshot.from_stat(before).matches(after):
                raise SourceObjectError(failure)
            return bytes(payload)
        finally:
            os.close(descriptor)

    def _snapshot_source_file(self, path: Path) -> _FileSnapshot:
        metadata = self._require_source_file(path)
        return _FileSnapshot.from_stat(metadata)

    def _require_source_file(self, path: Path) -> os.stat_result:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_nlink != 1
        ):
            self._source_error()
        return metadata

    def _require_source_directory(self, path: Path) -> None:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            self._source_error()

    def _require_destination_directory(self, path: Path) -> None:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise SourceObjectError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            self._destination_error()

    def _require_empty_destination_directory(self, path: Path) -> None:
        self._require_destination_directory(path)
        try:
            with os.scandir(path) as iterator:
                if next(iterator, None) is not None:
                    self._destination_error()
        except OSError as exc:
            raise SourceObjectError(FailureCode.WORKSPACE_STATE_INVALID) from exc

    def _open_snapshot(self, path: Path, snapshot: _FileSnapshot) -> int:
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not snapshot.matches(metadata)
        ):
            os.close(descriptor)
            self._source_error()
        return descriptor

    def _require_snapshot(
        self,
        path: Path,
        snapshot: _FileSnapshot,
        failure: FailureCode,
    ) -> None:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise SourceObjectError(failure) from exc
        if not snapshot.matches(metadata):
            raise SourceObjectError(failure)

    def _require_descriptor_snapshot(self, descriptor: int, snapshot: _FileSnapshot) -> None:
        if not snapshot.matches(os.fstat(descriptor)):
            self._source_error()

    def _read_pack_byte(self, descriptor: int, position: int, pack: _PackIndex) -> int:
        if position >= pack.pack_snapshot.size - self._hash_bytes:
            self._source_error()
        payload = os.pread(descriptor, 1, position)
        if len(payload) != 1:
            self._source_error()
        return payload[0]

    @staticmethod
    def _crc_range(descriptor: int, start: int, end: int) -> int:
        crc = 0
        position = start
        while position < end:
            chunk = os.pread(descriptor, min(64 * 1024, end - position), position)
            if not chunk:
                raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE)
            crc = zlib.crc32(chunk, crc)
            position += len(chunk)
        return crc & 0xFFFFFFFF

    def _decode_object_id(self, value: bytes) -> str:
        try:
            object_id = value.decode("ascii")
        except UnicodeDecodeError as exc:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        self._require_object_id(object_id)
        return object_id

    def _require_object_id(self, value: str, *, destination: bool = False) -> None:
        if len(value) != self._hex_length or any(character not in _HEX for character in value):
            if destination:
                self._destination_error()
            self._source_error()

    @staticmethod
    def _source_error() -> NoReturn:
        raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE)

    @staticmethod
    def _destination_error() -> NoReturn:
        raise SourceObjectError(FailureCode.WORKSPACE_STATE_INVALID)

    @staticmethod
    def _budget_error() -> NoReturn:
        raise SourceObjectError(FailureCode.MIRROR_BUDGET_EXCEEDED)


def _canonical_object(object_type: str, content: bytes) -> bytes:
    return f"{object_type} {len(content)}".encode("ascii") + b"\0" + content


def _object_id(hash_name: str, object_type: str, content: bytes) -> str:
    return hashlib.new(hash_name, _canonical_object(object_type, content)).hexdigest()


def _read_delta_varint(payload: bytes, position: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if position >= len(payload) or shift > 63:
            raise SourceObjectError(FailureCode.REPOSITORY_UNAVAILABLE)
        current = payload[position]
        position += 1
        value |= (current & 0x7F) << shift
        if not current & 0x80:
            return value, position
        shift += 7
