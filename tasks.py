"""Cross-platform development commands for the LOCUS research repository."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import cast

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(command: Sequence[str], *, env: dict[str, str] | None = None) -> None:
    """Run a command from the repository root and fail on a non-zero exit."""

    print("+", subprocess.list2cmdline(list(command)), flush=True)
    subprocess.run(list(command), cwd=ROOT, check=True, env=env)


def run_capture(command: Sequence[str], *, env: dict[str, str] | None = None) -> str:
    """Run a command while retaining output that may contain smoke credentials."""

    print("+", subprocess.list2cmdline(list(command)), flush=True)
    result = subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, list(command))
    return result.stdout


def run_capture_input(
    command: Sequence[str], input_text: str, *, env: dict[str, str] | None = None
) -> str:
    """Run a command with bounded synthetic stdin and retain only its output."""

    if len(input_text.encode("utf-8")) > 32_768:
        raise RuntimeError("bounded command input is too large")
    print("+", subprocess.list2cmdline(list(command)), flush=True)
    result = subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "bounded probe failed: " + result.stderr[-2000:].replace("\r", " ")
        )
    return result.stdout


def require(executable: str) -> str:
    """Return an executable path or stop with a useful setup message."""

    path = shutil.which(executable)
    if path is None:
        raise SystemExit(
            f"Required executable '{executable}' was not found on PATH. "
            "See README.md for prerequisites."
        )
    return path


def native_build() -> None:
    """Build and install the local Rust extension into the active uv environment."""

    require("uv")
    environment = os.environ.copy()
    environment["VIRTUAL_ENV"] = sys.prefix
    run(
        [PYTHON, "-m", "maturin", "develop", "--uv", "--locked"],
        env=environment,
    )


def python_tests() -> None:
    run(
        [
            PYTHON,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "prototype/tests",
            "-t",
            "prototype",
        ]
    )


def rust_manifests() -> list[str]:
    return [
        "appss-core/Cargo.toml",
        "tpass-core/Cargo.toml",
        "tpass-python/Cargo.toml",
    ]


def rust_tests() -> None:
    for manifest in rust_manifests():
        run(
            [
                require("cargo"),
                "test",
                "--locked",
                "--manifest-path",
                manifest,
            ]
        )


def test() -> None:
    native_build()
    python_tests()
    rust_tests()


def python_sources() -> list[str]:
    """Return the Python source roots checked by all quality tools."""

    return ["tasks.py", "prototype"]


def check_python_syntax() -> None:
    """Parse project Python sources without creating bytecode files."""

    files: list[Path] = []
    for source_name in python_sources():
        source = ROOT / source_name
        files.extend([source] if source.is_file() else source.rglob("*.py"))

    for path in sorted(files):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print(f"Parsed {len(files)} Python files successfully.")


def extracted_artifact_paths(root: Path) -> tuple[str, ...]:
    """Validate an extracted artifact manifest and return its source paths."""

    manifest_path = root / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("extracted artifact manifest is unreadable") from exc
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"artifact", "entries", "source_commit"}
        or manifest["artifact"]
        not in {"LOCUS-anonymous-artifact-v1", "LOCUS-anonymous-artifact-v2"}
        or not isinstance(manifest["entries"], list)
        or not isinstance(manifest["source_commit"], str)
        or re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]) is None
    ):
        raise RuntimeError("extracted artifact manifest has an invalid envelope")

    paths: list[str] = []
    for entry in manifest["entries"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise RuntimeError("extracted artifact manifest has an invalid entry")
        raw_path = entry["path"]
        expected_digest = entry["sha256"]
        expected_size = entry["size"]
        if not isinstance(raw_path, str):
            raise RuntimeError("extracted artifact manifest path is invalid")
        path = PurePosixPath(raw_path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != raw_path
            or raw_path.startswith("./")
        ):
            raise RuntimeError("extracted artifact manifest path is noncanonical")
        if (
            not isinstance(expected_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
        ):
            raise RuntimeError("extracted artifact manifest metadata is invalid")
        source = root / Path(*path.parts)
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"artifact source file is missing: {raw_path}")
        data = source.read_bytes()
        if (
            len(data) != expected_size
            or hashlib.sha256(data).hexdigest() != expected_digest
        ):
            raise RuntimeError(f"artifact source digest mismatch: {raw_path}")
        paths.append(raw_path)

    if paths != sorted(set(paths)):
        raise RuntimeError(
            "extracted artifact manifest paths are not sorted and unique"
        )
    return tuple(paths)


def repository_hygiene() -> None:
    """Reject tracked caches, scratch measurements, and LaTeX build products."""

    development_checkout = (ROOT / ".git").exists()
    if development_checkout:
        tracked = run_capture([require("git"), "ls-files", "-z"]).split("\0")
    elif (ROOT / "artifact_manifest.json").is_file():
        tracked = list(extracted_artifact_paths(ROOT))
    else:
        raise RuntimeError(
            "source boundary is unavailable: expected .git or artifact_manifest.json"
        )
    latex_suffixes = {
        ".aux",
        ".bbl",
        ".blg",
        ".fdb_latexmk",
        ".fls",
        ".log",
        ".out",
        ".synctex.gz",
        ".toc",
    }
    forbidden: list[str] = []
    for raw_path in tracked:
        if not raw_path:
            continue
        path = Path(raw_path)
        if (
            "__pycache__" in path.parts
            or raw_path.startswith("prototype/.benchmarks/")
            or (
                path.parent == Path("paper")
                and any(path.name.endswith(suffix) for suffix in latex_suffixes)
            )
        ):
            forbidden.append(raw_path)
    if forbidden:
        raise RuntimeError(
            "generated/scratch files are tracked: " + ", ".join(sorted(forbidden))
        )
    required = {
        "LICENSE",
        "LICENSE-DOCUMENTATION.md",
        "LICENSES.md",
        "artifact/EVALUATION.md",
        "artifact/INSTALL.md",
        "artifact/MANIFEST.md",
        "artifact/README.md",
        "experiments/README.md",
        "experiments/raw/README.md",
        "experiments/processed/README.md",
        "paper/generated/README.md",
    }
    if development_checkout:
        required.add("artifact/RELEASE-CHECKLIST.md")
    missing = [path for path in sorted(required) if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(
            "repository data lifecycle is incomplete: " + ", ".join(missing)
        )
    if development_checkout:
        ignore_lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if "experiments/raw/**/*.json" not in ignore_lines:
            raise RuntimeError("retained multi-file collection ignore rule is missing")
    print("Repository source/generated-data boundaries are valid.")


def python_quality() -> None:
    sources = python_sources()
    run([PYTHON, "-m", "ruff", "format", "--check", *sources])
    run([PYTHON, "-m", "ruff", "check", *sources])
    run([PYTHON, "-m", "mypy", *sources])


def format_sources() -> None:
    sources = python_sources()
    run([PYTHON, "-m", "ruff", "format", *sources])
    run([PYTHON, "-m", "ruff", "check", "--fix", *sources])
    for manifest in rust_manifests():
        run([require("cargo"), "fmt", "--manifest-path", manifest])


def rust_quality() -> None:
    for manifest in rust_manifests():
        run(
            [
                require("cargo"),
                "fmt",
                "--manifest-path",
                manifest,
                "--",
                "--check",
            ]
        )
        run(
            [
                require("cargo"),
                "clippy",
                "--locked",
                "--manifest-path",
                manifest,
                "--all-targets",
                "--",
                "-D",
                "warnings",
            ]
        )


def check() -> None:
    repository_hygiene()
    check_python_syntax()
    python_quality()
    rust_quality()
    test()


def artifact_package(args: argparse.Namespace) -> None:
    """Audit or build the deterministic anonymous artifact package."""

    from locus.artifact_package import (
        ARTIFACT_VERSION,
        audit_artifact_source,
        build_archive,
        release_is_approved,
        repository_commit,
        repository_is_clean,
    )

    if args.check:
        paths = audit_artifact_source(ROOT, include_untracked=True)
        report = {
            "artifact": ARTIFACT_VERSION,
            "archive_created": False,
            "candidate_files": len(paths),
            "release_authorization": (
                "approved" if release_is_approved(ROOT) else "pending"
            ),
            "repository_clean": repository_is_clean(ROOT),
            "status": "audit-passed",
        }
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return

    if not repository_is_clean(ROOT):
        raise RuntimeError(
            "artifact archive creation requires a clean committed repository"
        )
    if not release_is_approved(ROOT):
        raise RuntimeError(
            "artifact release authorization is pending; see "
            "artifact/RELEASE-CHECKLIST.md"
        )
    paths = audit_artifact_source(ROOT, include_untracked=False)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    entries = build_archive(
        ROOT,
        paths,
        output,
        replace=args.replace,
        source_commit=repository_commit(ROOT),
    )
    archive_digest = hashlib.sha256(output.read_bytes()).hexdigest()
    report = {
        "artifact": ARTIFACT_VERSION,
        "archive": output.relative_to(ROOT).as_posix(),
        "archive_created": True,
        "files": len(entries),
        "sha256": archive_digest,
        "status": "ok",
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


def demo(extra: Sequence[str]) -> None:
    run([PYTHON, "-B", "prototype/scripts/run_demo.py", *extra])


def walkthrough() -> None:
    """Run the synthetic-only interactive protocol walkthrough."""

    run([PYTHON, "-B", "prototype/scripts/run_walkthrough.py"])


def research_ui(args: argparse.Namespace) -> None:
    """Run the no-persistence P7 research UI on an exact loopback endpoint."""

    run(
        [
            PYTHON,
            "-B",
            "-m",
            "locus.research_ui",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ]
    )


INTEGRATED_COMPOSE = ROOT / "deploy" / "compose.integrated.yaml"
INTEGRATED_MANIFEST = ROOT / "deploy" / "integrated-manifest.json"


def _integrated_environment(project: str, port: int) -> dict[str, str]:
    environment = os.environ.copy()
    seed = hashlib.sha256(f"LOCUS integrated local {project}".encode()).hexdigest()
    environment.update(
        {
            "LOCUS_INTEGRATED_IMAGE": "locus-integrated-reference:local",
            "LOCUS_S3_ACCESS_KEY": f"local-{seed[:24]}",
            "LOCUS_S3_BUCKET": f"locus-{seed[:20]}",
            "LOCUS_S3_SECRET_KEY": seed,
            "LOCUS_UI_PORT": str(port),
        }
    )
    return environment


def _integrated_compose_command(project: str, profile: str) -> list[str]:
    return [
        require("docker"),
        "compose",
        "--project-name",
        project,
        "--file",
        str(INTEGRATED_COMPOSE),
        "--profile",
        profile,
    ]


def _validate_integrated_compose(value: dict[str, object], *, client: str) -> None:
    services = value.get("services")
    expected = {
        "admission",
        "bootstrap",
        "operator",
        "party1",
        "party2",
        "party3",
        "party4",
        "party5",
        "resolver",
        "s3",
        "storage-gateway",
        client,
    }
    if not isinstance(services, dict) or set(services) != expected:
        raise RuntimeError("integrated Compose has an unexpected service set")
    networks = value.get("networks")
    expected_networks = {
        "admission",
        "browser-edge",
        "cloud",
        "control",
        "recovery",
        "resolver",
        "storage",
    }
    if not isinstance(networks, dict) or set(networks) != expected_networks:
        raise RuntimeError("integrated Compose networks are not exact")
    for network_name, item in networks.items():
        if not isinstance(item, dict) or (
            network_name != "browser-edge" and item.get("internal") is not True
        ):
            raise RuntimeError("integrated service network is not internal")
    expected_membership = {
        "admission": {"admission"},
        "operator": {"control"},
        "resolver": {"resolver"},
        "s3": {"cloud"},
        "storage-gateway": {"cloud", "storage"},
        client: {
            "admission",
            "browser-edge",
            "control",
            "recovery",
            "resolver",
            "storage",
        },
        **{f"party{index}": {"recovery"} for index in range(1, 6)},
    }
    for name, raw in services.items():
        if not isinstance(raw, dict):
            raise RuntimeError("invalid integrated service")
        ports = raw.get("ports")
        if name == client:
            if (
                not isinstance(ports, list)
                or len(ports) != 1
                or not isinstance(ports[0], dict)
                or ports[0].get("host_ip") != "127.0.0.1"
                or ports[0].get("target") != 8080
            ):
                raise RuntimeError("integrated UI is not loopback-only")
        elif ports not in (None, []):
            raise RuntimeError("an internal integrated service publishes a port")
        if raw.get("read_only") is not True or raw.get("ulimits") != {"core": {}}:
            raise RuntimeError("integrated service hardening is incomplete")
        if raw.get("security_opt") != ["no-new-privileges:true"]:
            raise RuntimeError("integrated service lacks no-new-privileges")
        if name == "bootstrap":
            if raw.get("network_mode") != "none" or raw.get("networks") not in (
                None,
                {},
            ):
                raise RuntimeError("integrated bootstrap is not networkless")
        else:
            membership = raw.get("networks")
            if (
                not isinstance(membership, dict)
                or set(membership) != expected_membership[name]
            ):
                raise RuntimeError(f"invalid integrated network membership: {name}")
        mounts = raw.get("volumes", [])
        if not isinstance(mounts, list) or any(
            isinstance(item, dict)
            and item.get("source")
            in {"/var/run/docker.sock", "\\.\\pipe\\docker_engine"}
            for item in mounts
        ):
            raise RuntimeError("invalid integrated service mount")


def integrated_config() -> None:
    from locus.integrated_manifest import load_integrated_manifest

    manifest = load_integrated_manifest(INTEGRATED_MANIFEST)
    for profile, client in (("enrollment", "ui-client-a"), ("recovery", "ui-client-b")):
        environment = _integrated_environment("locus-integrated-config", 8765)
        configured = json.loads(
            run_capture(
                [
                    *_integrated_compose_command("locus-integrated-config", profile),
                    "config",
                    "--format",
                    "json",
                ],
                env=environment,
            )
        )
        _validate_integrated_compose(configured, client=client)
    print(
        json.dumps(
            {
                "deployment_id": manifest["deployment_id"],
                "profiles": 2,
                "status": "valid",
            },
            sort_keys=True,
        )
    )


def integrated_start(args: argparse.Namespace) -> None:
    integrated_config()
    environment = _integrated_environment(args.project, args.port)
    command = _integrated_compose_command(args.project, args.mode)
    run([*command, "build", "bootstrap"], env=environment)
    running = set(
        run_capture(
            [*command, "ps", "--services", "--status", "running"], env=environment
        ).splitlines()
    )
    common = {"admission", "operator", "resolver", "storage-gateway", "s3"} | {
        f"party{index}" for index in range(1, 6)
    }
    if args.mode == "recovery" and common <= running:
        enrollment = _integrated_compose_command(args.project, "enrollment")
        run([*enrollment, "stop", "ui-client-a"], env=environment)
        run([*enrollment, "rm", "--force", "ui-client-a"], env=environment)
        run(
            [
                require("docker"),
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--volume",
                f"{args.project}_client-a-data:/audit:ro",
                environment["LOCUS_INTEGRATED_IMAGE"],
                "python",
                "-m",
                "locus.integrated_state_audit",
                "--root",
                "/audit",
            ],
            env=environment,
        )
        run(
            [
                *command,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--wait",
                "ui-client-b",
            ],
            env=environment,
        )
    else:
        run([*command, "up", "--detach", "--no-build", "--wait"], env=environment)
    print(
        json.dumps(
            {
                "client": "A" if args.mode == "enrollment" else "B",
                "project": args.project,
                "status": "ready",
                "url": f"http://127.0.0.1:{args.port}/",
            },
            sort_keys=True,
        )
    )


def integrated_stop(args: argparse.Namespace) -> None:
    environment = _integrated_environment(args.project, args.port)
    command = _integrated_compose_command(args.project, "enrollment")
    if args.destroy:
        run(
            [
                *command,
                "down",
                "--remove-orphans",
                "--volumes",
                "--rmi",
                "local",
            ],
            env=environment,
        )
    else:
        both_profiles = [
            require("docker"),
            "compose",
            "--project-name",
            args.project,
            "--file",
            str(INTEGRATED_COMPOSE),
            "--profile",
            "enrollment",
            "--profile",
            "recovery",
        ]
        run([*both_profiles, "stop", "ui-client-a", "ui-client-b"], env=environment)


def _post_json(
    port: int, path: str, value: dict[str, object], *, expected: int = 200
) -> dict[str, object]:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(50):
        try:
            with urllib.request.urlopen(  # noqa: S310
                request, timeout=120
            ) as response:
                status = response.status
                body = response.read(256 * 1024)
            break
        except urllib.error.HTTPError as error:
            status = error.code
            body = error.read(256 * 1024)
            break
        except urllib.error.URLError:
            if attempt == 49:
                raise
            time.sleep(0.2)
    if status != expected:
        raise RuntimeError(f"integrated UI returned HTTP {status} for {path}")
    result = json.loads(body)
    if not isinstance(result, dict):
        raise RuntimeError("integrated UI returned a non-object")
    return cast(dict[str, object], result)


def integrated_smoke() -> None:
    integrated_config()
    project = f"locus-int-{secrets.token_hex(5)}"
    port = _free_loopback_port()
    environment = _integrated_environment(project, port)
    environment["LOCUS_INTEGRATED_SUCCESSOR_CRASH_PHASES"] = ",".join(
        (
            "PRESERVE_ORIGINAL_KEY",
            "PREPARE_PARTIES",
            "PUBLISH_BACKUP",
            "PUBLISH_DESCRIPTOR",
            "VERIFY_READINESS",
            "VERIFY_SUCCESSOR_RECOVERY",
            "ACTIVATE_SUCCESSOR",
            "RETIRE_PREDECESSOR",
        )
    )
    enrollment = _integrated_compose_command(project, "enrollment")
    recovery = _integrated_compose_command(project, "recovery")
    synthetic_key = bytes(range(32)).hex()
    email = ["Ada@Example.COM", "grace@example.net", "linus@example.org"]
    policy_inputs: dict[str, object] = {
        "LOCUS-canonical-email-set-v1": email,
        "LOCUS-canonical-phone-set-v1": [
            "+352621000001",
            "+352621000002",
            "+352621000003",
        ],
        "LOCUS-quantized-coordinate-set-v1": [
            {"latitude": "49.61160001", "longitude": "6.13190001"},
            {"latitude": "48.8566", "longitude": "2.3522"},
            {"latitude": "51.5074", "longitude": "-0.1278"},
        ],
        "LOCUS-location-person-set-v1": [
            {
                "location": {"latitude": "49.6116", "longitude": "6.1319"},
                "person": {"type": "email", "value": "Ada@Example.COM"},
            },
            {
                "location": {"latitude": "48.8566", "longitude": "2.3522"},
                "person": {"type": "phone", "value": "+352621000002"},
            },
            {
                "location": {"latitude": "51.5074", "longitude": "-0.1278"},
                "person": {"type": "email", "value": "linus@example.org"},
            },
        ],
    }
    arms = (
        ("LOCUS-TPASS-YI-ZK-RISTRETTO255-v1", "LOCUS-paired-suite-deployment-2of3-v1"),
        (
            "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "LOCUS-paired-suite-deployment-2of3-v1",
        ),
        ("LOCUS-TPASS-YI-ZK-RISTRETTO255-v1", "LOCUS-paired-suite-deployment-3of5-v1"),
        (
            "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "LOCUS-paired-suite-deployment-3of5-v1",
        ),
    )
    receipts: list[str] = []
    policy_receipts: list[tuple[str, object, str]] = []
    try:
        if os.environ.get("LOCUS_INTEGRATED_NO_BUILD") != "1":
            run([*enrollment, "build", "bootstrap"], env=environment)
        run([*enrollment, "up", "--detach", "--no-build", "--wait"], env=environment)
        for index, (suite, profile) in enumerate(arms, start=1):
            result = _post_json(
                port,
                "/api/v1/enroll",
                {
                    "api_version": "LOCUS-client-api-v1",
                    "deployment_profile_id": profile,
                    "operation_id": f"integrated-enroll-{index}",
                    "policy_id": "LOCUS-canonical-email-set-v1",
                    "protected_key": {"hex": synthetic_key, "mode": "import-synthetic"},
                    "recovery_input": email,
                    "suite_id": suite,
                },
            )
            if result.get("status") != "enrolled" or not isinstance(
                result.get("receipt"), str
            ):
                raise RuntimeError("integrated enrollment did not complete")
            receipts.append(cast(str, result["receipt"]))
        for index, (policy_id, recovery_input) in enumerate(
            policy_inputs.items(), start=1
        ):
            result = _post_json(
                port,
                "/api/v1/enroll",
                {
                    "api_version": "LOCUS-client-api-v1",
                    "deployment_profile_id": "LOCUS-paired-suite-deployment-2of3-v1",
                    "operation_id": f"integrated-policy-enroll-{index}",
                    "policy_id": policy_id,
                    "protected_key": {
                        "hex": synthetic_key,
                        "mode": "import-synthetic",
                    },
                    "recovery_input": recovery_input,
                    "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                },
            )
            if result.get("status") != "enrolled" or not isinstance(
                result.get("receipt"), str
            ):
                raise RuntimeError("integrated policy enrollment did not complete")
            policy_receipts.append(
                (policy_id, recovery_input, cast(str, result["receipt"]))
            )
        run([*enrollment, "stop", "ui-client-a"], env=environment)
        run([*enrollment, "rm", "--force", "ui-client-a"], env=environment)
        volume = f"{project}_client-a-data"
        run(
            [
                require("docker"),
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--volume",
                f"{volume}:/audit:ro",
                environment["LOCUS_INTEGRATED_IMAGE"],
                "python",
                "-m",
                "locus.integrated_state_audit",
                "--root",
                "/audit",
            ],
            env=environment,
        )
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--wait",
                "ui-client-b",
            ],
            env=environment,
        )
        for index, receipt in enumerate(receipts, start=1):
            result = _post_json(
                port,
                "/api/v1/recover",
                {
                    "api_version": "LOCUS-client-api-v1",
                    "operation_id": f"integrated-recover-{index}",
                    "receipt": receipt,
                    "recovery_input": email,
                },
            )
            if (
                result.get("status") != "recovered"
                or result.get("key_identity_verified") is not True
            ):
                raise RuntimeError(
                    "integrated recovery did not verify the protected key"
                )
        replay = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-recover-1",
                "receipt": receipts[0],
                "recovery_input": email,
            },
            expected=409,
        )
        if replay.get("category") != "operation_conflict":
            raise RuntimeError("completed-operation replay was not rejected")
        subset_recoveries = 0
        for holder_ids, threshold, selected_receipts, topology in (
            ((1, 2, 3), 2, receipts[:2], "2of3"),
            ((1, 2, 3, 4, 5), 3, receipts[2:], "3of5"),
        ):
            ordered_subsets: list[tuple[int, ...]] = []
            for subset in combinations(holder_ids, threshold):
                remainder = tuple(
                    holder_id for holder_id in holder_ids if holder_id not in subset
                )
                order = (*subset, *remainder)
                ordered_subsets.extend((order, order))
            environment["LOCUS_INTEGRATED_HOLDER_SCHEDULE"] = ";".join(
                ",".join(str(holder_id) for holder_id in order)
                for order in ordered_subsets
            )
            run(
                [
                    *recovery,
                    "up",
                    "--detach",
                    "--no-build",
                    "--no-deps",
                    "--force-recreate",
                    "--wait",
                    "ui-client-b",
                ],
                env=environment,
            )
            for subset_index, _subset in enumerate(
                combinations(holder_ids, threshold), start=1
            ):
                for suite_index, receipt in enumerate(selected_receipts, start=1):
                    result = _post_json(
                        port,
                        "/api/v1/recover",
                        {
                            "api_version": "LOCUS-client-api-v1",
                            "operation_id": (
                                f"integrated-subset-{topology}-{subset_index}-"
                                f"{suite_index}"
                            ),
                            "receipt": receipt,
                            "recovery_input": email,
                        },
                    )
                    if result.get("status") != "recovered":
                        raise RuntimeError("exact threshold subset recovery failed")
                    subset_recoveries += 1
        environment["LOCUS_INTEGRATED_HOLDER_SCHEDULE"] = ""
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--force-recreate",
                "--wait",
                "ui-client-b",
            ],
            env=environment,
        )
        environment["LOCUS_INTEGRATED_DISABLED_HOLDERS"] = "3,4,5"
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--force-recreate",
                "--wait",
                "ui-client-b",
            ],
            env=environment,
        )
        below_threshold = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-below-threshold",
                "receipt": receipts[2],
                "recovery_input": email,
            },
            expected=400,
        )
        if below_threshold.get("category") != "recovery_rejected":
            raise RuntimeError("below-threshold failure was not normalized")
        threshold_logs = run_capture(
            [*recovery, "logs", "--no-color", "ui-client-b"], env=environment
        )
        if '"stage":"suite-recovery"' not in threshold_logs:
            raise RuntimeError(
                "below-threshold failure did not pass authorization first"
            )
        environment["LOCUS_INTEGRATED_DISABLED_HOLDERS"] = ""
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--force-recreate",
                "--wait",
                "ui-client-b",
            ],
            env=environment,
        )
        for index, (policy_id, recovery_input, receipt) in enumerate(
            policy_receipts, start=1
        ):
            result = _post_json(
                port,
                "/api/v1/recover",
                {
                    "api_version": "LOCUS-client-api-v1",
                    "operation_id": f"integrated-policy-recover-{index}",
                    "receipt": receipt,
                    "recovery_input": recovery_input,
                },
            )
            if result.get("status") != "recovered":
                raise RuntimeError(f"integrated policy recovery failed: {policy_id}")
        wrong = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-wrong-input",
                "receipt": receipts[0],
                "recovery_input": [
                    "wrong1@example.test",
                    "wrong2@example.test",
                    "wrong3@example.test",
                ],
            },
            expected=400,
        )
        if wrong.get("category") != "recovery_rejected":
            raise RuntimeError("wrong input was not normalized")
        successor_suites = (
            "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
        )
        successor_profiles = (
            "LOCUS-paired-suite-deployment-2of3-v1",
            "LOCUS-paired-suite-deployment-2of3-v1",
            "LOCUS-paired-suite-deployment-3of5-v1",
            "LOCUS-paired-suite-deployment-3of5-v1",
        )
        successor_receipts: list[str] = []
        for index, receipt in enumerate(receipts):
            result = _post_json(
                port,
                "/api/v1/successor",
                {
                    "api_version": "LOCUS-client-api-v1",
                    "operation_id": f"integrated-successor-{index + 1}",
                    "receipt": receipt,
                    "recovery_input": email,
                    "rotate_protected_key": False,
                    "successor_deployment_profile_id": successor_profiles[index],
                    "successor_suite_id": successor_suites[index],
                },
            )
            if result.get("status") != "successor_enrolled" or result.get("epoch") != 2:
                raise RuntimeError("integrated successor did not complete")
            successor_receipts.append(cast(str, result["receipt"]))
        for index, receipt in enumerate(successor_receipts, start=1):
            result = _post_json(
                port,
                "/api/v1/recover",
                {
                    "api_version": "LOCUS-client-api-v1",
                    "operation_id": f"integrated-successor-recover-{index}",
                    "receipt": receipt,
                    "recovery_input": email,
                },
            )
            if result.get("status") != "recovered" or result.get("epoch") != 2:
                raise RuntimeError("integrated successor recovery failed")
        lifecycle_logs = run_capture(
            [*recovery, "logs", "--no-color", "ui-client-b"], env=environment
        )
        crash_phases = {
            "PRESERVE_ORIGINAL_KEY",
            "PREPARE_PARTIES",
            "PUBLISH_BACKUP",
            "PUBLISH_DESCRIPTOR",
            "VERIFY_READINESS",
            "VERIFY_SUCCESSOR_RECOVERY",
            "ACTIVATE_SUCCESSOR",
            "RETIRE_PREDECESSOR",
        }
        if not all(f'"phase":"{phase}"' in lifecycle_logs for phase in crash_phases):
            raise RuntimeError("successor crash-resumption matrix is incomplete")
        stale_probe = run_capture_input(
            [
                *recovery,
                "exec",
                "--no-TTY",
                "ui-client-b",
                "python",
                "-m",
                "locus.integrated_fault_probe",
                "stale-cas",
                "--root",
                "/role",
            ],
            json.dumps(
                {"receipt": successor_receipts[0]},
                sort_keys=True,
                separators=(",", ":"),
            ),
            env=environment,
        )
        if json.loads(stale_probe) != {"status": "stale_rejected"}:
            raise RuntimeError("stale current-pointer CAS probe failed")
        downgrade = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-downgrade-attempt",
                "receipt": successor_receipts[0],
                "recovery_input": email,
                "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            },
            expected=400,
        )
        if downgrade.get("category") != "recovery_rejected":
            raise RuntimeError("suite override was not rejected")
        run([*recovery, "stop", "party1"], env=environment)
        fallback = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-one-party-unavailable",
                "receipt": successor_receipts[3],
                "recovery_input": email,
            },
        )
        if fallback.get("status") != "recovered":
            raise RuntimeError("available threshold subset was not selected")
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--wait",
                "party1",
            ],
            env=environment,
        )
        run([*recovery, "stop", "party4", "party5"], env=environment)
        quorum_loss = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-authorization-quorum-loss",
                "receipt": successor_receipts[0],
                "recovery_input": email,
            },
            expected=400,
        )
        if quorum_loss.get("category") != "recovery_rejected":
            raise RuntimeError("authorization quorum loss was not normalized")
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--wait",
                "party4",
                "party5",
            ],
            env=environment,
        )
        run([*recovery, "restart", "party5"], env=environment)
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-build",
                "--no-deps",
                "--wait",
                "party5",
            ],
            env=environment,
        )
        restarted = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-party-restart",
                "receipt": successor_receipts[3],
                "recovery_input": email,
            },
        )
        if restarted.get("status") != "recovered":
            raise RuntimeError("party restart recovery failed")
        run([*recovery, "stop", "s3"], env=environment)
        provider_outage = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-provider-outage",
                "receipt": successor_receipts[0],
                "recovery_input": email,
            },
            expected=400,
        )
        if provider_outage.get("category") != "recovery_rejected":
            raise RuntimeError("provider outage was not normalized")
        run(
            [
                *recovery,
                "up",
                "--detach",
                "--no-deps",
                "--wait",
                "s3",
            ],
            env=environment,
        )
        provider_restored = _post_json(
            port,
            "/api/v1/recover",
            {
                "api_version": "LOCUS-client-api-v1",
                "operation_id": "integrated-provider-restored",
                "receipt": successor_receipts[0],
                "recovery_input": email,
            },
        )
        if provider_restored.get("status") != "recovered":
            raise RuntimeError("provider restoration recovery failed")
        live_membership = {
            "admission": {"admission"},
            "operator": {"control"},
            "resolver": {"resolver"},
            "s3": {"cloud"},
            "storage-gateway": {"cloud", "storage"},
            "party1": {"recovery"},
            "party2": {"recovery"},
            "party3": {"recovery"},
            "party4": {"recovery"},
            "party5": {"recovery"},
            "ui-client-b": {
                "admission",
                "browser-edge",
                "control",
                "recovery",
                "resolver",
                "storage",
            },
        }
        for service, expected_networks in live_membership.items():
            container_id = run_capture(
                [*recovery, "ps", "--quiet", service], env=environment
            ).strip()
            if not container_id:
                raise RuntimeError(f"integrated live service is absent: {service}")
            networks = json.loads(
                run_capture(
                    [
                        require("docker"),
                        "inspect",
                        "--format",
                        "{{json .NetworkSettings.Networks}}",
                        container_id,
                    ],
                    env=environment,
                )
            )
            observed_networks = {name.removeprefix(f"{project}_") for name in networks}
            if observed_networks != expected_networks:
                raise RuntimeError(
                    f"integrated live network membership changed: {service}"
                )
        from locus.redaction import exposed_categories

        all_logs = run_capture([*recovery, "logs", "--no-color"], env=environment)
        exposures = exposed_categories(
            all_logs,
            {
                "synthetic-protected-key": synthetic_key,
                "synthetic-cue-1": email[0],
                "synthetic-cue-2": email[1],
                "synthetic-cue-3": email[2],
                "storage-access-key": environment["LOCUS_S3_ACCESS_KEY"],
                "storage-secret-key": environment["LOCUS_S3_SECRET_KEY"],
            },
        )
        if exposures:
            raise RuntimeError(
                "integrated output scan found prohibited categories: "
                + ",".join(exposures)
            )
        run([*recovery, "stop"], env=environment)
        role_volumes = (
            ("admission-data", "admission"),
            ("bootstrap-data", "bootstrap"),
            ("client-b-data", "client"),
            ("operator-data", "operator"),
            ("party1-data", "party"),
            ("party2-data", "party"),
            ("party3-data", "party"),
            ("party4-data", "party"),
            ("party5-data", "party"),
            ("resolver-data", "resolver"),
            ("s3-data", "provider"),
            ("s3-role-data", "s3-role"),
            ("storage-gateway-data", "storage-gateway"),
        )
        for volume_name, role in role_volumes:
            audit = run_capture(
                [
                    require("docker"),
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--read-only",
                    "--volume",
                    f"{project}_{volume_name}:/audit:ro",
                    environment["LOCUS_INTEGRATED_IMAGE"],
                    "python",
                    "-m",
                    "locus.integrated_state_audit",
                    "--root",
                    "/audit",
                    "--role",
                    role,
                ],
                env=environment,
            )
            audit_lines = [line for line in audit.splitlines() if line.startswith("{")]
            if not audit_lines or json.loads(audit_lines[-1]).get("status") != "clean":
                raise RuntimeError(f"integrated role-state audit failed: {role}")
        print(
            json.dumps(
                {
                    "arms": 4,
                    "clean_client": True,
                    "below_threshold_after_authorization": True,
                    "faults": 5,
                    "lifecycle_crash_phases": len(crash_phases),
                    "live_network_audits": len(live_membership),
                    "policies": 4,
                    "output_scan": "passed",
                    "role_state_audits": len(role_volumes) + 1,
                    "subset_recoveries": subset_recoveries,
                    "stale_cas": "rejected",
                    "status": "passed",
                    "successors": 4,
                },
                sort_keys=True,
            )
        )
    except BaseException:
        active_error = sys.exc_info()[1]
        safe_diagnostics: list[str] = []
        for command, service in (
            (enrollment, "ui-client-a"),
            (recovery, "ui-client-b"),
        ):
            logs = run_capture(
                [*command, "logs", "--no-color", service], env=environment
            )
            safe_diagnostics.extend(
                line for line in logs.splitlines() if '"stage"' in line
            )
        if safe_diagnostics:
            print(safe_diagnostics[-1], file=sys.stderr, flush=True)
        print(
            json.dumps(
                {
                    "category": "integrated_smoke_failed",
                    "error": type(active_error).__name__,
                    "message": str(active_error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
            flush=True,
        )
        raise
    finally:
        cleanup = [
            require("docker"),
            "compose",
            "--project-name",
            project,
            "--file",
            str(INTEGRATED_COMPOSE),
            "--profile",
            "enrollment",
            "--profile",
            "recovery",
        ]
        run_capture(
            [*cleanup, "down", "--volumes", "--remove-orphans"], env=environment
        )
        leftovers = {
            "containers": run_capture(
                [
                    require("docker"),
                    "ps",
                    "--all",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                    "--format",
                    "{{.ID}}",
                ],
                env=environment,
            ).strip(),
            "networks": run_capture(
                [
                    require("docker"),
                    "network",
                    "ls",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                    "--format",
                    "{{.ID}}",
                ],
                env=environment,
            ).strip(),
            "volumes": run_capture(
                [
                    require("docker"),
                    "volume",
                    "ls",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                    "--format",
                    "{{.Name}}",
                ],
                env=environment,
            ).strip(),
        }
        if any(leftovers.values()):
            raise RuntimeError("integrated project cleanup left Docker objects")


def benchmark(extra: Sequence[str]) -> None:
    run([PYTHON, "-B", "prototype/scripts/run_benchmarks.py", *extra])


def attempt_model() -> None:
    """Run the frozen bounded attempt-control counterexample model."""

    run([PYTHON, "-B", "-m", "locus.attempt_model"])


def smoke() -> None:
    test()
    demo([])
    demo(["--simulator"])
    demo(["--concrete"])


def artifact_smoke() -> None:
    """Exercise every currently available artifact path without saving results."""

    check()
    attempt_model()
    demo([])
    demo(["--simulator"])
    demo(["--concrete"])
    benchmark(["--backend", "native", "--runs", "1"])
    benchmark(["--backend", "concrete", "--runs", "1"])


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _validate_s3_compose(configured: dict[str, object], *, image: str) -> None:
    """Fail closed if the smoke deployment broadens the cloud-role boundary."""

    services = configured.get("services")
    if not isinstance(services, dict) or set(services) != {"s3"}:
        raise RuntimeError("S3 smoke Compose must contain only the cloud service")
    service = services["s3"]
    if not isinstance(service, dict) or service.get("image") != image:
        raise RuntimeError("S3 smoke Compose image is not pinned as expected")
    environment = service.get("environment")
    expected_environment = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET"}
    if not isinstance(environment, dict) or set(environment) != expected_environment:
        raise RuntimeError("S3 smoke credentials escaped the minimal cloud service")
    ports = service.get("ports")
    if (
        not isinstance(ports, list)
        or len(ports) != 1
        or not isinstance(ports[0], dict)
        or ports[0].get("host_ip") != "127.0.0.1"
        or ports[0].get("target") != 8333
    ):
        raise RuntimeError("S3 smoke endpoint must bind only to loopback")
    mounts = service.get("volumes")
    if (
        not isinstance(mounts, list)
        or len(mounts) != 1
        or not isinstance(mounts[0], dict)
        or mounts[0].get("type") != "volume"
        or mounts[0].get("target") != "/data"
    ):
        raise RuntimeError("S3 smoke data must use exactly one cloud-only volume")
    service_networks = service.get("networks")
    networks = configured.get("networks")
    if (
        not isinstance(service_networks, dict)
        or set(service_networks) != {"cloud"}
        or not isinstance(networks, dict)
        or set(networks) != {"cloud"}
        or not isinstance(networks["cloud"], dict)
    ):
        raise RuntimeError("S3 smoke service must use only the dedicated cloud network")
    # Compose 2.34's JSON formatter elides nested numeric zero values while its
    # normalized YAML and created container preserve soft=hard=0.
    if service.get("ulimits") != {"core": {}}:
        raise RuntimeError("S3 smoke core dumps must be disabled")


def _validate_deployment_compose(
    configured: dict[str, object],
    *,
    reference_image: str,
    configurable_endpoints: bool = False,
) -> None:
    """Fail closed if the complete local deployment violates its role matrix."""

    services = configured.get("services")
    expected_services = {
        "attack",
        "benchmark",
        "client",
        "cloud-snapshot-attack",
        "cloud-snapshot-collector",
        "combined-cloud-snapshot-collector",
        "combined-party-snapshot-collector",
        "combined-snapshot-attack",
        "combined-snapshot-finalizer",
        "demo",
        "party1",
        "party2",
        "party3",
        "party4",
        "party5",
        "party-snapshot-attack",
        "party-snapshot-collector",
        "provisioner",
        "resolver",
        "s3",
    }
    if not isinstance(services, dict) or set(services) != expected_services:
        raise RuntimeError("deployment Compose has an unexpected service set")
    networks = configured.get("networks")
    if not isinstance(networks, dict) or set(networks) != {
        "cloud",
        "recovery",
        "resolver",
    }:
        raise RuntimeError("deployment Compose has an unexpected network set")
    if any(
        not isinstance(network, dict) or network.get("internal") is not True
        for network in networks.values()
    ):
        raise RuntimeError("every deployment network must be internal")
    volumes = configured.get("volumes")
    expected_volumes = {
        "cloud-snapshot-data",
        "combined-snapshot-data",
        "client-data",
        "party1-data",
        "party2-data",
        "party3-data",
        "party4-data",
        "party5-data",
        "party-snapshot-data",
        "s3-data",
    }
    if not isinstance(volumes, dict) or set(volumes) != expected_volumes:
        raise RuntimeError("deployment Compose has an unexpected volume set")

    def service(name: str) -> dict[str, object]:
        value = services[name]
        if not isinstance(value, dict):
            raise RuntimeError(f"invalid deployment service: {name}")
        if value.get("ports") not in (None, []):
            raise RuntimeError("deployment services must not publish host ports")
        if value.get("read_only") is not True:
            raise RuntimeError(f"deployment service root must be read-only: {name}")
        security = value.get("security_opt")
        if security != ["no-new-privileges:true"]:
            raise RuntimeError(f"deployment service is missing hardening: {name}")
        if value.get("ulimits") != {"core": {}}:
            raise RuntimeError(f"deployment service core dumps are enabled: {name}")
        return value

    reference_services = {
        "attack",
        "benchmark",
        "client",
        "cloud-snapshot-attack",
        "cloud-snapshot-collector",
        "combined-cloud-snapshot-collector",
        "combined-party-snapshot-collector",
        "combined-snapshot-attack",
        "combined-snapshot-finalizer",
        "demo",
        "party1",
        "party2",
        "party3",
        "party4",
        "party5",
        "party-snapshot-attack",
        "party-snapshot-collector",
        "provisioner",
        "resolver",
    }
    for name in reference_services:
        value = service(name)
        if value.get("image") != reference_image or value.get("cap_drop") != ["ALL"]:
            raise RuntimeError(f"invalid reference-image boundary: {name}")
    for party_id in range(1, 6):
        name = f"party{party_id}"
        value = service(name)
        if value.get("networks") != {"recovery": None}:
            raise RuntimeError(f"party escaped the recovery network: {name}")
        mounts = value.get("volumes")
        if (
            not isinstance(mounts, list)
            or len(mounts) != 1
            or mounts[0].get("source") != f"party{party_id}-data"
            or mounts[0].get("target") != "/var/lib/locus"
            or mounts[0].get("read_only") is True
        ):
            raise RuntimeError(f"party volume isolation failed: {name}")
        if value.get("environment") not in (None, {}):
            raise RuntimeError(f"party received environment credentials: {name}")
        if value.get("user") != "65532:65532" or "healthcheck" not in value:
            raise RuntimeError(f"party identity/health boundary failed: {name}")

    client_services = {
        "attack": ["attack"],
        "benchmark": ["benchmark"],
        "client": None,
        "demo": ["demo"],
    }
    for name, expected_profile in client_services.items():
        client = service(name)
        if set(cast(dict[str, object], client.get("networks", {}))) != {
            "cloud",
            "recovery",
            "resolver",
        }:
            raise RuntimeError(f"client runner network boundary changed: {name}")
        client_environment = client.get("environment")
        if not isinstance(client_environment, dict) or set(client_environment) != {
            "LOCUS_S3_ACCESS_KEY",
            "LOCUS_S3_BUCKET",
            "LOCUS_S3_ENDPOINT",
            "LOCUS_S3_PREFIX",
            "LOCUS_S3_SECRET_KEY",
        }:
            raise RuntimeError(f"client runner credential boundary changed: {name}")
        client_mounts = client.get("volumes")
        if (
            not isinstance(client_mounts, list)
            or len(client_mounts) != 1
            or client_mounts[0].get("source") != "client-data"
            or client_mounts[0].get("target") != "/var/lib/locus-client"
            or client_mounts[0].get("read_only") is not True
            or client.get("user") != "65532:65532"
            or client.get("profiles") != expected_profile
        ):
            raise RuntimeError(f"client runner identity/volume changed: {name}")

    client_command = [
        "python",
        "-m",
        "locus.deployment",
        "client",
        "--client-root",
        "/var/lib/locus-client",
        "--resolver-url",
        "http://resolver:8080/v1/cues",
    ]
    if service("client").get("command") != client_command:
        raise RuntimeError("default client command changed")
    if service("demo").get("command") != client_command:
        raise RuntimeError("demo profile stopped using the deployed client path")
    benchmark_command = service("benchmark").get("command")
    if (
        not isinstance(benchmark_command, list)
        or benchmark_command[:-1]
        != [
            "python",
            "-m",
            "locus.deployment",
            "benchmark",
            "--client-root",
            "/var/lib/locus-client",
            "--resolver-url",
            "http://resolver:8080/v1/cues",
            "--runs",
        ]
        or benchmark_command[-1] not in {"1", "2", "3", "4"}
    ):
        raise RuntimeError("benchmark profile command changed")
    attack_command = service("attack").get("command")
    if (
        not isinstance(attack_command, list)
        or len(attack_command) != 11
        or attack_command[:4] != ["python", "-m", "locus.attack_runner", "--scenario"]
        or attack_command[4]
        not in {"cross-epoch-runtime-mix-v1", "resolver-unavailable-v1"}
        or attack_command[5:]
        != [
            "--client-root",
            "/var/lib/locus-client",
            "--resolver-url",
            "http://resolver:8080/v1/cues",
            "--restart-checkpoint-dir",
            "/tmp",
        ]
    ):
        raise RuntimeError("attack profile command changed")

    snapshot_collector = service("cloud-snapshot-collector")
    if (
        snapshot_collector.get("networks") != {"cloud": None}
        or snapshot_collector.get("user") != "0:0"
        or snapshot_collector.get("profiles") != ["snapshot-attack"]
        or snapshot_collector.get("cap_add") != ["DAC_READ_SEARCH"]
    ):
        raise RuntimeError("cloud snapshot collector boundary changed")
    collector_environment = snapshot_collector.get("environment")
    if not isinstance(collector_environment, dict) or set(collector_environment) != {
        "LOCUS_S3_ACCESS_KEY",
        "LOCUS_S3_BUCKET",
        "LOCUS_S3_ENDPOINT",
        "LOCUS_S3_PREFIX",
        "LOCUS_S3_SECRET_KEY",
    }:
        raise RuntimeError("cloud snapshot collector credential boundary changed")
    collector_mounts = snapshot_collector.get("volumes")
    if (
        not isinstance(collector_mounts, list)
        or len(collector_mounts) != 2
        or snapshot_collector.get("command")
        != [
            "python",
            "-m",
            "locus.cloud_snapshot",
            "--client-root",
            "/var/lib/locus-client",
            "--snapshot-root",
            "/var/lib/locus-snapshot",
        ]
    ):
        raise RuntimeError("cloud snapshot collector mount/command changed")
    collector_mount_by_target = {
        mount.get("target"): mount for mount in collector_mounts
    }
    if (
        set(collector_mount_by_target)
        != {"/var/lib/locus-client", "/var/lib/locus-snapshot"}
        or collector_mount_by_target["/var/lib/locus-client"].get("source")
        != "client-data"
        or collector_mount_by_target["/var/lib/locus-client"].get("read_only")
        is not True
        or collector_mount_by_target["/var/lib/locus-snapshot"].get("source")
        != "cloud-snapshot-data"
        or collector_mount_by_target["/var/lib/locus-snapshot"].get("read_only") is True
    ):
        raise RuntimeError("cloud snapshot collector mounts changed")

    snapshot_attack = service("cloud-snapshot-attack")
    snapshot_mounts = snapshot_attack.get("volumes")
    if (
        snapshot_attack.get("network_mode") != "none"
        or snapshot_attack.get("networks") not in (None, {})
        or snapshot_attack.get("environment") not in (None, {})
        or snapshot_attack.get("user") != "65532:65532"
        or snapshot_attack.get("profiles") != ["snapshot-attack"]
        or not isinstance(snapshot_mounts, list)
        or len(snapshot_mounts) != 1
        or snapshot_mounts[0].get("source") != "cloud-snapshot-data"
        or snapshot_mounts[0].get("target") != "/var/lib/locus-snapshot"
        or snapshot_mounts[0].get("read_only") is not True
        or snapshot_attack.get("command")
        != [
            "python",
            "-m",
            "locus.attack_runner",
            "--scenario",
            "cloud-snapshot-no-offline-predicate-v1",
            "--snapshot-root",
            "/var/lib/locus-snapshot",
        ]
    ):
        raise RuntimeError("offline cloud snapshot attack boundary changed")

    party_snapshot_collector = service("party-snapshot-collector")
    party_collector_mounts = party_snapshot_collector.get("volumes")
    if (
        party_snapshot_collector.get("network_mode") != "none"
        or party_snapshot_collector.get("networks") not in (None, {})
        or party_snapshot_collector.get("environment") not in (None, {})
        or party_snapshot_collector.get("user") != "0:0"
        or party_snapshot_collector.get("profiles") != ["party-snapshot-attack"]
        or party_snapshot_collector.get("cap_add") != ["DAC_READ_SEARCH"]
        or not isinstance(party_collector_mounts, list)
        or len(party_collector_mounts) != 2
        or party_snapshot_collector.get("command")
        != [
            "python",
            "-m",
            "locus.party_snapshot",
            "--party-root",
            "/var/lib/locus-party",
            "--snapshot-root",
            "/var/lib/locus-party-snapshot",
        ]
    ):
        raise RuntimeError("party snapshot collector boundary changed")
    party_collector_mount_by_target = {
        mount.get("target"): mount for mount in party_collector_mounts
    }
    if (
        set(party_collector_mount_by_target)
        != {"/var/lib/locus-party", "/var/lib/locus-party-snapshot"}
        or party_collector_mount_by_target["/var/lib/locus-party"].get("source")
        != "party1-data"
        or party_collector_mount_by_target["/var/lib/locus-party"].get("read_only")
        is not True
        or party_collector_mount_by_target["/var/lib/locus-party-snapshot"].get(
            "source"
        )
        != "party-snapshot-data"
        or party_collector_mount_by_target["/var/lib/locus-party-snapshot"].get(
            "read_only"
        )
        is True
    ):
        raise RuntimeError("party snapshot collector mounts changed")

    party_snapshot_attack = service("party-snapshot-attack")
    party_snapshot_mounts = party_snapshot_attack.get("volumes")
    if (
        party_snapshot_attack.get("network_mode") != "none"
        or party_snapshot_attack.get("networks") not in (None, {})
        or party_snapshot_attack.get("environment") not in (None, {})
        or party_snapshot_attack.get("user") != "65532:65532"
        or party_snapshot_attack.get("profiles") != ["party-snapshot-attack"]
        or not isinstance(party_snapshot_mounts, list)
        or len(party_snapshot_mounts) != 1
        or party_snapshot_mounts[0].get("source") != "party-snapshot-data"
        or party_snapshot_mounts[0].get("target") != "/var/lib/locus-party-snapshot"
        or party_snapshot_mounts[0].get("read_only") is not True
        or party_snapshot_attack.get("command")
        != [
            "python",
            "-m",
            "locus.attack_runner",
            "--scenario",
            "t-minus-one-party-snapshot-no-offline-predicate-v1",
            "--snapshot-root",
            "/var/lib/locus-party-snapshot",
        ]
    ):
        raise RuntimeError("offline party snapshot attack boundary changed")

    combined_cloud_collector = service("combined-cloud-snapshot-collector")
    combined_cloud_environment = combined_cloud_collector.get("environment")
    combined_cloud_mounts = combined_cloud_collector.get("volumes")
    if (
        combined_cloud_collector.get("networks") != {"cloud": None}
        or combined_cloud_collector.get("user") != "0:0"
        or combined_cloud_collector.get("profiles") != ["combined-snapshot-attack"]
        or combined_cloud_collector.get("cap_add") != ["DAC_READ_SEARCH"]
        or not isinstance(combined_cloud_environment, dict)
        or set(combined_cloud_environment)
        != {
            "LOCUS_S3_ACCESS_KEY",
            "LOCUS_S3_BUCKET",
            "LOCUS_S3_ENDPOINT",
            "LOCUS_S3_PREFIX",
            "LOCUS_S3_SECRET_KEY",
        }
        or not isinstance(combined_cloud_mounts, list)
        or len(combined_cloud_mounts) != 2
        or combined_cloud_collector.get("command")
        != [
            "python",
            "-m",
            "locus.cloud_snapshot",
            "--client-root",
            "/var/lib/locus-client",
            "--snapshot-root",
            "/var/lib/locus-combined/cloud",
        ]
    ):
        raise RuntimeError("combined cloud collector boundary changed")
    combined_cloud_mount_by_target = {
        mount.get("target"): mount for mount in combined_cloud_mounts
    }
    if (
        set(combined_cloud_mount_by_target)
        != {"/var/lib/locus-client", "/var/lib/locus-combined"}
        or combined_cloud_mount_by_target["/var/lib/locus-client"].get("source")
        != "client-data"
        or combined_cloud_mount_by_target["/var/lib/locus-client"].get("read_only")
        is not True
        or combined_cloud_mount_by_target["/var/lib/locus-combined"].get("source")
        != "combined-snapshot-data"
        or combined_cloud_mount_by_target["/var/lib/locus-combined"].get("read_only")
        is True
    ):
        raise RuntimeError("combined cloud collector mounts changed")

    combined_party_collector = service("combined-party-snapshot-collector")
    combined_party_mounts = combined_party_collector.get("volumes")
    if (
        combined_party_collector.get("network_mode") != "none"
        or combined_party_collector.get("networks") not in (None, {})
        or combined_party_collector.get("environment") not in (None, {})
        or combined_party_collector.get("user") != "0:0"
        or combined_party_collector.get("profiles") != ["combined-snapshot-attack"]
        or combined_party_collector.get("cap_add") != ["DAC_READ_SEARCH"]
        or not isinstance(combined_party_mounts, list)
        or len(combined_party_mounts) != 2
        or combined_party_collector.get("command")
        != [
            "python",
            "-m",
            "locus.party_snapshot",
            "--party-root",
            "/var/lib/locus-party",
            "--snapshot-root",
            "/var/lib/locus-combined/party",
        ]
    ):
        raise RuntimeError("combined party collector boundary changed")
    combined_party_mount_by_target = {
        mount.get("target"): mount for mount in combined_party_mounts
    }
    if (
        set(combined_party_mount_by_target)
        != {"/var/lib/locus-party", "/var/lib/locus-combined"}
        or combined_party_mount_by_target["/var/lib/locus-party"].get("source")
        != "party1-data"
        or combined_party_mount_by_target["/var/lib/locus-party"].get("read_only")
        is not True
        or combined_party_mount_by_target["/var/lib/locus-combined"].get("source")
        != "combined-snapshot-data"
        or combined_party_mount_by_target["/var/lib/locus-combined"].get("read_only")
        is True
    ):
        raise RuntimeError("combined party collector mounts changed")

    combined_finalizer = service("combined-snapshot-finalizer")
    combined_finalizer_mounts = combined_finalizer.get("volumes")
    if (
        combined_finalizer.get("network_mode") != "none"
        or combined_finalizer.get("networks") not in (None, {})
        or combined_finalizer.get("environment") not in (None, {})
        or combined_finalizer.get("user") != "0:0"
        or combined_finalizer.get("profiles") != ["combined-snapshot-attack"]
        or combined_finalizer.get("cap_add") not in (None, [])
        or not isinstance(combined_finalizer_mounts, list)
        or len(combined_finalizer_mounts) != 1
        or combined_finalizer_mounts[0].get("source") != "combined-snapshot-data"
        or combined_finalizer_mounts[0].get("target") != "/var/lib/locus-combined"
        or combined_finalizer_mounts[0].get("read_only") is True
        or combined_finalizer.get("command")
        != [
            "python",
            "-m",
            "locus.combined_snapshot",
            "--snapshot-root",
            "/var/lib/locus-combined",
        ]
    ):
        raise RuntimeError("combined snapshot finalizer boundary changed")

    combined_attack = service("combined-snapshot-attack")
    combined_attack_mounts = combined_attack.get("volumes")
    if (
        combined_attack.get("network_mode") != "none"
        or combined_attack.get("networks") not in (None, {})
        or combined_attack.get("environment") not in (None, {})
        or combined_attack.get("user") != "65532:65532"
        or combined_attack.get("profiles") != ["combined-snapshot-attack"]
        or not isinstance(combined_attack_mounts, list)
        or len(combined_attack_mounts) != 1
        or combined_attack_mounts[0].get("source") != "combined-snapshot-data"
        or combined_attack_mounts[0].get("target") != "/var/lib/locus-combined"
        or combined_attack_mounts[0].get("read_only") is not True
        or combined_attack.get("command")
        != [
            "python",
            "-m",
            "locus.attack_runner",
            "--scenario",
            "cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1",
            "--snapshot-root",
            "/var/lib/locus-combined",
        ]
    ):
        raise RuntimeError("offline combined snapshot attack boundary changed")

    resolver = service("resolver")
    if resolver.get("networks") != {"resolver": None}:
        raise RuntimeError("resolver escaped its internal network")
    resolver_mounts = resolver.get("volumes")
    if (
        not isinstance(resolver_mounts, list)
        or len(resolver_mounts) != 1
        or resolver_mounts[0].get("type") != "bind"
        or resolver_mounts[0].get("target") != "/fixtures"
        or resolver_mounts[0].get("read_only") is not True
        or "healthcheck" not in resolver
    ):
        raise RuntimeError("resolver fixture/health boundary changed")

    provisioner = service("provisioner")
    if provisioner.get("network_mode") != "none":
        raise RuntimeError("provisioner must have no network")
    provisioner_mounts = provisioner.get("volumes")
    expected_provisioner_targets = {
        "/party1",
        "/party2",
        "/party3",
        "/party4",
        "/party5",
        "/client",
        "/fixtures",
    }
    if configurable_endpoints:
        expected_provisioner_targets.add("/setup/party-endpoints.json")
    if (
        not isinstance(provisioner_mounts, list)
        or {mount.get("target") for mount in provisioner_mounts}
        != expected_provisioner_targets
    ):
        raise RuntimeError("provisioner volume boundary changed")
    if configurable_endpoints:
        setup_mounts = [
            mount
            for mount in provisioner_mounts
            if mount.get("target") == "/setup/party-endpoints.json"
        ]
        if (
            len(setup_mounts) != 1
            or setup_mounts[0].get("type") != "bind"
            or setup_mounts[0].get("read_only") is not True
        ):
            raise RuntimeError("party endpoint setup mount is not read-only")
    provisioner_capabilities = provisioner.get("cap_add")
    if not isinstance(provisioner_capabilities, list) or set(
        provisioner_capabilities
    ) != {
        "CHOWN",
        "DAC_READ_SEARCH",
        "FOWNER",
    }:
        raise RuntimeError("provisioner capability boundary changed")

    s3 = service("s3")
    expected_s3_image = (
        "chrislusf/seaweedfs:4.29@"
        "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
    )
    if s3.get("image") != expected_s3_image or s3.get("networks") != {"cloud": None}:
        raise RuntimeError("cloud service image/network boundary changed")
    if s3.get("command") != [
        "-alsologtostderr=false",
        "-logdir=/tmp",
        "-stderrthreshold=ERROR",
        "mini",
        "-dir=/data",
    ]:
        raise RuntimeError("cloud service logging boundary changed")
    s3_environment = s3.get("environment")
    if not isinstance(s3_environment, dict) or set(s3_environment) != {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "S3_BUCKET",
    }:
        raise RuntimeError("cloud service credential boundary changed")
    s3_mounts = s3.get("volumes")
    if (
        not isinstance(s3_mounts, list)
        or len(s3_mounts) != 1
        or s3_mounts[0].get("source") != "s3-data"
        or s3_mounts[0].get("target") != "/data"
        or "healthcheck" not in s3
    ):
        raise RuntimeError("cloud service volume/health boundary changed")


def s3_smoke() -> None:
    """Run the backend contract against an ephemeral pinned S3 service."""

    docker = require("docker")
    compose_file = ROOT / "deploy" / "compose.s3.yaml"
    image = (
        "chrislusf/seaweedfs:4.29@"
        "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
    )
    port = _free_loopback_port()
    project = f"locus-s3-smoke-{os.getpid()}-{secrets.token_hex(4)}"
    access_key = f"locus{secrets.token_hex(12)}"
    secret_key = secrets.token_urlsafe(32)
    bucket = "locus-backups"
    environment = os.environ.copy()
    environment.update(
        {
            "LOCUS_S3_ACCESS_KEY": access_key,
            "LOCUS_S3_SECRET_KEY": secret_key,
            "LOCUS_S3_BUCKET": bucket,
            "LOCUS_S3_PORT": str(port),
        }
    )
    compose = [docker, "compose", "-p", project, "-f", str(compose_file)]
    try:
        raw_config = run_capture(
            [*compose, "config", "--format", "json"], env=environment
        )
        configured = json.loads(raw_config)
        if not isinstance(configured, dict):
            raise RuntimeError("Docker Compose returned an invalid configuration")
        _validate_s3_compose(configured, image=image)
        run([*compose, "up", "-d", "--pull", "missing"], env=environment)

        prototype_path = str(ROOT / "prototype")
        if prototype_path not in sys.path:
            sys.path.insert(0, prototype_path)
        from locus.object_store import ObjectNotFound, ObjectStoreUnavailable
        from locus.s3_object_store import S3BackupObjectStore

        store = S3BackupObjectStore.from_credentials(
            bucket=bucket,
            endpoint_url=f"http://127.0.0.1:{port}",
            access_key=access_key,
            secret_key=secret_key,
            prefix="health/probe",
            allow_http=True,
            verify=False,
            timeout_seconds=1.0,
        )
        deadline = time.monotonic() + 60.0
        while True:
            try:
                store.probe()
                break
            except (ObjectNotFound, ObjectStoreUnavailable):
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "S3 smoke service did not become ready"
                    ) from None
                time.sleep(0.25)

        test_environment = environment.copy()
        test_environment.update(
            {
                "LOCUS_RUN_S3_LIVE_TEST": "1",
                "LOCUS_S3_TEST_ENDPOINT": f"http://127.0.0.1:{port}",
                "LOCUS_S3_TEST_BUCKET": bucket,
                "LOCUS_S3_TEST_ACCESS_KEY": access_key,
                "LOCUS_S3_TEST_SECRET_KEY": secret_key,
                "LOCUS_S3_TEST_PREFIX": f"contract/{secrets.token_hex(12)}",
            }
        )
        run(
            [
                PYTHON,
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "prototype/tests",
                "-t",
                "prototype",
                "-p",
                "test_s3_live.py",
            ],
            env=test_environment,
        )
    finally:
        run([*compose, "down", "--volumes", "--remove-orphans"], env=environment)


def _json_result(output: str, *, label: str) -> dict[str, object]:
    lines = [line for line in output.splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError(f"{label} returned no result")
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"{label} returned a non-object result")
    return cast(dict[str, object], result)


def _deployment_result(
    output: str, *, expected_consumed: int, expected_selected: list[int] | None = None
) -> dict[str, object]:
    result = _json_result(output, label="deployment role")
    selected = [1, 3] if expected_selected is None else expected_selected
    if result != {
        "artifact": "LOCUS-compose-deployment-v2",
        "backup_binding": "verified",
        "consumed": expected_consumed,
        "recovery": "verified",
        "selected": selected,
        "status": "ok",
    }:
        raise RuntimeError("deployment recovery result was not exact")
    return result


def _deployment_output_exposures(
    text: str, *, access_key: str, secret_key: str
) -> list[str]:
    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.redaction import exposed_categories

    return exposed_categories(
        text,
        {
            "access-key": access_key,
            "cue-email": "fixture.friend@example.org",
            "cue-latitude-1": "49.59875",
            "cue-latitude-2": "49.61160",
            "cue-latitude-3": "49.62610",
            "cue-longitude-1": "6.13445",
            "cue-longitude-2": "6.13190",
            "cue-longitude-3": "6.12750",
            "cue-phone-1": "+352621123456",
            "cue-phone-2": "+33123456789",
            "private-key": "BEGIN PRIVATE KEY",
            "secret-key": secret_key,
            "signer-key-field": '"signer_private_key"',
            "tpass-state-field": '"state"',
        },
    )


def _run_cross_epoch_attack_profile(
    *,
    docker: str,
    compose: list[str],
    environment: dict[str, str],
    project: str,
) -> str:
    """Restart one activated party at the lifecycle runner's safe checkpoint."""

    container_name = f"{project}-lifecycle-attack"
    ready_path = "/tmp/locus-lifecycle-restart-ready"
    complete_path = "/tmp/locus-lifecycle-restart-complete"
    run_capture(
        [
            *compose,
            "run",
            "-d",
            "--name",
            container_name,
            "--no-deps",
            "attack",
        ],
        env=environment,
    )
    try:
        deadline = time.monotonic() + 120.0
        while True:
            probe = subprocess.run(
                [
                    docker,
                    "exec",
                    container_name,
                    "python",
                    "-c",
                    (
                        "from pathlib import Path; "
                        f"raise SystemExit(0 if Path({ready_path!r}).is_file() else 1)"
                    ),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            if probe.returncode == 0:
                break
            running = run_capture(
                [docker, "inspect", "--format", "{{.State.Running}}", container_name]
            ).strip()
            if running != "true":
                raise RuntimeError("lifecycle attack exited before restart checkpoint")
            if time.monotonic() >= deadline:
                raise RuntimeError("lifecycle restart checkpoint timed out")
            time.sleep(0.2)

        run([*compose, "restart", "party1"], env=environment)
        _wait_service_healthy(docker, compose, environment, "party1")
        run(
            [
                docker,
                "exec",
                container_name,
                "python",
                "-c",
                f"from pathlib import Path; Path({complete_path!r}).touch()",
            ]
        )
        status = run_capture([docker, "wait", container_name]).strip()
        output = run_capture([docker, "logs", container_name])
        if status not in {"0", "1"}:
            raise RuntimeError("lifecycle attack profile failed")
        return output
    finally:
        subprocess.run(
            [docker, "rm", "-f", container_name],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )


def _deployment_profile_output(
    *, profile: str, service: str, extra_environment: dict[str, str]
) -> str:
    """Run one isolated Compose profile and return only its redacted result."""

    docker = require("docker")
    compose_file = ROOT / "deploy" / "compose.yaml"
    project = f"locus-{profile}-{os.getpid()}-{secrets.token_hex(4)}"
    reference_image = "locus-reference:profile"
    access_key = f"locus{secrets.token_hex(12)}"
    secret_key = secrets.token_urlsafe(32)
    environment = os.environ.copy()
    environment.update(
        {
            "LOCUS_REFERENCE_IMAGE": reference_image,
            "LOCUS_S3_ACCESS_KEY": access_key,
            "LOCUS_S3_SECRET_KEY": secret_key,
            "LOCUS_S3_BUCKET": "locus-backups",
            "LOCUS_S3_PREFIX": f"{profile}/{secrets.token_hex(12)}",
            **extra_environment,
        }
    )
    compose = [
        docker,
        "compose",
        "-p",
        project,
        "-f",
        str(compose_file),
        "--profile",
        profile,
    ]
    output = ""
    auxiliary_output = ""
    try:
        raw_config = run_capture(
            [*compose, "--profile", "*", "config", "--format", "json"],
            env=environment,
        )
        configured = json.loads(raw_config)
        if not isinstance(configured, dict):
            raise RuntimeError("Docker Compose returned an invalid profile graph")
        _validate_deployment_compose(configured, reference_image=reference_image)
        run([*compose, "build", "--pull", "provisioner"], env=environment)
        run(
            [
                *compose,
                "up",
                "-d",
                "--pull",
                "missing",
                "--wait",
                "--wait-timeout",
                "180",
                "s3",
                "resolver",
                "party1",
                "party2",
                "party3",
                "party4",
                "party5",
            ],
            env=environment,
        )
        if profile == "snapshot-attack":
            auxiliary_output += run_capture(
                [*compose, "run", "--rm", "--no-deps", "client"],
                env=environment,
            )
            auxiliary_output += run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "cloud-snapshot-collector",
                ],
                env=environment,
            )
            output = run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "cloud-snapshot-attack",
                ],
                env=environment,
            )
        elif profile == "party-snapshot-attack":
            auxiliary_output += run_capture(
                [*compose, "run", "--rm", "--no-deps", "client"],
                env=environment,
            )
            run([*compose, "stop", "party1"], env=environment)
            auxiliary_output += run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "party-snapshot-collector",
                ],
                env=environment,
            )
            output = run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "party-snapshot-attack",
                ],
                env=environment,
            )
        elif profile == "combined-snapshot-attack":
            auxiliary_output += run_capture(
                [*compose, "run", "--rm", "--no-deps", "client"],
                env=environment,
            )
            run([*compose, "stop", "party1"], env=environment)
            auxiliary_output += run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "combined-cloud-snapshot-collector",
                ],
                env=environment,
            )
            auxiliary_output += run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "combined-party-snapshot-collector",
                ],
                env=environment,
            )
            auxiliary_output += run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "combined-snapshot-finalizer",
                ],
                env=environment,
            )
            output = run_capture(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "combined-snapshot-attack",
                ],
                env=environment,
            )
        elif (
            profile == "attack"
            and extra_environment.get("LOCUS_ATTACK_SCENARIO")
            == "cross-epoch-runtime-mix-v1"
        ):
            output = _run_cross_epoch_attack_profile(
                docker=docker,
                compose=compose,
                environment=environment,
                project=project,
            )
        else:
            output = run_capture(
                [*compose, "run", "--rm", "--no-deps", service], env=environment
            )
        logs = run_capture([*compose, "logs", "--no-color"], env=environment)
        exposed = _deployment_output_exposures(
            logs + auxiliary_output + output,
            access_key=access_key,
            secret_key=secret_key,
        )
        if exposed:
            raise RuntimeError(
                "deployment profile output contains prohibited categories: "
                + ", ".join(exposed)
            )
        return output
    except subprocess.CalledProcessError:
        diagnostic = run_capture(
            [*compose, "logs", "--no-color", "provisioner"], env=environment
        )
        if diagnostic:
            exposed = _deployment_output_exposures(
                diagnostic, access_key=access_key, secret_key=secret_key
            )
            if exposed:
                print(
                    "provisioner diagnostic suppressed; prohibited categories: "
                    + ", ".join(exposed),
                    file=sys.stderr,
                )
            else:
                print(diagnostic, file=sys.stderr)
        raise
    finally:
        run([*compose, "down", "--volumes", "--remove-orphans"], env=environment)


