# Managed Flow Evidence Profile v1

Status: Complete. Assigned by owner-approved D027 and collected once from a
clean committed source state.

The seven identifiers assigned by D027 are the managed-flow evidence profile,
trace policy, fixed scenario manifest, Yi/aPPSS/common result families, and
corpus manifest recorded in `VERSION-REGISTRY.md`. The canonical scenario
manifest is `managed-flow-scenarios-v1.json`: NF01--NF06 run once for each of
the four matched arms (12 Yi and 12 aPPSS reports), while NF07--NF12 produce
six managed-common reports, exactly 30 in total.

Evidence mode adds only payload-free observations at the synthetic browser
driver, Manager and Client route adapters, mutually authenticated RPC caller
and server adapters, the storage gateway's logical provider boundary, and the
controller's constrained Docker Engine adapter. It adds no service, network,
volume, socket, mount, endpoint, or protocol route. Operational health traffic
and repeated shutdown-readiness polling have no scenario context and are
excluded. The actual system-stop request and resulting controller/Docker
operations remain observed. Packet capture is prohibited.
Before an evidence-mode self-destruction removes a Client, the controller uses
a bounded three-second observation-drain delay so the Client's final
payload-free event can be read in memory. Normal managed operation keeps its
existing delay; lifecycle result semantics are unchanged, and no duration is
retained.

Transient events contain a boot pseudonym, sequence, scenario context,
sender/receiver roles, fixed category, application request/response body-byte
counts, result class, and observation side. Events are scanned, deduplicated,
sequence-checked, and discarded. RPC and browser observations must reconcile
across sender and receiver; provider and Docker use their fixed available
observation boundaries. Retained contacts contain only aggregate
roles/categories/counts/body bytes/result classes/reconciliation plus public
provenance digests, pseudonymous project/host/client/package-set identifiers,
fixed absences, controls, cleanup, safety status, and limitations.

The collector fails the whole run and publishes nothing for an unknown edge or
category, prohibited browser/service or UI/Docker contact, Client/Manager or
Client/provider contact, resolver contact in a NoResolver arm, observation
mismatch, sequence gap, byte-bound failure, output finding, incomplete
scenario membership, or incomplete cleanup. Positive controls exercise those
detectors, a fictional output marker, allowed Manager/controller and
Client/controller calls, and the live isolation probes.

Exploratory execution writes no retained output. `--retain` requires a clean
source commit, rebuilds and validates the exact D025 graph, and atomically
publishes all 30 canonical reports or none at
`evidence/retained/managed-flow-v1/`. An existing target is never overwritten.

The sole v1 retained run completed on 2026-08-17 from source commit
`cd5aaaf762a9b18bef681f496f704f772fe6e9be`. It published exactly 12 Yi,
12 aPPSS, and six common reports. The canonical corpus manifest closes them
with `corpus_sha256`
`1deb49fcf5a7550f16da28702d1364ce20603f573d872cf811f631d331cf842c`.

This is same-host, single-operator application-boundary implementation
evidence. It is not packet-level evidence, a timing/performance corpus,
cryptographic proof, multi-host or independent-administration evidence,
real-provider evidence, production-security assurance, or manuscript
authorization. The managed UI does not expose successor lifecycle operations.

The pre-retention exploratory gate corrected one implementation-to-registry
mismatch discovered by NF05: the managed client now dispatches
`LOCUS-location-person-set-v1` through its registered
`LOCUS-deterministic-directory-v1` remote resolver profile. Both 3-of-5 arms
must observe that contact; both canonical-email 2-of-3 arms must observe none.
