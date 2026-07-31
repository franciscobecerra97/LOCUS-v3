"""Build a deterministic, allowlisted anonymous LOCUS artifact archive."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ARTIFACT_VERSION = "LOCUS-anonymous-artifact-v1"
ARCHIVE_ROOT = "locus-artifact"
RELEASE_STATUS_PATH = "artifact/RELEASE-CHECKLIST.md"

ALLOWED_EXACT = frozenset(
    {
        ".github/workflows/ci.yml",
        ".python-version",
        "LICENSE",
        "LICENSE-DOCUMENTATION.md",
        "LICENSES.md",
        "README.md",
        "artifact/EVALUATION.md",
        "artifact/INSTALL.md",
        "artifact/MANIFEST.md",
        "artifact/README.md",
        "pyproject.toml",
        "rust-toolchain.toml",
        "tasks.py",
        "uv.lock",
        "experiments/README.md",
        "experiments/processed/README.md",
        "experiments/raw/README.md",
        "paper/generated/README.md",
    }
)
ALLOWED_PREFIXES = (
    "deploy/",
    "docs/schemas/",
    "experiments/processed/performance-v2/",
    "experiments/raw/attacks-v2/",
    "experiments/raw/performance-v2/",
    "paper/generated/performance-v2/",
    "prototype/",
    "tpass-core/",
    "tpass-python/",
)
FORBIDDEN_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "target",
        "tmp",
    }
)
FORBIDDEN_SUFFIXES = (
    ".aux",
    ".bbl",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".key",
    ".log",
    ".out",
    ".p12",
    ".pem",
    ".pfx",
    ".pyc",
    ".pyd",
    ".so",
    ".synctex.gz",
)
_WINDOWS_USER_PATH = rb"[A-Za-z]:" + rb"\\Users\\" + rb"[^\\/\s]+"
_POSIX_HOME_PATH = rb"/" + rb"home/" + rb"[^/\s]+"
_POSIX_MAC_PATH = rb"/" + rb"Users/" + rb"[^/\s]+"
_POSIX_USER_PATHS = rb"(?:" + _POSIX_HOME_PATH + rb"|" + _POSIX_MAC_PATH + rb")"
LOCAL_PATH_PATTERN = re.compile(
    rb"(?:" + _WINDOWS_USER_PATH + rb"|" + _POSIX_USER_PATHS + rb")"
)
PROJECT_MANAGEMENT_PATTERNS = (
    re.compile(rb"\b(?:PLAN|AGENTS)\.md\b", re.IGNORECASE),
    re.compile(rb"\b(?:P|M)[0-9]+(?:\.[0-9]+)+\b"),
    re.compile(rb"\bCycle " + rb"1\b", re.IGNORECASE),
    re.compile(rb"\bdevelopment (?:workspace|repository)\b", re.IGNORECASE),
    re.compile(rb"\bsubmission " + rb"artifact\b", re.IGNORECASE),
    re.compile(rb"(?:^|[`\s])extra" + rb"/", re.IGNORECASE | re.MULTILINE),
)


@dataclass(frozen=True)
class ArtifactEntry:
    """One archive member and its content digest."""

    path: str
    sha256: str
    size: int


def _canonical_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or normalized.startswith("./"):
        raise ValueError(f"noncanonical artifact path: {raw_path!r}")
    return path.as_posix()


def select_artifact_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """Return the exact sorted allowlisted subset of repository paths."""

    selected: list[str] = []
    for raw_path in paths:
        path = _canonical_path(raw_path)
        parts = PurePosixPath(path).parts
        if any(part in FORBIDDEN_PARTS for part in parts):
            continue
        if path.endswith(FORBIDDEN_SUFFIXES):
            continue
        if path in ALLOWED_EXACT or path.startswith(ALLOWED_PREFIXES):
            selected.append(path)
    return tuple(sorted(set(selected)))


def validate_required_paths(paths: Sequence[str]) -> None:
    """Require the artifact entry points and authoritative v2 evidence."""

    required = {
        "LICENSE",
        "LICENSE-DOCUMENTATION.md",
        "LICENSES.md",
        "artifact/EVALUATION.md",
        "artifact/INSTALL.md",
        "artifact/MANIFEST.md",
        "artifact/README.md",
        "experiments/processed/performance-v2/summary.json",
        "paper/generated/performance-v2/manifest.json",
        "prototype/locus/__init__.py",
        "tasks.py",
    }
    missing = sorted(required - set(paths))
    if missing:
        raise ValueError(
            "artifact allowlist is missing required paths: " + ", ".join(missing)
        )
    if not any(path.startswith("experiments/raw/attacks-v2/") for path in paths):
        raise ValueError("artifact allowlist contains no retained v2 attack evidence")
    if not any(path.startswith("experiments/raw/performance-v2/") for path in paths):
        raise ValueError(
            "artifact allowlist contains no retained v2 performance evidence"
        )


def find_anonymity_violations(
    root: Path,
    paths: Sequence[str],
    identity_fragments: Iterable[str],
) -> tuple[str, ...]:
    """Return category-and-path observations without echoing identifying bytes."""

    fragments = tuple(
        sorted(
            {
                fragment.encode("utf-8")
                for fragment in identity_fragments
                if len(fragment.strip()) >= 4
            },
            key=len,
            reverse=True,
        )
    )
    violations: list[str] = []
    for path in paths:
        data = (root / Path(path)).read_bytes()
        if LOCAL_PATH_PATTERN.search(data):
            violations.append(f"local-user-path:{path}")
        lowered = data.lower()
        if any(fragment.lower() in lowered for fragment in fragments):
            violations.append(f"development-identity:{path}")
        if Path(path).suffix.lower() in {".md", ".txt"} and any(
            pattern.search(data) for pattern in PROJECT_MANAGEMENT_PATTERNS
        ):
            violations.append(f"project-management-language:{path}")
    return tuple(sorted(set(violations)))


def _git_output(root: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def repository_paths(root: Path, *, include_untracked: bool) -> tuple[str, ...]:
    """List tracked paths, optionally including non-ignored development additions."""

    arguments = ["ls-files", "-z"]
    if include_untracked:
        arguments.extend(["--cached", "--others", "--exclude-standard"])
    output = _git_output(root, arguments)
    return tuple(path for path in output.split("\0") if path)


def repository_is_clean(root: Path) -> bool:
    return not _git_output(root, ["status", "--porcelain"]).strip()


def repository_commit(root: Path) -> str:
    commit = _git_output(root, ["rev-parse", "--verify", "HEAD"]).strip().lower()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("repository commit is invalid")
    return commit


def development_identity_fragments(root: Path) -> tuple[str, ...]:
    """Collect local Git identity/path strings for rejection, never for output."""

    fragments: set[str] = {str(root), root.as_posix()}
    commands = (
        ["config", "--get", "user.name"],
        ["config", "--get", "user.email"],
        ["log", "--format=%an%n%ae"],
        ["remote", "-v"],
    )
    for command in commands:
        result = subprocess.run(
            ["git", *command],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                stripped = line.strip()
                fragments.add(stripped)
                if command == ["remote", "-v"]:
                    fields = stripped.split()
                    if len(fields) >= 2:
                        fragments.add(fields[1])
    return tuple(fragment for fragment in fragments if fragment)


def release_is_approved(root: Path) -> bool:
    text = (root / RELEASE_STATUS_PATH).read_text(encoding="utf-8")
    status_lines = [
        line.strip()
        for line in text.splitlines()
        if line.startswith("Release authorization:")
    ]
    if len(status_lines) != 1:
        raise ValueError("release checklist must contain exactly one status field")
    return status_lines[0] == "Release authorization: APPROVED"


def audit_artifact_source(root: Path, *, include_untracked: bool) -> tuple[str, ...]:
    """Validate the allowlist and anonymity boundary and return selected paths."""

    paths = select_artifact_paths(
        repository_paths(root, include_untracked=include_untracked)
    )
    validate_required_paths(paths)
    violations = find_anonymity_violations(
        root, paths, development_identity_fragments(root)
    )
    if violations:
        raise ValueError(
            "anonymous artifact audit failed (values suppressed): "
            + ", ".join(violations)
        )
    return paths


def _entry(path: str, data: bytes) -> ArtifactEntry:
    return ArtifactEntry(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
    )


def build_archive(
    root: Path,
    paths: Sequence[str],
    output: Path,
    *,
    replace: bool,
    source_commit: str,
) -> tuple[ArtifactEntry, ...]:
    """Create a deterministic archive and return its content manifest."""

    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise ValueError("artifact source commit is invalid")
    output = output.resolve()
    expected_parent = (root / "dist").resolve()
    if output.parent != expected_parent:
        raise ValueError("artifact archive output must be directly below dist/")
    if output.exists() and not replace:
        raise FileExistsError(f"artifact archive already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    entries = tuple(_entry(path, (root / Path(path)).read_bytes()) for path in paths)
    manifest = {
        "artifact": ARTIFACT_VERSION,
        "entries": [entry.__dict__ for entry in entries],
        "source_commit": source_commit,
    }
    manifest_bytes = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")

    compression = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(
        output, "w", compression=compression, compresslevel=9
    ) as archive:
        for entry in entries:
            info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/{entry.path}")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = compression
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / Path(entry.path)).read_bytes())
        info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/artifact_manifest.json")
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = compression
        info.external_attr = 0o100644 << 16
        archive.writestr(info, manifest_bytes)
    return entries
