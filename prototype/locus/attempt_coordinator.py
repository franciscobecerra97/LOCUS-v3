"""Untrusted collector for LOCUS attempt and freshness certificates."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .attempt_certificates import (
    AttemptEntry,
    AuthorizationCertificate,
    AuthorizerConfig,
    AuthorizerSigner,
    EntryVote,
    FreshnessRequest,
    FreshnessVote,
    InstallVote,
    PrepareCertificate,
    ResponseFreshnessCertificate,
)
from .party_store import Conflict, PartyStore, PartyStoreError


class CoordinatorError(Exception):
    """The collector could not safely assemble or reconcile a quorum."""


class CoordinatorUnavailable(CoordinatorError):
    """The configured quorum did not respond before the operation deadline."""


_Result = TypeVar("_Result")


@dataclass(frozen=True)
class AuthorizerState:
    status: dict[str, int | str]
    next_slot_lock: str | None
    installed_certificate: AuthorizationCertificate | None


class AuthorizerPeer(Protocol):
    """Minimum signed-ledger boundary used by an untrusted coordinator."""

    @property
    def party_id(self) -> int: ...

    def state_summary(self, bid: str, epoch: int, sid: str) -> AuthorizerState: ...

    def create_entry_vote(
        self, entry: AttemptEntry, config: AuthorizerConfig
    ) -> EntryVote: ...

    def create_install_vote(
        self, prepare: PrepareCertificate, config: AuthorizerConfig
    ) -> InstallVote: ...

    def install_certificate(
        self, certificate: AuthorizationCertificate, config: AuthorizerConfig
    ) -> None: ...

    def create_freshness_vote(
        self, request: FreshnessRequest, config: AuthorizerConfig
    ) -> FreshnessVote: ...


@dataclass(frozen=True)
class AuthorizerNode:
    """In-process implementation of the authorizer peer boundary."""

    store: PartyStore
    signer: AuthorizerSigner

    @property
    def party_id(self) -> int:
        return self.signer.party_id

    def state_summary(self, bid: str, epoch: int, sid: str) -> AuthorizerState:
        return AuthorizerState(
            status=self.store.status(bid, epoch),
            next_slot_lock=self.store.next_slot_lock(bid, epoch),
            installed_certificate=self.store.installed_certificate(bid, epoch, sid),
        )

    def create_entry_vote(
        self, entry: AttemptEntry, config: AuthorizerConfig
    ) -> EntryVote:
        return self.store.create_entry_vote(entry, config, self.signer)

    def create_install_vote(
        self, prepare: PrepareCertificate, config: AuthorizerConfig
    ) -> InstallVote:
        return self.store.create_install_vote(prepare, config, self.signer)

    def install_certificate(
        self, certificate: AuthorizationCertificate, config: AuthorizerConfig
    ) -> None:
        self.store.install_certificate(certificate, config)

    def create_freshness_vote(
        self, request: FreshnessRequest, config: AuthorizerConfig
    ) -> FreshnessVote:
        return self.store.create_freshness_vote(request, config, self.signer)


class AttemptCoordinator:
    """Collect signatures without holding an authorizer key of its own."""

    def __init__(
        self,
        *,
        config: AuthorizerConfig,
        nodes: list[AuthorizerPeer],
        operation_timeout_seconds: float = 45.0,
        phase_timeout_seconds: float | None = None,
    ) -> None:
        config.validate()
        node_ids = [node.party_id for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            raise CoordinatorError("duplicate authorizer nodes")
        if any(node_id not in config.public_keys for node_id in node_ids):
            raise CoordinatorError("unknown authorizer node")
        if (
            isinstance(operation_timeout_seconds, bool)
            or not isinstance(operation_timeout_seconds, (int, float))
            or not 0 < operation_timeout_seconds <= 120
        ):
            raise CoordinatorError("invalid coordinator operation timeout")
        selected_phase_timeout = (
            min(10.0, float(operation_timeout_seconds))
            if phase_timeout_seconds is None
            else phase_timeout_seconds
        )
        if (
            isinstance(selected_phase_timeout, bool)
            or not isinstance(selected_phase_timeout, (int, float))
            or not 0 < selected_phase_timeout <= operation_timeout_seconds
        ):
            raise CoordinatorError("invalid coordinator phase timeout")
        self.config = config
        self.nodes = sorted(nodes, key=lambda node: node.party_id)
        self.operation_timeout_seconds = float(operation_timeout_seconds)
        self.phase_timeout_seconds = float(selected_phase_timeout)

    def _collect_quorum(
        self,
        operation: Callable[[AuthorizerPeer], _Result],
        *,
        deadline: float,
        label: str,
    ) -> list[tuple[AuthorizerPeer, _Result]]:
        """Collect one quorum concurrently without weakening conflict handling."""

        executor = ThreadPoolExecutor(
            max_workers=max(1, len(self.nodes)), thread_name_prefix="locus-authorizer"
        )
        futures: dict[Future[_Result], AuthorizerPeer] = {
            executor.submit(operation, node): node for node in self.nodes
        }
        results: list[tuple[AuthorizerPeer, _Result]] = []
        try:
            remaining = min(
                self.phase_timeout_seconds, max(0.0, deadline - time.monotonic())
            )
            completed, _ = wait(futures, timeout=remaining)
            for future in completed:
                node = futures[future]
                try:
                    result = future.result()
                except Conflict:
                    raise
                except PartyStoreError:
                    continue
                except Exception as exc:
                    raise CoordinatorError(f"unexpected {label} peer failure") from exc
                results.append((node, result))
        finally:
            for future in futures:
                if not future.done():
                    future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
        if len(results) < self.config.quorum:
            raise CoordinatorUnavailable(f"insufficient {label} quorum")
        return sorted(results, key=lambda item: item[0].party_id)

    def state_summaries(
        self, bid: str, epoch: int, sid: str
    ) -> list[tuple[int, AuthorizerState]]:
        """Return one deadline-bounded quorum of authenticated state summaries."""

        deadline = time.monotonic() + self.operation_timeout_seconds
        results = self._collect_quorum(
            lambda node: node.state_summary(bid, epoch, sid),
            deadline=deadline,
            label="state-summary",
        )
        return [(node.party_id, summary) for node, summary in results]

    def _reconcile_entry(
        self, entry: AttemptEntry, *, deadline: float
    ) -> AuthorizationCertificate | None:
        entry.validate()
        installed: list[AuthorizationCertificate] = []
        matching_heads = 0
        observed_locks: set[str] = set()
        summaries = self._collect_quorum(
            lambda node: node.state_summary(entry.bid, entry.epoch, entry.sid),
            deadline=deadline,
            label="state-summary",
        )
        for _, summary in summaries:
            certificate = summary.installed_certificate
            if certificate is not None:
                certificate.verify(self.config)
                if certificate.prepare.entry.entry_hash != entry.entry_hash:
                    raise Conflict("session identifier has a conflicting certificate")
                installed.append(certificate)
            status = summary.status
            if (
                status["installed_index"] == entry.log_index - 1
                and status["installed_head"] == entry.previous_head
                and status["consumed"] == entry.resulting_consumed - 1
                and status["budget"] == entry.effective_budget
            ):
                matching_heads += 1
            lock = summary.next_slot_lock
            if lock is not None:
                observed_locks.add(lock)
        if installed:
            first = installed[0]
            if any(
                certificate.certificate_hash != first.certificate_hash
                for certificate in installed[1:]
            ):
                raise CoordinatorError("conflicting installed certificates")
            self._collect_quorum(
                lambda node: node.install_certificate(first, self.config),
                deadline=deadline,
                label="certificate-reconciliation",
            )
            return first
        if len(observed_locks) > 1 or (
            observed_locks and entry.entry_hash not in observed_locks
        ):
            raise Conflict("next ledger slot is locked for another entry")
        if matching_heads < self.config.quorum:
            raise CoordinatorError("insufficient matching head summaries")
        return None

    def authorize(self, entry: AttemptEntry) -> AuthorizationCertificate:
        """Reconcile, resume, or assemble one exact two-phase certificate."""

        deadline = time.monotonic() + self.operation_timeout_seconds
        installed = self._reconcile_entry(entry, deadline=deadline)
        if installed is not None:
            return installed
        entry_votes = [
            vote
            for _, vote in self._collect_quorum(
                lambda node: node.create_entry_vote(entry, self.config),
                deadline=deadline,
                label="durable-entry-vote",
            )
        ]
        prepare = PrepareCertificate.create(entry, entry_votes, self.config)

        install_votes = [
            vote
            for _, vote in self._collect_quorum(
                lambda node: node.create_install_vote(prepare, self.config),
                deadline=deadline,
                label="durable-install-vote",
            )
        ]
        certificate = AuthorizationCertificate.create(
            prepare, install_votes, self.config
        )
        self._collect_quorum(
            lambda node: node.install_certificate(certificate, self.config),
            deadline=deadline,
            label="authorization-install",
        )
        return certificate

    def certify_freshness(
        self,
        *,
        authorization: AuthorizationCertificate,
        responding_party_id: int,
        boot_nonce: str,
        response_nonce: str,
    ) -> ResponseFreshnessCertificate:
        authorization.verify(self.config)
        entry = authorization.prepare.entry
        request = FreshnessRequest(
            bid=entry.bid,
            epoch=entry.epoch,
            config_digest=entry.config_digest,
            authorization_hash=authorization.certificate_hash,
            request_digest=entry.request_digest,
            responding_party_id=responding_party_id,
            phase="commitment",
            boot_nonce=boot_nonce,
            response_nonce=response_nonce,
        )
        deadline = time.monotonic() + self.operation_timeout_seconds
        votes = [
            vote
            for _, vote in self._collect_quorum(
                lambda node: node.create_freshness_vote(request, self.config),
                deadline=deadline,
                label="live-freshness-vote",
            )
        ]
        return ResponseFreshnessCertificate.create(request, votes, self.config)