def _emit_profile_evidence(
    *,
    result: dict[str, object],
    profile: str,
    experiment_id: str,
    evidence_class: str,
    configuration: dict[str, object],
    started_at: str,
    finished_at: str,
    output_path: Path | None,
    host_id: str | None,
    randomness_kind: str = "os-csprng",
    seed: int | None = None,
) -> None:
    """Attach exact host-side provenance and optionally retain immutable output."""

    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.experiment_metadata import collect_experiment_metadata
    from locus.profile_evidence import (
        build_profile_evidence,
        serialize_profile_evidence,
        write_profile_evidence,
    )

    metadata = collect_experiment_metadata(
        repo_root=ROOT,
        experiment_id=experiment_id,
        profile=profile,
        evidence_class=evidence_class,
        configuration=configuration,
        randomness_kind=randomness_kind,
        seed=seed,
        started_at=started_at,
        finished_at=finished_at,
        output_path=output_path,
        host_id=host_id,
    )
    payload = build_profile_evidence(
        metadata=metadata,
        result=result,
    )
    serialized = serialize_profile_evidence(payload)
    if output_path is not None:
        write_profile_evidence(
            repo_root=ROOT,
            output_path=output_path,
            evidence=payload,
        )
    print(serialized.decode("ascii"), end="")


