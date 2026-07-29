from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import platform
import resource
import socket
import stat
import sys
from pathlib import Path

_EXPECTED_FIXTURE = b"Original fixture text.\n"
_EXPECTED_FIXTURE_SHA256 = hashlib.sha256(_EXPECTED_FIXTURE).hexdigest()
_LANDLOCK_CREATE_RULESET = 444
_LANDLOCK_ADD_RULE = 445
_LANDLOCK_RESTRICT_SELF = 446
_LANDLOCK_CREATE_RULESET_VERSION = 1
_LANDLOCK_RULE_PATH_BENEATH = 1

_ACCESS_FS_EXECUTE = 1 << 0
_ACCESS_FS_WRITE_FILE = 1 << 1
_ACCESS_FS_READ_FILE = 1 << 2
_ACCESS_FS_READ_DIR = 1 << 3
_ACCESS_FS_REMOVE_DIR = 1 << 4
_ACCESS_FS_REMOVE_FILE = 1 << 5
_ACCESS_FS_MAKE_CHAR = 1 << 6
_ACCESS_FS_MAKE_DIR = 1 << 7
_ACCESS_FS_MAKE_REG = 1 << 8
_ACCESS_FS_MAKE_SOCK = 1 << 9
_ACCESS_FS_MAKE_FIFO = 1 << 10
_ACCESS_FS_MAKE_BLOCK = 1 << 11
_ACCESS_FS_MAKE_SYM = 1 << 12
_ACCESS_FS_REFER = 1 << 13
_ACCESS_FS_TRUNCATE = 1 << 14

_READ_ACCESS = _ACCESS_FS_READ_FILE | _ACCESS_FS_READ_DIR
_WRITE_ACCESS = (
    _ACCESS_FS_WRITE_FILE
    | _ACCESS_FS_REMOVE_DIR
    | _ACCESS_FS_REMOVE_FILE
    | _ACCESS_FS_MAKE_CHAR
    | _ACCESS_FS_MAKE_DIR
    | _ACCESS_FS_MAKE_REG
    | _ACCESS_FS_MAKE_SOCK
    | _ACCESS_FS_MAKE_FIFO
    | _ACCESS_FS_MAKE_BLOCK
    | _ACCESS_FS_MAKE_SYM
    | _ACCESS_FS_REFER
    | _ACCESS_FS_TRUNCATE
)

_PR_SET_NO_NEW_PRIVS = 38
_PR_SET_SECCOMP = 22
_SECCOMP_MODE_FILTER = 2
_SECCOMP_RET_KILL_PROCESS = 0x80000000
_SECCOMP_RET_ERRNO = 0x00050000
_SECCOMP_RET_ALLOW = 0x7FFF0000
_BPF_LD_W_ABS = 0x20
_BPF_JMP_JEQ_K = 0x15
_BPF_RET_K = 0x06


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
        ("reserved", ctypes.c_uint32),
    ]


class _SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint32),
    ]


class _SockFprog(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("filters", ctypes.POINTER(_SockFilter)),
    ]


def _syscall(
    libc: ctypes.CDLL,
    number: int,
    *arguments: object,
) -> int:
    result = int(libc.syscall(number, *arguments))
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def _apply_limits(
    *,
    cpu_seconds: int,
    memory_bytes: int,
    pid_limit: int,
    fd_limit: int,
    output_bytes: int,
    artifact_bytes: int,
) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_NPROC, (pid_limit, pid_limit))
    resource.setrlimit(resource.RLIMIT_NOFILE, (fd_limit, fd_limit))
    resource.setrlimit(resource.RLIMIT_FSIZE, (artifact_bytes, artifact_bytes))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if hasattr(resource, "RLIMIT_DATA"):
        resource.setrlimit(resource.RLIMIT_DATA, (memory_bytes, memory_bytes))
    if output_bytes <= 0:
        raise ValueError("output budget must be positive")


