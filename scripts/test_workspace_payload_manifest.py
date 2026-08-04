import io
import os
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

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

    def test_top_level_git_file_and_symlink_are_excluded(self) -> None:
        for kind in ("file", "symlink"):
            with self.subTest(kind=kind):
                root = self.base / f"nongit-{kind}"
                root.mkdir()
                (root / "payload").write_text("payload", encoding="utf-8")
                dot_git = root / ".git"
                if kind == "file":
                    dot_git.write_text("gitdir: elsewhere\n", encoding="utf-8")
                else:
                    dot_git.symlink_to("elsewhere")
                before_path = self.manifests / f"nongit-{kind}-before.json"
                manifest.write_manifest(root, before_path)
                before = manifest.manifest_digest(before_path)
                dot_git.unlink()
                if kind == "file":
                    dot_git.write_text("gitdir: changed\n", encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