def deployment_demo() -> None:
    output = _deployment_profile_output(
        profile="demo", service="demo", extra_environment={}
    )
    result = _deployment_result(output, expected_consumed=1)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


def deployment_benchmark(args: argparse.Namespace) -> None:
    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.deployment import validate_benchmark_result
    from locus.experiment_metadata import utc_timestamp

    started_at = utc_timestamp()
    output = _deployment_profile_output(
        profile="benchmark",
        service="benchmark",
        extra_environment={"LOCUS_BENCHMARK_RUNS": str(args.runs)},
    )
    finished_at = utc_timestamp()
    result = validate_benchmark_result(
        _json_result(output, label="deployment benchmark")
    )
    _emit_profile_evidence(
        result=result,
        profile="compose-benchmark",
        experiment_id=args.experiment_id,
        evidence_class=args.evidence_class,
        configuration={
            "runs": args.runs,
            "selected": [1, 3],
            "threshold": 2,
            "topology": "same-host-compose-5-party-v1",
        },
        started_at=started_at,
        finished_at=finished_at,
        output_path=args.out,
        host_id=args.host_id,
    )


def deployment_attack(args: argparse.Namespace) -> None:
    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.attack_runner import validate_attack_report
    from locus.experiment_metadata import utc_timestamp

    started_at = utc_timestamp()
    snapshot_profiles = {
        "cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1": (
            "combined-snapshot-attack",
            "combined-snapshot-attack",
        ),
        "cloud-snapshot-no-offline-predicate-v1": (
            "snapshot-attack",
            "cloud-snapshot-attack",
        ),
        "t-minus-one-party-snapshot-no-offline-predicate-v1": (
            "party-snapshot-attack",
            "party-snapshot-attack",
        ),
    }
    snapshot_profile = snapshot_profiles.get(args.scenario)
    output = _deployment_profile_output(
        profile=snapshot_profile[0] if snapshot_profile else "attack",
        service=snapshot_profile[1] if snapshot_profile else "attack",
        extra_environment=(
            {} if snapshot_profile else {"LOCUS_ATTACK_SCENARIO": args.scenario}
        ),
    )
    finished_at = utc_timestamp()
    result = validate_attack_report(_json_result(output, label="attack runner"))
    if result["status"] != "passed":
        print(
            json.dumps(result, sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
        )
        raise RuntimeError("attack scenario did not match its registered result")
    _emit_profile_evidence(
        result=result,
        profile="compose-attack",
        experiment_id=args.experiment_id,
        evidence_class=args.evidence_class,
        configuration={
            "scenario": args.scenario,
            "topology": "same-host-compose-5-party-v1",
        },
        started_at=started_at,
        finished_at=finished_at,
        output_path=args.out,
        host_id=args.host_id,
    )


def _performance_project_is_removed(docker: str, project: str) -> None:
    """Require exact-label cleanup of one disposable performance project."""

    checks = (
        [
            docker,
            "ps",
            "-aq",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        [
            docker,
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        [
            docker,
            "network",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
    )
    if any(run_capture(command).strip() for command in checks):
        raise RuntimeError("disposable performance project cleanup was incomplete")


def _performance_cloud_object_bytes(result: dict[str, object]) -> int:
    """Return the one exact canonical cloud-object size shared by all samples."""

    samples = result.get("samples")
    if not isinstance(samples, list):
        raise RuntimeError("performance result has no samples")
    sizes: set[int] = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise RuntimeError("performance sample is malformed")
        application_bytes = sample.get("application_bytes")
        if not isinstance(application_bytes, dict):
            raise RuntimeError("performance byte metric is malformed")
        cloud = application_bytes.get("cloud")
        if not isinstance(cloud, dict):
            raise RuntimeError("performance cloud metric is malformed")
        received = cloud.get("received")
        if not isinstance(received, int) or isinstance(received, bool) or received <= 0:
            raise RuntimeError("performance cloud-object size is invalid")
        sizes.add(received)
    if len(sizes) != 1:
        raise RuntimeError("canonical cloud-object size changed within a scenario")
    return sizes.pop()


def _build_performance_reference_image() -> tuple[str, str]:
    """Build the reference image under one stable Compose project identity."""

    docker = require("docker")
    compose_file = ROOT / "deploy" / "compose.yaml"
    project = "locus-performance-image-v2"
    reference_image = "locus-reference:performance-v2"
    environment = os.environ.copy()
    environment.update(
        {
            "LOCUS_REFERENCE_IMAGE": reference_image,
            "LOCUS_S3_ACCESS_KEY": "locus-performance-build",
            "LOCUS_S3_SECRET_KEY": "locus-performance-build-placeholder",
            "LOCUS_S3_BUCKET": "locus-backups",
            "LOCUS_S3_PREFIX": "performance/build",
        }
    )
    compose = [docker, "compose", "-p", project, "-f", str(compose_file)]
    configured = json.loads(
        run_capture(
            [*compose, "--profile", "*", "config", "--format", "json"],
            env=environment,
        )
    )
    if not isinstance(configured, dict):
        raise RuntimeError("Docker Compose returned an invalid performance graph")
    _validate_deployment_compose(configured, reference_image=reference_image)
    run([*compose, "build", "--pull", "provisioner"], env=environment)
    image_id = run_capture(
        [
            docker,
            "image",
            "inspect",
            "--format",
            "{{.Id}}",
            reference_image,
        ]
    ).strip()
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise RuntimeError("performance reference image has no canonical identity")
    return reference_image, image_id


def _performance_scenario_result(
    *,
    block: int,
    orchestration_seed: int,
    scenario_position: int,
    scenario_id: str,
    reference_image: str,
    reference_image_id: str,
) -> dict[str, object]:
    """Run one frozen scenario in a fresh exact-label disposable project."""

    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.deployment import (
        PERFORMANCE_RESULT_VERSION,
        validate_performance_client_result,
        validate_performance_result,
        validate_provision_metric,
        validate_storage_metric,
    )

    docker = require("docker")
    compose_file = ROOT / "deploy" / "compose.yaml"
    project = f"locus-perf-b{block}-{os.getpid()}-{secrets.token_hex(4)}"
    access_key = f"locus{secrets.token_hex(12)}"
    secret_key = secrets.token_urlsafe(32)
    environment = os.environ.copy()
    environment.update(
        {
            "LOCUS_REFERENCE_IMAGE": reference_image,
            "LOCUS_S3_ACCESS_KEY": access_key,
            "LOCUS_S3_SECRET_KEY": secret_key,
            "LOCUS_S3_BUCKET": "locus-backups",
            "LOCUS_S3_PREFIX": f"performance/{secrets.token_hex(12)}",
        }
    )
    compose = [docker, "compose", "-p", project, "-f", str(compose_file)]
    party_roots = [
        item
        for party_id in range(1, 6)
        for item in ("--party-root", f"/party{party_id}")
    ]
    provision_command = [
        "python",
        "-m",
        "locus.deployment",
        "provision",
        *party_roots,
        "--client-root",
        "/client",
        "--fixture",
        "/fixtures/cues.json",
        "--owner-uid",
        "65532",
        "--owner-gid",
        "65532",
        "--measure",
    ]
    storage_command = [
        "python",
        "-m",
        "locus.deployment",
        "storage-metric",
        *party_roots,
        "--client-root",
        "/client",
    ]
    performance_command = [
        "python",
        "-m",
        "locus.deployment",
        "performance",
        "--client-root",
        "/var/lib/locus-client",
        "--resolver-url",
        "http://resolver:8080/v1/cues",
        "--scenario",
        scenario_id,
        "--runs",
        "3",
    ]
    orchestration_started = time.perf_counter()
    provision_metric: dict[str, object] | None = None
    storage_before: dict[str, object] | None = None
    storage_after: dict[str, object] | None = None
    client_result: dict[str, object] | None = None
    runtime: dict[str, object] | None = None
    captured_outputs: list[str] = []
    try:
        raw_config = run_capture(
            [*compose, "--profile", "*", "config", "--format", "json"],
            env=environment,
        )
        configured = json.loads(raw_config)
        if not isinstance(configured, dict):
            raise RuntimeError("Docker Compose returned an invalid performance graph")
        _validate_deployment_compose(configured, reference_image=reference_image)
        runtime = {
            "compose_version": run_capture(
                [docker, "compose", "version", "--short"]
            ).strip(),
            "docker_engine_version": run_capture(
                [docker, "version", "--format", "{{.Server.Version}}"]
            ).strip(),
            "reference_image_id": reference_image_id,
            "s3_image": (
                "chrislusf/seaweedfs:4.29@"
                "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
            ),
        }

        provision_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "provisioner", *provision_command],
            env=environment,
        )
        captured_outputs.append(provision_output)
        provision_metric = validate_provision_metric(
            _json_result(provision_output, label="performance provisioner")
        )
        run(
            [
                *compose,
                "up",
                "-d",
                "--pull",
                "missing",
                "--wait",
                "--wait-timeout",
                "180",
                "s3",
                "resolver",
                "party1",
                "party2",
                "party3",
                "party4",
                "party5",
            ],
            env=environment,
        )

        before_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "provisioner", *storage_command],
            env=environment,
        )
        captured_outputs.append(before_output)
        storage_before = validate_storage_metric(
            _json_result(before_output, label="pre-scenario storage metric")
        )

        warmup_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "client"], env=environment
        )
        captured_outputs.append(warmup_output)
        _deployment_result(warmup_output, expected_consumed=1)
        if scenario_id == "recover-one-party-unavailable-v1":
            run([*compose, "stop", "party1"], env=environment)

        performance_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "client", *performance_command],
            env=environment,
        )
        captured_outputs.append(performance_output)
        client_result = validate_performance_client_result(
            _json_result(performance_output, label="performance client")
        )

        run(
            [
                *compose,
                "stop",
                "party1",
                "party2",
                "party3",
                "party4",
                "party5",
            ],
            env=environment,
        )
        after_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "provisioner", *storage_command],
            env=environment,
        )
        captured_outputs.append(after_output)
        storage_after = validate_storage_metric(
            _json_result(after_output, label="post-scenario storage metric")
        )

        logs = run_capture([*compose, "logs", "--no-color"], env=environment)
        exposed = _deployment_output_exposures(
            logs + "".join(captured_outputs),
            access_key=access_key,
            secret_key=secret_key,
        )
        if exposed:
            raise RuntimeError(
                "performance output contains prohibited categories: "
                + ", ".join(exposed)
            )
    finally:
        run([*compose, "down", "--volumes", "--remove-orphans"], env=environment)
        _performance_project_is_removed(docker, project)

    if (
        provision_metric is None
        or storage_before is None
        or storage_after is None
        or client_result is None
        or runtime is None
    ):
        raise RuntimeError("performance scenario did not produce complete metrics")
    result = {
        "artifact": PERFORMANCE_RESULT_VERSION,
        "block": block,
        "cleanup": "passed",
        "configuration": {
            "alternate_selected": [2, 3],
            "authorization_membership": 5,
            "authorization_quorum": 4,
            "baseline_selected": [1, 3],
            "measurements": 3,
            "threshold": 2,
            "topology": "same-host-compose-5-party-v1",
            "tpass_parties": 3,
            "warmups": 1,
        },
        "enrollment_latency_ms": provision_metric["latency_ms"],
        "orchestration_latency_ms": (time.perf_counter() - orchestration_started)
        * 1000,
        "orchestration_seed": orchestration_seed,
        "output_scan": "passed",
        "profile": "performance",
        "runtime": runtime,
        "samples": client_result["samples"],
        "scenario_position": scenario_position,
        "scenario_id": scenario_id,
        "status": "ok",
        "storage": {
            "after": storage_after,
            "before": storage_before,
            "cloud_object_bytes": _performance_cloud_object_bytes(client_result),
        },
    }
    return validate_performance_result(result)