def _landlock_access_for_abi(abi: int) -> int:
    access = (
        _ACCESS_FS_EXECUTE
        | _ACCESS_FS_WRITE_FILE
        | _ACCESS_FS_READ_FILE
        | _ACCESS_FS_READ_DIR
        | _ACCESS_FS_REMOVE_DIR
        | _ACCESS_FS_REMOVE_FILE
        | _ACCESS_FS_MAKE_CHAR
        | _ACCESS_FS_MAKE_DIR
        | _ACCESS_FS_MAKE_REG
        | _ACCESS_FS_MAKE_SOCK
        | _ACCESS_FS_MAKE_FIFO
        | _ACCESS_FS_MAKE_BLOCK
        | _ACCESS_FS_MAKE_SYM
    )
    if abi >= 2:
        access |= _ACCESS_FS_REFER
    if abi >= 3:
        access |= _ACCESS_FS_TRUNCATE
    return access


def _install_landlock(
    input_root: Path,
    writable_roots: tuple[Path, ...],
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    abi = _syscall(
        libc,
        _LANDLOCK_CREATE_RULESET,
        ctypes.c_void_p(),
        ctypes.c_size_t(0),
        ctypes.c_uint(_LANDLOCK_CREATE_RULESET_VERSION),
    )
    if abi < 1:
        raise OSError(errno.ENOSYS, "Landlock ABI is unavailable")
    handled = _landlock_access_for_abi(abi)
    ruleset_attr = _RulesetAttr(handled_access_fs=handled)
    ruleset_fd = _syscall(
        libc,
        _LANDLOCK_CREATE_RULESET,
        ctypes.byref(ruleset_attr),
        ctypes.sizeof(ruleset_attr),
        ctypes.c_uint(0),
    )
    opened: list[int] = []
    try:
        for path, access in (
            (input_root, _READ_ACCESS),
            *((path, _READ_ACCESS | _WRITE_ACCESS) for path in writable_roots),
        ):
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
            opened.append(descriptor)
            rule = _PathBeneathAttr(
                allowed_access=access & handled,
                parent_fd=descriptor,
                reserved=0,
            )
            _syscall(
                libc,
                _LANDLOCK_ADD_RULE,
                ruleset_fd,
                _LANDLOCK_RULE_PATH_BENEATH,
                ctypes.byref(rule),
                ctypes.c_uint(0),
            )
        if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        _syscall(
            libc,
            _LANDLOCK_RESTRICT_SELF,
            ruleset_fd,
            ctypes.c_uint(0),
        )
    finally:
        for descriptor in opened:
            os.close(descriptor)
        os.close(ruleset_fd)


def _network_syscalls() -> tuple[int, set[int]]:
    machine = platform.machine().casefold()
    if machine in {"x86_64", "amd64"}:
        return (
            0xC000003E,
            {
                41,
                42,
                43,
                44,
                45,
                46,
                47,
                48,
                49,
                50,
                51,
                52,
                53,
                54,
                55,
                288,
                299,
                307,
                425,
            },
        )
    if machine in {"aarch64", "arm64"}:
        return (
            0xC00000B7,
            {
                198,
                199,
                200,
                201,
                202,
                203,
                204,
                205,
                206,
                207,
                208,
                209,
                210,
                211,
                212,
                242,
                243,
                269,
                425,
            },
        )
    raise OSError(errno.ENOTSUP, "unsupported seccomp architecture")


def _install_network_seccomp() -> None:
    audit_arch, blocked = _network_syscalls()
    instructions = [
        _SockFilter(_BPF_LD_W_ABS, 0, 0, 4),
        _SockFilter(_BPF_JMP_JEQ_K, 1, 0, audit_arch),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_KILL_PROCESS),
        _SockFilter(_BPF_LD_W_ABS, 0, 0, 0),
    ]
    for number in sorted(blocked):
        instructions.extend(
            (
                _SockFilter(_BPF_JMP_JEQ_K, 0, 1, number),
                _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
            )
        )
    instructions.append(_SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ALLOW))
    program_array = (_SockFilter * len(instructions))(*instructions)
    program = _SockFprog(
        length=len(instructions),
        filters=ctypes.cast(program_array, ctypes.POINTER(_SockFilter)),
    )
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    if libc.prctl(_PR_SET_SECCOMP, _SECCOMP_MODE_FILTER, ctypes.byref(program)) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _require_denied_boundaries(canonical_workspace: Path) -> None:
    try:
        descriptor = os.open(
            canonical_workspace,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except PermissionError:
        print("VE_VALIDATION_SANDBOX_FILESYSTEM_DENIED", flush=True)
    else:
        os.close(descriptor)
        raise RuntimeError("filesystem boundary was not enforced")

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        print("VE_VALIDATION_SANDBOX_NETWORK_DENIED", flush=True)
        return
    try:
        probe.connect(("127.0.0.1", 9))
    except PermissionError:
        print("VE_VALIDATION_SANDBOX_NETWORK_DENIED", flush=True)
    else:
        raise RuntimeError("network boundary was not enforced")
    finally:
        probe.close()


def _open_fixture(input_root: Path) -> tuple[int, int]:
    root_descriptor = os.open(
        input_root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
    )
    sandbox_descriptor: int | None = None
    try:
        sandbox_descriptor = os.open(
            "sandbox",
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=root_descriptor,
        )
        try:
            fixture_descriptor = os.open(
                "original.txt",
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=sandbox_descriptor,
            )
        except Exception:
            os.close(sandbox_descriptor)
            raise
    finally:
        os.close(root_descriptor)
    metadata = os.fstat(fixture_descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > 4096:
        os.close(fixture_descriptor)
        os.close(sandbox_descriptor)
        raise OSError(errno.EPERM, "validation input identity is invalid")
    return fixture_descriptor, sandbox_descriptor


def _run_profile(
    profile_id: str,
    fixture_descriptor: int,
    sandbox_descriptor: int,
) -> int:
    os.lseek(fixture_descriptor, 0, os.SEEK_SET)
    value = os.read(fixture_descriptor, 4097)
    if profile_id == "fixture-python-stdlib-v1":
        if value != _EXPECTED_FIXTURE:
            print("VE_VALIDATION_PROFILE_CONTRACT_MISMATCH", file=sys.stderr, flush=True)
            return 1
        print("VE_VALIDATION_PROFILE_PASS", flush=True)
        return 0
    if profile_id == "fixture-python-manifest-v1":
        entries = sorted(entry.name for entry in os.scandir(sandbox_descriptor))
        if entries != ["original.txt"] or hashlib.sha256(value).hexdigest() != (
            _EXPECTED_FIXTURE_SHA256
        ):
            print("VE_VALIDATION_PROFILE_MANIFEST_MISMATCH", file=sys.stderr, flush=True)
            return 1
        print("VE_VALIDATION_PROFILE_MANIFEST_PASS", flush=True)
        return 0
    else:
        print("VE_VALIDATION_PROFILE_CONTRACT_MISMATCH", file=sys.stderr, flush=True)
        return 70


def main() -> int:
    if len(sys.argv) != 13:
        return 70
    (
        profile_id,
        input_value,
        scratch_value,
        output_value,
        home_value,
        temp_value,
        canonical_value,
        cpu_value,
        memory_value,
        pid_value,
        fd_value,
        output_budget_value,
    ) = sys.argv[1:]
    input_root = Path(input_value)
    writable_roots = tuple(
        Path(value) for value in (scratch_value, output_value, home_value, temp_value)
    )
    canonical_workspace = Path(canonical_value)
    stage = "input"
    fixture_descriptor: int | None = None
    sandbox_descriptor: int | None = None
    try:
        fixture_descriptor, sandbox_descriptor = _open_fixture(input_root)
        stage = "limits"
        _apply_limits(
            cpu_seconds=int(cpu_value),
            memory_bytes=int(memory_value),
            pid_limit=int(pid_value),
            fd_limit=int(fd_value),
            output_bytes=int(output_budget_value),
            artifact_bytes=0,
        )
        stage = "landlock"
        _install_landlock(input_root, writable_roots)
        stage = "seccomp"
        _install_network_seccomp()
        stage = "boundary"
        _require_denied_boundaries(canonical_workspace)
        stage = "profile"
        os.chdir(input_root)
        return _run_profile(profile_id, fixture_descriptor, sandbox_descriptor)
    except (OSError, RuntimeError, ValueError) as exc:
        error_number = exc.errno if isinstance(exc, OSError) else 0
        print(
            f"VE_VALIDATION_SANDBOX_{stage.upper()}_UNAVAILABLE_{error_number}",
            file=sys.stderr,
            flush=True,
        )
        return 70
    finally:
        if fixture_descriptor is not None:
            os.close(fixture_descriptor)
        if sandbox_descriptor is not None:
            os.close(sandbox_descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
