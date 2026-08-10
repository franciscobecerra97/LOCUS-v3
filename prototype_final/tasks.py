"""Five-command executor for the final integrated LOCUS prototype."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
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
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
INTEGRATED_COMPOSE = ROOT / "deploy" / "compose.integrated.yaml"
INTEGRATED_MANIFEST = ROOT / "deploy" / "integrated-manifest.json"


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


def _integrated_environment(project: str, port: int) -> dict[str, str]:
    environment = os.environ.copy()
    seed = hashlib.sha256(f"LOCUS integrated local {project}".encode()).hexdigest()
    environment.update(
        {
            "LOCUS_INTEGRATED_IMAGE": "locus-integrated-reference-final:local",
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
    source_path = str(ROOT)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
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


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _ui_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("UI port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("UI port must be between 1 and 65535")
    return port


def integrated_check() -> None:
    """Run the focused quality/native gate for this isolated implementation."""

    sources = [ROOT / "tasks.py", *sorted((ROOT / "locus").rglob("*.py"))]
    sources.extend(sorted((ROOT / "tests").rglob("*.py")))
    for source in sources:
        ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    print(f"Parsed {len(sources)} Python files successfully.")
    run([PYTHON, "-m", "ruff", "format", "--check", "tasks.py", "locus", "tests"])
    run([PYTHON, "-m", "ruff", "check", "tasks.py", "locus", "tests"])
    run([PYTHON, "-m", "mypy", "tasks.py", "locus", "tests"])
    for manifest in (
        "appss-core/Cargo.toml",
        "tpass-core/Cargo.toml",
        "tpass-python/Cargo.toml",
    ):
        cargo = require("cargo")
        run([cargo, "fmt", "--manifest-path", manifest, "--", "--check"])
        run(
            [
                cargo,
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
    native_build()
    run([PYTHON, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."])
    for manifest in (
        "appss-core/Cargo.toml",
        "tpass-core/Cargo.toml",
        "tpass-python/Cargo.toml",
    ):
        run([require("cargo"), "test", "--locked", "--manifest-path", manifest])


def build_integrated_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operate the final integrated LOCUS reference prototype."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "integrated-check", help="run focused Python and native quality checks"
    )
    subparsers.add_parser(
        "integrated-config", help="validate the manifest and resolved graphs"
    )
    start = subparsers.add_parser(
        "integrated-start", help="start the service plane and one client role"
    )
    start.add_argument(
        "--mode", choices=("enrollment", "recovery"), default="enrollment"
    )
    start.add_argument("--project", default="locus-integrated-final")
    start.add_argument("--port", type=_ui_port, default=8765)
    stop = subparsers.add_parser(
        "integrated-stop", help="stop or destroy one exact integrated project"
    )
    stop.add_argument("--project", default="locus-integrated-final")
    stop.add_argument("--port", type=_ui_port, default=8765)
    stop.add_argument(
        "--destroy",
        action="store_true",
        help="also remove exact project volumes and the local image",
    )
    subparsers.add_parser(
        "integrated-smoke", help="run the disposable UI-to-services acceptance gate"
    )
    return parser


def main() -> int:
    parser = build_integrated_parser()
    args = parser.parse_args()
    try:
        if args.command == "integrated-check":
            integrated_check()
        elif args.command == "integrated-config":
            integrated_config()
        elif args.command == "integrated-start":
            integrated_start(args)
        elif args.command == "integrated-stop":
            integrated_stop(args)
        elif args.command == "integrated-smoke":
            integrated_smoke()
        else:  # pragma: no cover - argparse enforces the command choices.
            raise AssertionError(f"Unhandled command: {args.command}")
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