def deployment_performance_block(args: argparse.Namespace) -> None:
    """Run one deterministic three-scenario development or paper block."""

    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.deployment import performance_scenario_order
    from locus.experiment_metadata import utc_timestamp

    if args.evidence_class == "paper" and args.out_dir is None:
        raise RuntimeError("paper performance evidence requires --out-dir")
    reference_image, reference_image_id = _build_performance_reference_image()
    scenario_order = performance_scenario_order(args.seed)
    for scenario_position, scenario_id in enumerate(scenario_order, start=1):
        started_at = utc_timestamp()
        result = _performance_scenario_result(
            block=args.block,
            orchestration_seed=args.seed,
            scenario_position=scenario_position,
            scenario_id=scenario_id,
            reference_image=reference_image,
            reference_image_id=reference_image_id,
        )
        finished_at = utc_timestamp()
        output_path = (
            None if args.out_dir is None else args.out_dir / f"{scenario_id}.json"
        )
        _emit_profile_evidence(
            result=result,
            profile="compose-performance",
            experiment_id=args.experiment_id,
            evidence_class=args.evidence_class,
            configuration={
                "block": args.block,
                "orchestration_seed": args.seed,
                "scenario": scenario_id,
                "scenario_position": scenario_position,
                "topology": "same-host-compose-5-party-v1",
            },
            started_at=started_at,
            finished_at=finished_at,
            output_path=output_path,
            host_id=args.host_id,
            randomness_kind="orchestrator-prng-v1",
            seed=args.seed,
        )


