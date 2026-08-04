import hashlib
import io
import json
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import workspace_payload_manifest as manifest


class WorkspacePayloadManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="workspace-payload-manifest-test-")
        self.base = Path(self.temporary.name)
        self.root = self.base / "workspace"
        self.manifests = self.base / "manifests"
        self.root.mkdir()
        self.manifests.mkdir()
        self._git("init", "--quiet")
        self._git("config", "user.name", "Manifest Test")
        self._git("config", "user.email", "manifest@example.invalid")
        (self.root / ".gitignore").write_text("ignored.log\n", encoding="utf-8")
        (self.root / "tracked.txt").write_text("tracked payload\n", encoding="utf-8")
        (self.root / "executable.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(self.root / "executable.sh", 0o644)
        self._git("add", ".gitignore", "tracked.txt", "executable.sh")
        self._git("commit", "--quiet", "-m", "fixture")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def _write(self, name: str) -> Path:
        path = self.manifests / f"{name}.json"
        manifest.write_manifest(self.root, path)
        return path

    def _digest(self, name: str) -> tuple[Path, str]:
        path = self._write(name)
        return path, manifest.manifest_digest(path)

    def _plain_root(self, name: str) -> Path:
        root = self.base / name
        root.mkdir()
        return root

    def _start_mutation(
        self,
        trigger: threading.Event,
        done: threading.Event,
        action: object,
    ) -> tuple[threading.Thread, list[BaseException]]:
        errors: list[BaseException] = []

        def worker() -> None:
            if not trigger.wait(5):
                errors.append(AssertionError("mutation trigger was not reached"))
                done.set()
                return
            try:
                assert callable(action)
                action()
            except BaseException as error:
                errors.append(error)
            finally:
                done.set()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread, errors

    def _finish_mutation(
        self,
        thread: threading.Thread,
        errors: list[BaseException],
    ) -> None:
        thread.join(5)
        self.assertFalse(thread.is_alive(), "mutation thread did not finish")
        if errors:
            raise errors[0]

    def test_identical_payload_and_git_metadata_are_deterministic(self) -> None:
        first_path, first = self._digest("same-first")
        _, second = self._digest("same-second")
        self.assertEqual(first, second)

        (self.root / ".git" / "manifest-test-metadata").write_bytes(b"transaction metadata")
        index = self.root / ".git" / "index"
        index_stat = index.stat()
        os.utime(index, ns=(index_stat.st_atime_ns, index_stat.st_mtime_ns + 1_000_000))
        _, git_changed = self._digest("git-changed")
        self.assertEqual(first, git_changed)

        document = manifest.load_manifest(first_path)
        self.assertNotIn(".git", {entry["path"].split("/", 1)[0] for entry in document["entries"]})

    def test_ignored_and_untracked_files_are_included(self) -> None:
        before_path, before = self._digest("artifacts-before")
        (self.root / "ignored.log").write_text("ignored runtime artifact\n", encoding="utf-8")
        ignored_path, ignored = self._digest("ignored-after")
        self.assertNotEqual(before, ignored)
        added, removed, changed = manifest.manifest_differences(
            manifest.load_manifest(before_path), manifest.load_manifest(ignored_path)
        )
        self.assertEqual([entry["path"] for entry in added], ["ignored.log"])
        self.assertEqual((removed, changed), ([], []))

        (self.root / "untracked.txt").write_text("untracked runtime artifact\n", encoding="utf-8")
        _, untracked = self._digest("untracked-after")
        self.assertNotEqual(ignored, untracked)

    def test_tracked_content_and_git_status_both_change(self) -> None:
        before_path, before = self._digest("tracked-before")
        (self.root / "tracked.txt").write_text("changed tracked payload\n", encoding="utf-8")
        after_path, after = self._digest("tracked-after")
        self.assertNotEqual(before, after)
        self.assertTrue(self._git("status", "--porcelain=v1", "-uall").stdout)
        _, _, changed = manifest.manifest_differences(
            manifest.load_manifest(before_path), manifest.load_manifest(after_path)
        )
        self.assertEqual([old["path"] for old, _ in changed], ["tracked.txt"])

        output = io.StringIO()
        with redirect_stdout(output):
            mismatch = manifest.print_mismatch(before_path, after_path, "workspace-tree", self.root)
        diagnostic = output.getvalue()
        self.assertTrue(mismatch)
        self.assertIn('"check": "workspace-tree"', diagnostic)
        self.assertIn('"path": "tracked.txt"', diagnostic)
        self.assertNotIn("changed tracked payload", diagnostic)

    def test_executable_bit_changes_digest(self) -> None:
        before_path, before = self._digest("mode-before")
        executable = self.root / "executable.sh"
        os.chmod(executable, stat.S_IMODE(executable.stat().st_mode) | stat.S_IXUSR)
        after_path, after = self._digest("mode-after")
        self.assertNotEqual(before, after)
        _, _, changed = manifest.manifest_differences(
            manifest.load_manifest(before_path), manifest.load_manifest(after_path)
        )
        self.assertEqual([old["path"] for old, _ in changed], ["executable.sh"])
        self.assertNotEqual(changed[0][0]["mode"], changed[0][1]["mode"])

    def test_symlink_target_changes_digest(self) -> None:
        link = self.root / "payload-link"
        link.symlink_to("first-target")
        before_path, before = self._digest("symlink-before")
        link.unlink()
        link.symlink_to("second-target")
        after_path, after = self._digest("symlink-after")
        self.assertNotEqual(before, after)
        _, _, changed = manifest.manifest_differences(
            manifest.load_manifest(before_path), manifest.load_manifest(after_path)
        )
        self.assertEqual(changed[0][0]["symlink_target"], "first-target")
        self.assertEqual(changed[0][1]["symlink_target"], "second-target")

    def test_empty_directory_creation_and_removal_change_digest(self) -> None:
        before_path, before = self._digest("directory-before")
        empty = self.root / "empty-runtime-directory"
        empty.mkdir()
        created_path, created = self._digest("directory-created")
        self.assertNotEqual(before, created)
        added, _, _ = manifest.manifest_differences(
            manifest.load_manifest(before_path), manifest.load_manifest(created_path)
        )
        self.assertEqual([entry["path"] for entry in added], ["empty-runtime-directory"])
        empty.rmdir()
        removed_path, removed = self._digest("directory-removed")
        self.assertEqual(before, removed)
        _, removed_entries, _ = manifest.manifest_differences(
            manifest.load_manifest(created_path), manifest.load_manifest(removed_path)
        )
        self.assertEqual([entry["path"] for entry in removed_entries], ["empty-runtime-directory"])

    def test_manifest_excludes_absolute_root_and_mtime(self) -> None:
        path, before = self._digest("metadata-before")
        payload = path.read_bytes()
        self.assertNotIn(os.fsencode(str(self.root)), payload)
        self.assertNotIn(b"mtime", payload)

        tracked = self.root / "tracked.txt"
        metadata = tracked.stat()
        os.utime(tracked, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 5_000_000_000))
        _, after = self._digest("metadata-after")
        self.assertEqual(before, after)
        with self.assertRaisesRegex(ValueError, "outside the workspace root"):
            manifest.write_manifest(self.root, self.root / "forbidden-manifest.json")

    def test_paths_with_line_breaks_are_unambiguous_and_byte_sorted(self) -> None:
        (self.root / "line\nbreak\tname").write_text("payload", encoding="utf-8")
        path = self._write("control-character-path")
        document = manifest.load_manifest(path)
        paths = [entry["path"] for entry in document["entries"]]
        self.assertIn("line\nbreak\tname", paths)
        self.assertEqual(paths, sorted(paths, key=os.fsencode))

    def test_top_level_git_file_directory_and_symlink_are_excluded(self) -> None:
        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind):
                root = self.base / f"nongit-{kind}"
                root.mkdir()
                (root / "payload").write_text("payload", encoding="utf-8")
                dot_git = root / ".git"
                if kind == "file":
                    dot_git.write_text("gitdir: elsewhere\n", encoding="utf-8")
                elif kind == "directory":
                    dot_git.mkdir()
                    (dot_git / "metadata").write_text("first", encoding="utf-8")
                else:
                    dot_git.symlink_to("elsewhere")
                before_path = self.manifests / f"nongit-{kind}-before.json"
                manifest.write_manifest(root, before_path)
                before = manifest.manifest_digest(before_path)
                if kind == "directory":
                    shutil.rmtree(dot_git)
                else:
                    dot_git.unlink()
                if kind == "file":
                    dot_git.write_text("gitdir: changed\n", encoding="utf-8")
                elif kind == "directory":
                    dot_git.mkdir()
                    (dot_git / "metadata").write_text("second", encoding="utf-8")
                else:
                    dot_git.symlink_to("changed")
                after_path = self.manifests / f"nongit-{kind}-after.json"
                manifest.write_manifest(root, after_path)
                self.assertEqual(before, manifest.manifest_digest(after_path))

    def test_nested_git_named_paths_are_included(self) -> None:
        nested = self.root / "nested" / ".git"
        nested.mkdir(parents=True)
        (nested / "payload").write_text("nested payload\n", encoding="utf-8")
        path = self._write("nested-git")
        entries = {entry["path"] for entry in manifest.load_manifest(path)["entries"]}
        self.assertIn("nested/.git", entries)
        self.assertIn("nested/.git/payload", entries)

    def test_fifo_is_rejected_with_safe_typed_error(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("os.mkfifo is unavailable")
        nested = self.root / "nested-special"
        nested.mkdir()
        fifo = nested / "payload.pipe"
        os.mkfifo(fifo)

        with self.assertRaises(manifest.UnsupportedWorkspaceEntryError) as raised:
            manifest.build_manifest(self.root)
        message = str(raised.exception)
        self.assertIn("nested-special/payload.pipe", message)
        self.assertIn("type=fifo", message)
        self.assertNotIn(str(self.root), message)
        self.assertNotIn(str(self.base), message)

    def test_unix_socket_is_rejected_with_safe_typed_error(self) -> None:
        if not hasattr(socket, "AF_UNIX"):
            self.skipTest("Unix domain sockets are unavailable")
        with tempfile.TemporaryDirectory(prefix="ve-socket-", dir="/tmp") as short_temporary:
            root = Path(short_temporary) / "workspace"
            root.mkdir()
            (root / "payload.txt").write_text("payload", encoding="utf-8")
            socket_path = root / "payload.sock"
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                try:
                    listener.bind(str(socket_path))
                except OSError as error:
                    self.skipTest(f"Unix domain socket bind is unavailable: {error.errno}")
                with self.assertRaises(manifest.UnsupportedWorkspaceEntryError) as raised:
                    manifest.build_manifest(root)
                message = str(raised.exception)
                self.assertIn("payload.sock", message)
                self.assertIn("type=socket", message)
                self.assertNotIn(str(root), message)
                self.assertNotIn(short_temporary, message)
            finally:
                listener.close()

    def test_nested_git_special_type_is_not_excluded(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("os.mkfifo is unavailable")
        nested = self.root / "nested-special-git"
        nested.mkdir()
        os.mkfifo(nested / ".git")
        with self.assertRaises(manifest.UnsupportedWorkspaceEntryError) as raised:
            manifest.build_manifest(self.root)
        self.assertIn("nested-special-git/.git", str(raised.exception))

    def test_regular_file_replaced_between_lstat_and_open_fails_closed(self) -> None:
        root = self._plain_root("pre-open-race")
        victim = root / "race.txt"
        victim.write_text("original", encoding="utf-8")
        replacement = self.base / "pre-open-replacement"
        replacement.write_text("replacement", encoding="utf-8")
        trigger = threading.Event()
        done = threading.Event()
        thread, errors = self._start_mutation(
            trigger, done, lambda: os.replace(replacement, victim)
        )
        real_open = manifest.os.open
        opened = False

        def racing_open(
            path: object,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal opened
            if path == b"race.txt" and dir_fd is not None and not opened:
                opened = True
                trigger.set()
                self.assertTrue(done.wait(5), "replacement did not complete")
            return real_open(path, flags, mode, dir_fd=dir_fd)

        try:
            with mock.patch.object(manifest.os, "open", side_effect=racing_open):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError) as raised:
                    manifest.build_manifest(root)
            self.assertIn("race.txt", str(raised.exception))
            self.assertNotIn(str(root), str(raised.exception))
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_regular_file_modified_during_descriptor_read_fails_closed(self) -> None:
        root = self._plain_root("read-race")
        victim = root / "race.txt"
        victim.write_text("original", encoding="utf-8")
        trigger = threading.Event()
        done = threading.Event()
        thread, errors = self._start_mutation(
            trigger, done, lambda: victim.write_text("modified", encoding="utf-8")
        )
        real_read = manifest.os.read
        read_started = False

        def racing_read(descriptor: int, length: int) -> bytes:
            nonlocal read_started
            if not read_started:
                read_started = True
                trigger.set()
                self.assertTrue(done.wait(5), "in-place modification did not complete")
            return real_read(descriptor, length)

        try:
            with mock.patch.object(manifest.os, "read", side_effect=racing_read):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError) as raised:
                    manifest.build_manifest(root)
            self.assertIn("race.txt", str(raised.exception))
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_entry_added_after_initial_directory_snapshot_fails_closed(self) -> None:
        root = self._plain_root("directory-add-race")
        (root / "present.txt").write_text("present", encoding="utf-8")
        trigger = threading.Event()
        done = threading.Event()
        thread, errors = self._start_mutation(
            trigger,
            done,
            lambda: (root / "added.txt").write_text("added", encoding="utf-8"),
        )
        real_names = manifest._directory_entry_names
        scanned = False

        def racing_names(
            descriptor: int, relative_path: str, exclude_git: bool
        ) -> tuple[bytes, ...]:
            nonlocal scanned
            names = real_names(descriptor, relative_path, exclude_git)
            if relative_path == "." and not scanned:
                scanned = True
                trigger.set()
                self.assertTrue(done.wait(5), "entry addition did not complete")
            return names

        try:
            with mock.patch.object(manifest, "_directory_entry_names", side_effect=racing_names):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError):
                    manifest.build_manifest(root)
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_entry_deleted_after_initial_directory_snapshot_fails_closed(self) -> None:
        root = self._plain_root("directory-delete-race")
        victim = root / "removed.txt"
        victim.write_text("present", encoding="utf-8")
        trigger = threading.Event()
        done = threading.Event()
        thread, errors = self._start_mutation(trigger, done, victim.unlink)
        real_names = manifest._directory_entry_names
        scanned = False

        def racing_names(
            descriptor: int, relative_path: str, exclude_git: bool
        ) -> tuple[bytes, ...]:
            nonlocal scanned
            names = real_names(descriptor, relative_path, exclude_git)
            if relative_path == "." and not scanned:
                scanned = True
                trigger.set()
                self.assertTrue(done.wait(5), "entry deletion did not complete")
            return names

        try:
            with mock.patch.object(manifest, "_directory_entry_names", side_effect=racing_names):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError):
                    manifest.build_manifest(root)
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_entry_replaced_after_initial_directory_snapshot_fails_closed(self) -> None:
        root = self._plain_root("directory-replace-race")
        victim = root / "replaced.txt"
        victim.write_text("original", encoding="utf-8")
        replacement = self.base / "directory-entry-replacement"
        replacement.write_text("replacement", encoding="utf-8")
        trigger = threading.Event()
        done = threading.Event()
        thread, errors = self._start_mutation(
            trigger, done, lambda: os.replace(replacement, victim)
        )
        real_names = manifest._directory_entry_names
        scanned = False

        def racing_names(
            descriptor: int, relative_path: str, exclude_git: bool
        ) -> tuple[bytes, ...]:
            nonlocal scanned
            names = real_names(descriptor, relative_path, exclude_git)
            if relative_path == "." and not scanned:
                scanned = True
                trigger.set()
                self.assertTrue(done.wait(5), "entry replacement did not complete")
            return names

        try:
            with mock.patch.object(manifest, "_directory_entry_names", side_effect=racing_names):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError):
                    manifest.build_manifest(root)
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_symlink_changed_during_readlink_fails_closed(self) -> None:
        root = self._plain_root("symlink-race")
        link = root / "race-link"
        link.symlink_to("first-target")
        trigger = threading.Event()
        done = threading.Event()

        def replace_link() -> None:
            link.unlink()
            link.symlink_to("second-target")

        thread, errors = self._start_mutation(trigger, done, replace_link)
        real_readlink = manifest.os.readlink
        read_started = False

        def racing_readlink(path: object, *, dir_fd: int | None = None) -> object:
            nonlocal read_started
            if path == b"race-link" and dir_fd is not None and not read_started:
                read_started = True
                trigger.set()
                self.assertTrue(done.wait(5), "symlink replacement did not complete")
            return real_readlink(path, dir_fd=dir_fd)

        try:
            with mock.patch.object(manifest.os, "readlink", side_effect=racing_readlink):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError) as raised:
                    manifest.build_manifest(root)
            self.assertIn("race-link", str(raised.exception))
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_processed_file_changed_before_manifest_completion_fails_closed(self) -> None:
        root = self._plain_root("global-snapshot-race")
        processed = root / "a-processed.txt"
        processed.write_text("first", encoding="utf-8")
        (root / "z-blocker.txt").write_text("blocker", encoding="utf-8")
        trigger = threading.Event()
        done = threading.Event()
        thread, errors = self._start_mutation(
            trigger, done, lambda: processed.write_text("other", encoding="utf-8")
        )
        real_open = manifest.os.open
        blocked = False

        def racing_open(
            path: object,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal blocked
            if path == b"z-blocker.txt" and dir_fd is not None and not blocked:
                blocked = True
                trigger.set()
                self.assertTrue(done.wait(5), "late file modification did not complete")
            return real_open(path, flags, mode, dir_fd=dir_fd)

        try:
            with mock.patch.object(manifest.os, "open", side_effect=racing_open):
                with self.assertRaises(manifest.WorkspaceSnapshotChangedError) as raised:
                    manifest.build_manifest(root)
            self.assertIn("global-snapshot-compare", str(raised.exception))
        finally:
            trigger.set()
            self._finish_mutation(thread, errors)

    def test_creation_order_does_not_change_canonical_manifest_or_digest(self) -> None:
        first_root = self._plain_root("creation-order-first")
        second_root = self._plain_root("creation-order-second")

        def populate(root: Path, reverse: bool) -> None:
            directories = ["alpha", "beta", "empty"]
            files = [
                ("root.txt", b"root payload\n", 0o640),
                ("alpha/one.txt", b"one\n", 0o644),
                ("beta/two.sh", b"#!/bin/sh\nexit 0\n", 0o755),
            ]
            for name in reversed(directories) if reverse else directories:
                (root / name).mkdir()
                os.chmod(root / name, 0o755)
            for name, payload, mode in reversed(files) if reverse else files:
                path = root / name
                path.write_bytes(payload)
                os.chmod(path, mode)
            (root / "payload-link").symlink_to("alpha/one.txt")

        populate(first_root, False)
        populate(second_root, True)
        first_payload = manifest.canonical_manifest_bytes(manifest.build_manifest(first_root))
        second_payload = manifest.canonical_manifest_bytes(manifest.build_manifest(second_root))
        first_digest = hashlib.sha256(first_payload).hexdigest()
        second_digest = hashlib.sha256(second_payload).hexdigest()
        self.assertEqual(first_payload, second_payload)
        self.assertEqual(first_digest, second_digest)
        print(
            f"CREATION_ORDER_MANIFEST expected_digest={first_digest} actual_digest={second_digest}"
        )
        self.assertNotIn(os.fsencode(str(first_root)), first_payload)
        self.assertNotIn(os.fsencode(str(second_root)), second_payload)
        self.assertNotIn(b"mtime", first_payload)
        self.assertNotIn(b"ctime", first_payload)

    def test_mismatch_diagnostics_are_capped_and_redact_symlink_targets(self) -> None:
        expected = {"schema": manifest.SCHEMA, "entries": []}
        secret_target = "/sensitive/credential-location/token-value"
        actual_entries = [
            {
                "type": "symlink",
                "mode": "0777",
                "path": f"link-{index:02d}",
                "size": len(os.fsencode(secret_target)),
                "symlink_target": secret_target,
            }
            for index in range(manifest.DIAGNOSTIC_ENTRY_LIMIT + 5)
        ]
        actual = {"schema": manifest.SCHEMA, "entries": actual_entries}
        expected_path = self.manifests / "diagnostic-expected.json"
        actual_path = self.manifests / "diagnostic-actual.json"
        expected_path.write_bytes(manifest.canonical_manifest_bytes(expected))
        actual_path.write_bytes(manifest.canonical_manifest_bytes(actual))

        output = io.StringIO()
        with redirect_stdout(output):
            mismatch = manifest.print_mismatch(
                expected_path, actual_path, "diagnostic-redaction", self.root
            )
        diagnostic = output.getvalue()
        summary = json.loads(diagnostic.splitlines()[0].split(" ", 1)[1])
        self.assertTrue(mismatch)
        self.assertEqual(summary["diagnostic_total_count"], manifest.DIAGNOSTIC_ENTRY_LIMIT + 5)
        self.assertEqual(summary["diagnostic_omitted_count"], 5)
        self.assertEqual(
            diagnostic.count("E2E_WORKSPACE_MANIFEST_ADDED "),
            manifest.DIAGNOSTIC_ENTRY_LIMIT,
        )
        self.assertNotIn(secret_target, diagnostic)
        self.assertNotIn("token-value", diagnostic)
        self.assertNotIn("synthetic file body", diagnostic)
        self.assertIn("symlink_target_sha256", diagnostic)
        self.assertNotIn('"symlink_target":', diagnostic)


if __name__ == "__main__":
    unittest.main()