def process_performance(args: argparse.Namespace) -> None:
    """Validate and deterministically process the complete retained corpus."""

    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.performance_processing import (
        PerformanceProcessingError,
        process_performance_corpus,
        read_processed_performance,
        serialize_processed_performance,
        write_processed_performance,
    )

    raw_root = args.raw_dir
    if not raw_root.is_absolute():
        raw_root = ROOT / raw_root
    output_path = args.out
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    try:
        processed = process_performance_corpus(
            repo_root=ROOT,
            raw_root=raw_root,
            bootstrap_seed=args.bootstrap_seed,
            bootstrap_resamples=args.bootstrap_resamples,
        )
        if args.verify:
            _retained, existing = read_processed_performance(output_path)
            regenerated = serialize_processed_performance(processed)
            if existing != regenerated:
                raise PerformanceProcessingError(
                    "processed performance output differs from regenerated bytes"
                )
            print(
                json.dumps(
                    {
                        "artifact": processed["artifact"],
                        "inputs": len(processed["source"]["inputs"]),
                        "output": output_path.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(existing).hexdigest(),
                        "status": "verified",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return
        write_processed_performance(
            repo_root=ROOT,
            output_path=output_path,
            processed=processed,
        )
    except PerformanceProcessingError as exc:
        raise SystemExit(f"Performance processing failed: {exc}") from exc
    print(
        json.dumps(
            {
                "artifact": processed["artifact"],
                "inputs": len(processed["source"]["inputs"]),
                "output": output_path.relative_to(ROOT).as_posix(),
                "status": "created",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def generate_performance_paper(args: argparse.Namespace) -> None:
    """Generate versioned LaTeX rows from one canonical processed artifact."""

    prototype_path = str(ROOT / "prototype")
    if prototype_path not in sys.path:
        sys.path.insert(0, prototype_path)
    from locus.performance_paper import (
        PerformancePaperError,
        build_performance_paper_inputs,
        write_performance_paper_inputs,
    )
    from locus.performance_processing import (
        PerformanceProcessingError,
        read_processed_performance,
    )

    input_path = args.input
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    output_dir = args.out_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    try:
        processed, source_bytes = read_processed_performance(input_path)
        source_path = input_path.resolve().relative_to(ROOT.resolve()).as_posix()
        manifest, outputs = build_performance_paper_inputs(
            processed=processed,
            source_path=source_path,
            source_bytes=source_bytes,
        )
        status = write_performance_paper_inputs(
            repo_root=ROOT,
            output_dir=output_dir,
            manifest=manifest,
            outputs=outputs,
            replace=args.replace,
        )
    except (PerformancePaperError, PerformanceProcessingError, ValueError) as exc:
        raise SystemExit(f"Performance paper generation failed: {exc}") from exc
    print(
        json.dumps(
            {
                "artifact": manifest["artifact"],
                "input": source_path,
                "output": output_dir.resolve().relative_to(ROOT.resolve()).as_posix(),
                "status": status,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _wait_service_healthy(
    docker: str,
    compose: list[str],
    environment: dict[str, str],
    service: str,
) -> None:
    deadline = time.monotonic() + 90.0
    while True:
        container_id = run_capture(
            [*compose, "ps", "-q", service], env=environment
        ).strip()
        if container_id:
            status = run_capture(
                [
                    docker,
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    container_id,
                ],
                env=environment,
            ).strip()
            if status == "healthy":
                return
            if status == "unhealthy":
                raise RuntimeError(f"deployment service is unhealthy: {service}")
        if time.monotonic() >= deadline:
            raise RuntimeError(f"deployment service did not become healthy: {service}")
        time.sleep(0.5)


def _inspect_deployment_runtime(
    docker: str,
    compose: list[str],
    environment: dict[str, str],
) -> None:
    """Verify live mounts, networks, users, ports, dumps, and credentials."""

    def core_dumps_disabled(inspected: dict[str, object]) -> bool:
        host_config = inspected.get("HostConfig")
        if not isinstance(host_config, dict):
            return False
        limits = host_config.get("Ulimits")
        return (
            isinstance(limits, list)
            and {
                "Hard": 0,
                "Name": "core",
                "Soft": 0,
            }
            in limits
        )

    for party_id in range(1, 6):
        service = f"party{party_id}"
        container_id = run_capture(
            [*compose, "ps", "-q", service], env=environment
        ).strip()
        inspected = json.loads(
            run_capture([docker, "inspect", container_id], env=environment)
        )[0]
        networks = set(inspected["NetworkSettings"]["Networks"])
        mounts = inspected["Mounts"]
        runtime_environment = inspected["Config"]["Env"]
        if (
            not inspected["HostConfig"]["ReadonlyRootfs"]
            or inspected["Config"]["User"] != "65532:65532"
            or len(networks) != 1
            or not next(iter(networks)).endswith("_recovery")
            or len(mounts) != 1
            or mounts[0]["Destination"] != "/var/lib/locus"
            or not mounts[0]["Name"].endswith(f"_party{party_id}-data")
            or any(
                value.startswith(("AWS_", "LOCUS_S3_")) for value in runtime_environment
            )
            or inspected["HostConfig"]["PortBindings"] not in (None, {})
            or not core_dumps_disabled(inspected)
        ):
            raise RuntimeError(f"live party role boundary failed: {service}")

    for service, network_suffix, target in (
        ("resolver", "_resolver", "/fixtures"),
        ("s3", "_cloud", "/data"),
    ):
        container_id = run_capture(
            [*compose, "ps", "-q", service], env=environment
        ).strip()
        inspected = json.loads(
            run_capture([docker, "inspect", container_id], env=environment)
        )[0]
        networks = set(inspected["NetworkSettings"]["Networks"])
        mounts = inspected["Mounts"]
        if (
            not inspected["HostConfig"]["ReadonlyRootfs"]
            or len(networks) != 1
            or not next(iter(networks)).endswith(network_suffix)
            or len(mounts) != 1
            or mounts[0]["Destination"] != target
            or inspected["HostConfig"]["PortBindings"] not in (None, {})
            or not core_dumps_disabled(inspected)
        ):
            raise RuntimeError(f"live service role boundary failed: {service}")


def _deployment_smoke(*, configurable_endpoints: bool) -> None:
    """Build and exercise one exact isolated same-host deployment profile."""

    docker = require("docker")
    compose_files = [ROOT / "deploy" / "compose.yaml"]
    if configurable_endpoints:
        compose_files.append(ROOT / "deploy" / "compose.party-endpoints.yaml")
    project = f"locus-deployment-smoke-{os.getpid()}-{secrets.token_hex(4)}"
    reference_image = "locus-reference:artifact-smoke"
    access_key = f"locus{secrets.token_hex(12)}"
    secret_key = secrets.token_urlsafe(32)
    environment = os.environ.copy()
    environment.update(
        {
            "LOCUS_REFERENCE_IMAGE": reference_image,
            "LOCUS_S3_ACCESS_KEY": access_key,
            "LOCUS_S3_SECRET_KEY": secret_key,
            "LOCUS_S3_BUCKET": "locus-backups",
            "LOCUS_S3_PREFIX": f"deployment/{secrets.token_hex(12)}",
        }
    )
    if configurable_endpoints:
        environment.setdefault(
            "LOCUS_PARTY_ENDPOINT_SETUP",
            str(ROOT / "deploy" / "party-endpoints.json"),
        )
    compose = [docker, "compose", "-p", project]
    for compose_file in compose_files:
        compose.extend(["-f", str(compose_file)])
    party_roots = [
        item
        for party_id in range(1, 6)
        for item in ("--party-root", f"/party{party_id}")
    ]
    try:
        raw_config = run_capture(
            [*compose, "--profile", "*", "config", "--format", "json"],
            env=environment,
        )
        configured = json.loads(raw_config)
        if not isinstance(configured, dict):
            raise RuntimeError("Docker Compose returned an invalid deployment")
        _validate_deployment_compose(
            configured,
            reference_image=reference_image,
            configurable_endpoints=configurable_endpoints,
        )
        run([*compose, "build", "--pull", "provisioner"], env=environment)
        run(
            [
                *compose,
                "up",
                "-d",
                "--pull",
                "missing",
                "--wait",
                "--wait-timeout",
                "180",
                "s3",
                "resolver",
                "party1",
                "party2",
                "party3",
                "party4",
                "party5",
            ],
            env=environment,
        )
        audit_output = run_capture(
            [
                *compose,
                "run",
                "--rm",
                "--no-deps",
                "provisioner",
                "python",
                "-m",
                "locus.deployment",
                "audit",
                *party_roots,
                "--client-root",
                "/client",
            ],
            env=environment,
        )
        audit_lines = [
            line for line in audit_output.splitlines() if line.startswith("{")
        ]
        if not audit_lines or json.loads(audit_lines[-1]) != {
            "client_has_party_secrets": False,
            "party_count": 5,
            "party_states_distinct": True,
            "status": "ok",
            "version": "LOCUS-compose-deployment-v2",
        }:
            raise RuntimeError("deployment snapshot audit failed")
        first_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "client"], env=environment
        )
        _deployment_result(first_output, expected_consumed=1)
        _inspect_deployment_runtime(docker, compose, environment)

        run([*compose, "restart", "party1"], env=environment)
        _wait_service_healthy(docker, compose, environment, "party1")
        second_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "client"], env=environment
        )
        _deployment_result(second_output, expected_consumed=2)

        run([*compose, "stop", "party1"], env=environment)
        third_output = run_capture(
            [*compose, "run", "--rm", "--no-deps", "client"], env=environment
        )
        _deployment_result(third_output, expected_consumed=3, expected_selected=[2, 3])

        logs = run_capture([*compose, "logs", "--no-color"], env=environment)
        collected_output = logs + first_output + second_output + third_output
        exposed = _deployment_output_exposures(
            collected_output, access_key=access_key, secret_key=secret_key
        )
        if exposed:
            raise RuntimeError(
                "deployment output contains prohibited categories: "
                + ", ".join(exposed)
            )
    except subprocess.CalledProcessError:
        diagnostic = run_capture(
            [*compose, "logs", "--no-color", "provisioner"], env=environment
        )
        if diagnostic:
            exposed = _deployment_output_exposures(
                diagnostic, access_key=access_key, secret_key=secret_key
            )
            if exposed:
                print(
                    "provisioner diagnostic suppressed; prohibited categories: "
                    + ", ".join(exposed),
                    file=sys.stderr,
                )
            else:
                print(diagnostic, file=sys.stderr)
        raise
    finally:
        run([*compose, "down", "--volumes", "--remove-orphans"], env=environment)


def deployment_smoke() -> None:
    """Build and exercise the frozen isolated same-host deployment."""

    _deployment_smoke(configurable_endpoints=False)


def deployment_configurable_smoke() -> None:
    """Exercise five local containers through the public endpoint setup."""

    _deployment_smoke(configurable_endpoints=True)


def _profile_runs(value: str) -> int:
    try:
        runs = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("runs must be an integer") from exc
    if not 1 <= runs <= 4:
        raise argparse.ArgumentTypeError("runs must be between 1 and 4")
    return runs


def _ui_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("UI port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("UI port must be between 1 and 65535")
    return port


def _performance_block(value: str) -> int:
    try:
        block = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("block must be an integer") from exc
    if not 1 <= block <= 10:
        raise argparse.ArgumentTypeError("block must be between 1 and 10")
    return block


def _uint64(value: str) -> int:
    try:
        seed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seed must be an integer") from exc
    if not 0 <= seed <= 2**64 - 1:
        raise argparse.ArgumentTypeError("seed must be an unsigned 64-bit integer")
    return seed


def _bootstrap_resamples(value: str) -> int:
    try:
        resamples = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "bootstrap resamples must be an integer"
        ) from exc
    if not 1_000 <= resamples <= 100_000:
        raise argparse.ArgumentTypeError(
            "bootstrap resamples must be between 1000 and 100000"
        )
    return resamples


def _add_profile_evidence_arguments(
    parser: argparse.ArgumentParser, *, default_experiment_id: str
) -> None:
    parser.add_argument(
        "--evidence-class", choices=("development", "paper"), default="development"
    )
    parser.add_argument("--experiment-id", default=default_experiment_id)
    parser.add_argument("--host-id")
    parser.add_argument("--out", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run reproducible LOCUS development tasks."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("test", help="run Python and Rust unit tests")
    subparsers.add_parser("check", help="run formatting, lint, typing, and unit checks")
    subparsers.add_parser("format", help="format Python and apply safe lint fixes")
    subparsers.add_parser("native", help="build the local Rust Python extension")
    subparsers.add_parser("smoke", help="run tests and both local demos")
    subparsers.add_parser(
        "s3-smoke",
        help="run the backup-store contract against an ephemeral local S3 service",
    )
    subparsers.add_parser(
        "deployment-smoke",
        help="build and exercise the complete isolated local deployment",
    )
    subparsers.add_parser(
        "deployment-configurable-smoke",
        help="run five local party containers through the configurable endpoint file",
    )
    subparsers.add_parser(
        "integrated-config",
        help="validate the exact P7.5 manifest and both resolved Compose graphs",
    )
    integrated_start_parser = subparsers.add_parser(
        "integrated-start",
        help="start the P7.5 integrated system with one ephemeral client role",
    )
    integrated_start_parser.add_argument(
        "--mode", choices=("enrollment", "recovery"), default="enrollment"
    )
    integrated_start_parser.add_argument("--project", default="locus-integrated")
    integrated_start_parser.add_argument("--port", type=_ui_port, default=8765)
    integrated_stop_parser = subparsers.add_parser(
        "integrated-stop", help="stop or destroy one exact P7.5 project"
    )
    integrated_stop_parser.add_argument("--project", default="locus-integrated")
    integrated_stop_parser.add_argument("--port", type=_ui_port, default=8765)
    integrated_stop_parser.add_argument(
        "--destroy",
        action="store_true",
        help="also remove exact project volumes and image",
    )
    subparsers.add_parser(
        "integrated-smoke",
        help="run the disposable P7.5 UI-to-services acceptance smoke",
    )
    subparsers.add_parser(
        "deployment-demo",
        help="run recovery through the isolated Compose demo profile",
    )
    deployment_benchmark_parser = subparsers.add_parser(
        "deployment-benchmark",
        help="measure complete recoveries through the Compose benchmark profile",
    )
    deployment_benchmark_parser.add_argument("--runs", type=_profile_runs, default=2)
    _add_profile_evidence_arguments(
        deployment_benchmark_parser, default_experiment_id="compose-benchmark"
    )
    deployment_attack_parser = subparsers.add_parser(
        "deployment-attack",
        help="run one registered scenario through the Compose attack profile",
    )
    deployment_attack_parser.add_argument(
        "--scenario",
        choices=(
            "cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1",
            "cloud-snapshot-no-offline-predicate-v1",
            "cross-epoch-runtime-mix-v1",
            "resolver-unavailable-v1",
            "t-minus-one-party-snapshot-no-offline-predicate-v1",
        ),
        default="resolver-unavailable-v1",
    )
    _add_profile_evidence_arguments(
        deployment_attack_parser, default_experiment_id="compose-attack"
    )
    deployment_performance_parser = subparsers.add_parser(
        "deployment-performance-block",
        help="run one frozen three-scenario Compose performance block",
    )
    deployment_performance_parser.add_argument(
        "--block", type=_performance_block, required=True
    )
    deployment_performance_parser.add_argument("--seed", type=_uint64, required=True)
    deployment_performance_parser.add_argument(
        "--evidence-class", choices=("development", "paper"), default="development"
    )
    deployment_performance_parser.add_argument(
        "--experiment-id", default="compose-performance-v2"
    )
    deployment_performance_parser.add_argument("--host-id")
    deployment_performance_parser.add_argument("--out-dir", type=Path)
    performance_process_parser = subparsers.add_parser(
        "process-performance",
        help="validate and process the complete retained performance corpus",
    )
    performance_process_parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("experiments/raw/performance-v2"),
    )
    performance_process_parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/processed/performance-v2/summary.json"),
    )
    performance_process_parser.add_argument(
        "--bootstrap-seed",
        type=_uint64,
        default=20260723,
    )
    performance_process_parser.add_argument(
        "--bootstrap-resamples",
        type=_bootstrap_resamples,
        default=10_000,
    )
    performance_process_parser.add_argument(
        "--verify",
        action="store_true",
        help="compare regenerated canonical bytes with the existing output",
    )
    performance_paper_parser = subparsers.add_parser(
        "generate-performance-paper",
        help="generate versioned LaTeX rows from processed performance data",
    )
    performance_paper_parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/processed/performance-v2/summary.json"),
    )
    performance_paper_parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("paper/generated/performance-v2"),
    )
    performance_paper_parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing complete generated bundle",
    )
    subparsers.add_parser(
        "artifact-smoke",
        help="run checks, tests, demos, and one unsaved benchmark sample",
    )
    artifact_package_parser = subparsers.add_parser(
        "artifact-package",
        help="audit or build the deterministic anonymous artifact archive",
    )
    artifact_package_parser.add_argument(
        "--check",
        action="store_true",
        help="audit the current allowlist without creating an archive",
    )
    artifact_package_parser.add_argument(
        "--out",
        type=Path,
        default=Path("dist/LOCUS-anonymous-artifact-v2.zip"),
    )
    artifact_package_parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing archive after all release gates pass",
    )
    subparsers.add_parser(
        "attempt-model",
        help="explore the bounded attempt-control model and emit its strict report",
    )
    subparsers.add_parser(
        "walkthrough",
        help="run the synthetic-only in-process educational walkthrough",
    )
    ui_parser = subparsers.add_parser(
        "ui",
        help="run the local no-persistence research UI",
    )
    ui_parser.add_argument(
        "--host", choices=("127.0.0.1", "::1", "localhost"), default="127.0.0.1"
    )
    ui_parser.add_argument("--port", type=_ui_port, default=8765)

    demo_parser = subparsers.add_parser("demo", help="run the local Python demo")
    demo_parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="arguments forwarded to run_demo.py"
    )

    benchmark_parser = subparsers.add_parser(
        "benchmark", help="run scaffold benchmarks without implied paper provenance"
    )
    benchmark_parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="arguments forwarded to run_benchmarks.py",
    )
    return parser


def forwarded_args(raw: Sequence[str]) -> list[str]:
    """Return arguments intended for a demo or benchmark child command."""

    forwarded = list(raw)
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    return forwarded


def main() -> int:
    parser = build_parser()
    if sys.argv[1:2] and sys.argv[1] in {"demo", "benchmark"}:
        try:
            forwarded = forwarded_args(sys.argv[2:])
            if sys.argv[1] == "demo":
                demo(forwarded)
            else:
                benchmark(forwarded)
        except subprocess.CalledProcessError as error:
            return error.returncode
        return 0

    args = parser.parse_args()
    try:
        if args.command == "test":
            test()
        elif args.command == "check":
            check()
        elif args.command == "format":
            format_sources()
        elif args.command == "native":
            native_build()
        elif args.command == "smoke":
            smoke()
        elif args.command == "s3-smoke":
            s3_smoke()
        elif args.command == "deployment-smoke":
            deployment_smoke()
        elif args.command == "deployment-configurable-smoke":
            deployment_configurable_smoke()
        elif args.command == "integrated-config":
            integrated_config()
        elif args.command == "integrated-start":
            integrated_start(args)
        elif args.command == "integrated-stop":
            integrated_stop(args)
        elif args.command == "integrated-smoke":
            integrated_smoke()
        elif args.command == "deployment-demo":
            deployment_demo()
        elif args.command == "deployment-benchmark":
            deployment_benchmark(args)
        elif args.command == "deployment-attack":
            deployment_attack(args)
        elif args.command == "deployment-performance-block":
            deployment_performance_block(args)
        elif args.command == "process-performance":
            process_performance(args)
        elif args.command == "generate-performance-paper":
            generate_performance_paper(args)
        elif args.command == "artifact-smoke":
            artifact_smoke()
        elif args.command == "artifact-package":
            artifact_package(args)
        elif args.command == "attempt-model":
            attempt_model()
        elif args.command == "walkthrough":
            walkthrough()
        elif args.command == "ui":
            research_ui(args)
        elif args.command in {"demo", "benchmark"}:
            raise AssertionError("forwarded command was not dispatched early")
        else:  # pragma: no cover - argparse enforces the command choices.
            raise AssertionError(f"Unhandled command: {args.command}")
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
