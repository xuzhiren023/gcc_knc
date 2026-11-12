# Host/card transfers on the Windows host and 7120P

S11-01, 2026-11-12. Status: host validation and staging; **no new card measurements**.
S11-02 owns production integration. No driver, MPSS setting, module, MTU, mount,
`/etc` file, harness code, or other project's files were changed.

## Decision pending the exclusive card turn

Keep authenticated SSH for control. Batch small artifacts into one guarded stream.
Evaluate bounded SCIF writes for bulk data in **both** directions, with raw TCP
as the intermediate candidate and SSH as the established fallback. Do not enable
automatic DMA retry after an integrity error, host bugcheck, or uncertain cleanup.
There is insufficient evidence to name a universally fastest or safest bulk path.

PhiChat's successful upload is evidence for that upload implementation, not for
reverse DMA, a different driver workload, or overlapping production assembly.
PhiWeather's crash is evidence of a host kernel failure during the attempt, not
proof that DMA reads, buffer registration, or a particular MPSS driver caused it.

## Evidence and reproducibility

References used for facts, without copying implementation or vendor prose:

* **PC**: [PhiChat transfer notes](</C:/Users/xuzhi/Documents/PhiChat/docs/SCIF-TRANSFER.md>),
  including the separately labelled 1.6.13 and 1.6.14 behavior and measurements.
* **PW**: [PhiWeather plan](</C:/Users/xuzhi/Documents/PhiWeather/PLAN.md:1446>),
  [reuse analysis](</C:/Users/xuzhi/Documents/PhiWeather/native/translation/SCIF_TRANSPORT_REUSE.md>),
  [recovery report](</C:/Users/xuzhi/Documents/PhiWeather/native/translation/L8_REBOOT_RECOVERY_20261027.md:47>),
  and the report's referenced
  `artifacts/test-state/link-smoke-20261027/reboot-recovery/interruption.json`.
* **PW-code**: read-only inspection of `scripts/KncDmaTransport.py:69-160`,
  `scripts/Assemble-KncWrfProduction791Dma.py:180-218`,
  `native/transport/ScifReceive.cs:148-192`, and
  `native/transport/scif_sender.c:116-133` under PhiWeather. These distinguish
  the prepared adapter from what the damaged execution record can establish.
* **SDK**: installed `C:/Program Files/Intel/MPSS/sdk/include/scif.h` declarations
  and API contracts: connection 334-598, messages 601-731, registration 734-890,
  mapping 894-1022, RMA 1026-1379, fences 1382-1519, node enumeration 1522-1547.
  Its K1OM counterpart and libraries are in `k1om-mpss-linux/usr`.
  `C:/Windows/System32/uSCIF.dll` reports **3.7.53857.1**. Inspection of its
  import/export table found all the tested SCIF entry points and MSVCR110.
  This was file inspection, not a SCIF connection or DMA operation.
* **SCIF guide**: Intel SCIF User Guide rev. 1.0, October 2012, sections 3.3-3.6
  ([publisher-authored document, university mirror](https://didawiki.cli.di.unipi.it/lib/exe/fetch.php/magistraleinformaticanetworking/spm/knc_scif_userguide.pdf)).
  Installed SDK contracts take precedence over this older architectural guide.
* **MPSS guide**: Intel Windows User's Guide, document 330077-001US, rev. 3.8,
  sections 7-8, pages 28-30
  ([publisher-authored document, mirror](https://manuals.plus/m/ce3b332d6a2842c7e7cc5ba36a4aace74bffc1ed0a41dc644b668d5802c179c2)).
  This later guide establishes the Windows product features, not the exact
  configuration of the installed 3.7 system.
* **COI**: installed `docs/coi/release_notes.txt` (3.7 and earlier release entries),
  `sdk/include/intel-coi/source/COIBuffer_source.h` and `COIProcess_source.h`,
  `sdk/lib/coi_host.lib`, and card-side `usr/lib64/libcoi_device.so.0`.
* **SSH**: [OpenSSH option contracts](https://man.openbsd.org/ssh_config.5),
  and this project's [card runner contract](../card-run.md). Remote algorithm
  availability must come from the actual daemon, not this current manual.
* **Crash**: [Microsoft's 0x7E interpretation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x7e--system-thread-exception-not-handled).
  **Hash**: [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final),
  sections 4.1.2, 4.2.2, 5 and 6.2, implemented independently in C.

The ticket specifies MPSS 3.7.1 on the card. The installed `mic0.xml` gives
host `192.168.1.99`, card `192.168.1.100`, subnet `255.255.255.0`; these are
configuration facts, not a fresh connectivity observation. The engineer's
`Get-NetIPInterface` query was denied by the host. **Current MTU and card sshd
offers remain unobserved.** The lead runner records a read-only daemon/MTU
probe in the admitted turn. No guessed algorithm list or default MTU is presented
as observed fact.

## Inventory

All candidates below support host-to-card and card-to-host payloads in principle.
Availability is separated from an established operational path.

| Method | Availability and appropriate use | Limits and cost | Failure and cleanup |
| --- | --- | --- | --- |
| SSH stream | Existing pinned-key path in `card_run`; commands, bootstrap, stdout and stderr. One full-duplex child session can frame repeated transfers. | Encryption and network copies consume CPU. No SCIF registration; bounded application buffers. Our current pack protocol caps staging through `maxStageMiB`; that is a harness policy, not an SSH size limit. | Deadline, EOF, auth failure, remote exit. Keep boot/path guards; remove only owned incomplete files. Never replay a command after an ambiguous result. |
| SCP | Existing Windows client and card program, conditional on the selected protocol. The runner requests legacy SCP with `-O`, not SFTP. | File IO, process startup, SSH crypto, metadata and per-file operations. Large files require 64-bit lengths and enough destination filesystem space. | Partial destination after disconnect; subprocess exit is insufficient to publish a file without exact length/integrity. Use a private `.part`, then atomic publication in S11-02. |
| Tar over SSH | Packs many files into one SSH byte stream in either direction. Small socket/C tools avoid any dependence on netcat. | Tar framing, disk/RAM filesystem writes, crypto. Compression only helps compressible inputs. The card filesystem uses RAM; never create a second multi-GB archive there. | Pipeline failures must propagate (`pipefail`); reject unsafe archive paths/symlinks and excess bytes. The benchmark archive contains only its own fixed `payload.bin`; production must keep `claude-unpack`'s validation. |
| Raw TCP over virtual Ethernet | Ordinary sockets over the already configured mic network. No new service or adapter configuration. An authenticated SSH launch supplies a per-session nonce and endpoint. | Kernel/network copies; MTU may affect packet overhead. Keep the existing MTU; record both ends. No application pinned-memory quota; bounded send/receive buffers still consume memory. No encryption on this path. | Connection reset, short read/write, firewall refusal and timeouts. Close sockets; discard partial data. A nonce binds the experiment to its SSH launch but does not encrypt an observable network. |
| SCIF messages | `scif_send`/`scif_recv`, Windows `uSCIF.dll` and card `libscif.so.0`. Either side can listen or connect. | Byte-count API takes `int`; split into bounded messages and handle partial progress. Kernel queues/backpressure rather than explicit user RMA windows. Probe availability before bulk use. | Peer reset, device loss, resource exhaustion; check every return. Close endpoints on termination; never infer EOF from a successful short message. |
| Registered SCIF writes | `scif_register` + `scif_writeto`. A host sender or card sender can push into the other's registered destination. | Page-aligned address and registration length; 64-bit offsets, separate registered address space. Pinned pages remain live until release. Use bounded reusable windows, not a 1-GiB registration. Registration/copy cost must be reported separately from payload throughput. | Invalid offset/length/permission, pin failure, peer loss, incomplete async DMA, teardown races. Synchronous completion plus receiver acknowledgement before reuse/unregister; exact length and digest before publication. |
| Registered SCIF reads | `scif_readfrom`: receiver pulls remote source into its local window. Both initiating sides are possible. | Same registration requirements; remote source must remain unchanged through receiver completion. PCIe read behavior can differ substantially from writes; do not extrapolate upload speed. | A sender releasing a source window too soon is particularly dangerous. Explicit ready/completed handshake, synchronous operation, no source reuse before acknowledgement. |
| Virtual-address SCIF writes | `scif_vwriteto`: local pointer instead of a pre-registered local offset; remote destination still registered. Both directions. | Implicit local pin/mapping work can add overhead. `SCIF_RMA_USECACHE` changes lifetime/caching behavior; the benchmark leaves it off. Our allocation remains alive through synchronous completion. | Implicit registration failures and stale mappings if lifetime is mishandled. No free/realloc during the operation, no cached mapping reuse. Experimental until actual trials pass. |
| SCIF remote mapping | `scif_mmap`/`scif_munmap`, present in installed Windows exports and card API. A receiving CPU can copy from a peer's registered source. | This is CPU access to a remote mapping, **not proof of DMA throughput**. Page-aligned mapping, remote lifetime and access permissions apply; BAR/aperture and driver resources may limit usable mappings. | Mapping failure, peer reset, invalid access after unregister. Map only the bounded advertised window, unmap before acknowledging completion. Actual platform/direction viability is still untested. |
| COI buffers | Windows host library and card runtime are installed. `COIBufferWrite`, `COIBufferRead`, `COIBufferCopy`, map/unmap and events provide offload-process buffers; host initiates work. | Runtime owns coherence and extra copies; 64-bit sizes do not guarantee allocations succeed. Installed release notes say COI pinned-buffer support was removed in 3.7, and older streaming buffer types were removed earlier. Do not design around those obsolete flags. | Event errors, sink/process loss and authentication failure; wait for outstanding operations, unmap buffers, destroy buffers and the owned COI process. This introduces an offload process/lifecycle beyond the current SSH harness. |
| `micnativeloadex` | Installed Windows executable; uses COI to load native programs and resolve/copy dependencies. Useful for an offload application, not a general bidirectional file-sync interface. | Library search and COI authentication/runtime requirements. It launches a program rather than merely copying an arbitrary result file back. | Dependency/load/daemon errors; owned offload process cleanup. No transparent substitute for `card_run`'s lease, affinity, boot guards and watchdog. |
| NFS | MPSS Windows guide describes a Windows **Server** NFS share. A card can read/write an already mounted share. No existing permitted share has been established here. | Network server and mount/coherence semantics; no application RMA registration. Windows 10 is not evidence of an installed NFS server role. | Stale handles/server loss/partial files. Installing a server or mounting/reconfiguring the card would violate this ticket's no-change boundary. Not a runnable candidate without evidence of an existing share. |
| virtio / higher layers | Virtual Ethernet already supplies the TCP path. No installed, configured virtio shared filesystem or host block export was established. Installed ibscif libraries alone do not establish a usable Windows verbs stack. | Device provisioning, driver/backend and guest configuration would be needed for an unconfigured service. | These are not additional zero-change file-transfer methods in this inventory. Do not install or enable them for this study. |

SDK-specific registration facts: let the driver choose offsets; do not assume an
offset is a CPU pointer. With fixed offsets, the installed SDK documents a usable
range below 2^62. The study uses at most 64 MiB per endpoint, rounds registration
length to 4096 bytes, and bounds all offsets/lengths. This is a **chosen budget**,
not an asserted MPSS maximum. Actual page-lock capacity depends on host/card
memory and driver resources; allocation/registration failure stops the run.
Both read and write permissions are currently requested for the reusable study
buffer; production should narrow permissions by direction.

SSH experiments must choose the intersection of the client and actual sshd
offers. `ssh -Q` describes the client only. Record `sshd -T` (and, if unsupported,
the peer proposal in `ssh -vv` during the lead's admitted turn). Candidate
comparisons are AES-CTR with an offered SHA-2 MAC and an offered AEAD cipher;
AEAD carries its own authentication rather than a separately chosen MAC.
Do not disable authentication, select obsolete algorithms to win a benchmark,
or change server configuration. Compression on/off is a separate experiment;
the synthetic mixed-byte input deliberately provides little compression gain.
Use real compressible suite/source data before applying compression by default.

ControlMaster/ControlPersist are OpenSSH multiplexing mechanisms, but support in
the installed native Windows client is not assumed. The implemented `pipe` case
uses one persistent SSH process for twenty transfers and is usable without a
control socket. Parallel `pipe`/TCP/SCIF groups use two independent sessions only
after serial trials; they show contention as well as aggregate opportunity.
Do not claim two-stream aggregate bandwidth by adding unrelated serial medians.

Licensing: use installed MPSS libraries, never redistribute Intel headers, DLLs,
shared libraries, samples or docs. The installed SDK header identifies a restricted
Intel agreement; the installation has `EULA.rtf`, `COPYING.rtf` and a separate
sample-code agreement. Those are separate from our implementation's source.
Dynamic loading uses the existing Windows system DLL / card SONAME. The new C
declarations contain only needed ABI facts; code, protocol, SHA implementation
and test are original. No ICC headers, SVML, libimf, XML, ISPC code or Intel sample
implementation was used. OpenSSH/tar/system networking are invoked in place;
none of their binaries is bundled either. Intel and Xeon Phi are trademarks of
Intel Corporation or its subsidiaries.

## What differs between PhiChat and PhiWeather

| Dimension | PhiChat documented implementation | PhiWeather prepared attempt | What is actually known |
| --- | --- | --- | --- |
| Direction | Established Windows-to-card `scif_writeto` upload. | Upload uses unchanged PhiChat helpers; new protocol 3 download makes Windows call synchronous `scif_readfrom`. | PW recovery says the reverse pair has no completed native transfer evidence. Do not locate the crash in a particular direction from that fact alone. |
| Buffers | Host: two reusable page-aligned 64-MiB buffers. Earlier receiver: successive file-backed windows. 1.6.14: two reusable 64-MiB receive buffers plus eight copy workers. | Reverse pair: one registered 64-MiB host receive allocation; one card anonymous source window, filled from a file. Tails rounded to 64 bytes and checked by exact byte count. | These are different versions and directions, not evidence that PhiWeather pinned an entire multi-GB file. |
| Lifetime | Synchronous completion before reuse; receiver completion endpoint stays open until host consumes its acknowledgement. | Reverse sender waits for each read acknowledgement, unregisters/unmaps, sends terminal status, then waits for disconnect. Windows finally unregisters/closes/releases. | A normal-path lifetime bug is not established by this inspection. |
| Concurrency | Protocol 2 overlaps disk reading/registration; depth 1 is an available comparison. Later receiver uses eight copy workers; thirty-two were slower. | Adapter waits for a transfer's helpers. The production assembly pipeline could impose different card/host load; exact active assembly count at crash is unknown. | The crash record says execution counts and in-flight logs are damaged. Do not invent a concurrency count. |
| Failure handling | Cleanup-confirmed SCP fallback; uncertain cleanup, Stop and identity/thermal errors do not retry. | 900-second transfer deadline; finally force-kills a still-running Windows helper, closes card helper stdin, waits 30 seconds, retains scope if termination is unresolved. Reverse helper ignores unregister return values in finally. | Abrupt host teardown is a concrete difference to investigate; no evidence yet says that finally path ran before the bugcheck. |
| Workload | Inference/model or image uploads with resident-worker heartbeats. | About 2.8-GB assembly input pack, later object/output retrieval; 719 changed objects planned. | The dump and surviving event timeline are needed to identify the actual failing phase. |

The retained interruption record gives bugcheck **0x7E**, exception **0xC0000005**,
and an exception address, but no resolved module because dump access was unavailable.
Microsoft describes these as an unhandled system-thread exception and access
violation respectively. A user-mode application can expose a driver defect; the
same outcome can also have unrelated kernel/hardware causes. Source comparison
cannot resolve the exception address to a driver.

| Hypothesis, not diagnosis | Evidence that would distinguish it | Avoidance in this study / remaining risk |
| --- | --- | --- |
| Driver cancellation/teardown race | Dump stack at the exception address; process-exit/transfer timeline; whether the 900-second kill path ran. | No forced host DMA termination/retry. Synchronous operations and explicit final acknowledgement; unregister after both digests are exchanged, before endpoint close. Any uncertain cleanup stops the entire matrix. A kernel fault during process death remains possible. |
| Source reuse, early unmap, or window-offset bug | Faulting request's direction, offsets/lengths and last acknowledged window; reproduce in an isolated small transfer. | One transfer/window at a time, explicit ready/completed phases, 64-bit bounds, pinned allocation lifetime, no reallocation, no file remapping, no implicit registration cache. |
| Pinned-memory/registration pressure | Dump/resource diagnostics and number of simultaneous registrations at failure; distinguish file-backed churn from reusable windows. | Register once per session, at most 64 MiB per endpoint, serial first; two concurrent sessions only after serial sizes pass. No 1-GiB pin or arbitrary fanout. |
| Reverse read path differs from write path | Stack/function and transfer direction; matched `readfrom` versus `writeto` trials in both directions. | Keep read, write, virtual write and mmap results separate. Production preference remains write until reverse trials succeed. Testing a driver path cannot guarantee avoidance of an unknown driver defect. |
| Card/host load changes timing or deadline behavior | Surviving workload timeline; idle versus 240-thread trial results, CPU time and completion timing. | Exclusive lease, explicit idle/load states, no production assembly, small-to-large ramp, no cancellation based on a short guessed throughput deadline. Timeout is a stop, not a retry. |
| Unrelated driver, link/power fault or hardware problem | Privileged dump analysis, WHEA/PCIe/event records, module versions, negotiated link state. | Check bugcheck/host boot before and after each trial group; stop on changes. No driver/power/link reconfiguration. This hypothesis cannot be eliminated in user code. |

Lead action: analyze the preserved crash dump with symbols before attributing
fault. Do not deliberately reproduce a BSOD or enable Driver Verifier as part of
this runner. Historical helper success does not clear an unexplained kernel crash.

## Measurement tool and lead handoff

Sources: `tools/transfer_bench.c`, `transfer_sha256.h`, `host_card_transfer.py`,
`transfer-card.sh`; acceptance test `tests/tools/test_host_card_transfer.py`.
Shared outputs: `.work/_shared/S11-01/transfer-host.exe`, `transfer-card.mic`,
`host_card_transfer.py`, `transfer-card.sh`. Host is Cygwin x64; card binary is
built with the installed **GCC-KNC 16.2.0 prefix**, not the donor compiler.
The host uses the already shared Cygwin runtime through PATH. No vendor binaries
are copied into the staging directory.

Host test: FIPS `abc` vector, two repetitions of a 1-MiB + 129-byte payload in
both directions over loopback, bounded fake-method framing, and an intentional
corruption which must fail. Fake methods use TCP to exercise payload framing;
**they do not emulate the SCIF driver, DMA visibility or registration semantics**.
Native correctness and performance remain pending.

Final local validation passed on 2026-11-12: host loopback/injected-corruption/FIPS
test and GCC-KNC build plus `knc_lint`. Logs under `.work/_state/logs/`:
`s11_01_loopback_final-20261112-075652.log` and
`s11_01_card_final-20261112-075652.log`. The binaries and runner are staged in
`.work/_shared/S11-01/`. x86 and native tests were not run.

Lead command, only inside the coordinated exclusive card turn, from the main
checkout (set the config path to the existing configuration):

```powershell
python tools/run.py --name s11-01-native --inputs tools/host_card_transfer.py tools/transfer_bench.c -- python .work/_shared/S11-01/host_card_transfer.py run --project C:/Users/xuzhi/Documents/gcc_knc --config C:/Users/xuzhi/Documents/gcc_knc/config/card.local.json --host-address 192.168.1.99 --lead-exclusive-turn
```

The runner starts a `card_run --benchmark --threads 240` lease and stages the
card helper/script there. The lease sends its exact guarded directory and granted
CPU set back over a nonce-bound control connection. Measured helpers are launched
through strict SSH in that directory and explicitly use that CPU set. The loaded
case creates one pinned arithmetic worker per granted CPU; pin readback must pass,
and all 240 workers must enter the busy state before its acknowledgement. Idle
workers sleep on a condition variable. The existing watchdog/boot/path admission
mechanism remains responsible for the card turn; the runner has its own 20-second
lease heartbeat. A failed heartbeat prevents subsequent groups.

For each method, size (4 KiB, 1 MiB, 64 MiB, 1 GiB), direction and load, twenty
payload transfers compare sender and receiver SHA-256 **in memory**, print the
digest and match result, and stop on mismatch. SHA is never a provenance file.
Normal buffer transfers retain a session/window across all twenty repetitions.
After all serial groups in both loads, two-session groups ramp through the same
sizes. No higher DMA concurrency is attempted. `--methods` permits a lead to stage
smaller coordinated turns; `--compression`, `--cipher` and `--mac` select explicit
SSH variants after the recorded offer intersection is known.

Results overwrite `results.jsonl`; control output overwrites `card-control.log`.
No dated output trees are created. An incomplete prior results stream requires
the lead to inspect the crash/cleanup state before explicitly using
`--acknowledge-prior-incomplete`. A host reboot terminates the runner; its unfinished
results remain a stop marker, not a successful run. Every group checks the System
WER bugcheck event and host boot identity before the next step. Event-log access
failure stops; an empty event query is distinguished from an access failure.
SCP/tar also check before/after each individual file transfer.

For buffer methods, `seconds` is the sum of acknowledged chunk-transfer intervals;
generation and SHA time are outside those intervals. Registration occurs before
the repetition loop. `wall_seconds` includes that repetition's generation/hash/
protocol work; `host_hash_seconds` identifies host hashing explicitly. `MiB_s`
uses payload bytes, not padding. `latency_us` is useful for the 4-KiB case.
`host_cpu_seconds` and `card_cpu_seconds` are endpoint process CPU during payload
intervals; SSH daemon/client and background load CPU are **not** included in those
buffer figures. Card elapsed uses `CLOCK_MONOTONIC_RAW`; Cygwin host uses its
monotonic clock, never cross-machine clock subtraction or TSC.

SCP/tar are separate **end-to-end file** cases: elapsed includes process setup,
SSH establishment, protocol and file IO, with SHA inspection outside timing.
The helper wraps the actual SCP/tar process and reports child CPU through `wait4`.
Host CPU includes the host transport process tree; card CPU is the remote SCP/tar
process tree, excluding its SSH daemon. Only the fixed generated payload is
archived. These numbers must not be mixed with memory-buffer throughput in a
single ranking. Session startup, disk IO, hashing, registration and publication
all matter to the user-visible crossover.

COI/micnativeloadex have **inventory-only coverage** in this tool. They are an
offload runtime with process creation/authentication outside the SSH admission
contract, not an implemented transport adapter. Existing COI authentication and
usable sink lifecycle have not been established. NFS/virtio are likewise not
marked measured or operational. If the lead establishes an already configured COI
path within the allowed admission model, it needs an additional buffer adapter
and its own measurements before a best-of-all-MPSS claim is possible.

The twenty-sample matrix is the ticket's requested characterization, not an M2
performance gate. There is no pre/post compiler change here. To accept an S11-02
speedup under ADR-0010, pair old and new paths on identical payloads and load,
interleave/rotate their order in at least three exclusive launches, preserve all
samples, and use paired ratios/confidence intervals. The current serial safety
ramp does **not** itself supply that paired integration evidence. Record the
clock/power policy at both ends of those qualification launches.

## Measurements and recommendations to fill in

Historical PC figures are not results of this tool. PC reports a 5.85-GB upload
in 26.375 seconds (about 212 MiB/s), an earlier matched 256-MiB + 129-byte comparison
of 69.5 MiB/s DMA versus 13.6 MiB/s SCP, and a later reusable-buffer sender time
of 1.090 seconds versus 3.203 seconds for the complete smaller upload. Different
versions, timing boundaries and workloads prevent combining them into one speedup.
There is no measured reverse-transfer speed here, and no verified 1.5-GB/s result.

For every measured cell retain n, failures/timeouts, median/range, tail latency,
CPU times, hash match status, direction, load, concurrency, cipher/MAC/compression,
and timing scope. Twenty successes characterize this experiment; they do not
establish long-term driver reliability. Failed or incomplete cells stay visible.

| Data kind | Interim practice | Lead measurements still needed | Production decision after evidence |
| --- | --- | --- | --- |
| Commands/control | Strict persistent SSH; no retry after ambiguous command execution. | 4-KiB latency, handshake-inclusive latency, CPU, loaded tails. **Pending.** | Keep SSH even if a bulk path is faster; control authenticates/bootstrap/cleanup. |
| Small files/scripts | Existing guarded SSH stream; avoid per-file SSH/chmod subprocesses. | 4-KiB / 1-MiB end-to-end SCP versus batched stream/tar, compression off/on. **Pending.** | Pick crossover using total elapsed, not DMA-only bandwidth. |
| Test suites | Existing `--file-list` pack and unpack validation; one archive stream. | Real suite count/byte mix, time-to-ready, CPU and load sensitivity. Synthetic file case **pending**, real-suite qualification S11-02. | Preserve safe unpacking; transport its bytes over the selected path only after equivalent failure behavior passes. |
| Multi-GB binaries/datasets | Candidate reusable-window SCIF **write**, once qualified; SSH remains available. | Both directions, 64-MiB / 1-GiB throughput, setup/registration plus disk costs, serial/concurrent failures. **Pending.** | Stream beyond 1 GiB with bounded windows; do not stage a second card copy or relax RAM admission blindly. |
| Results back to host | Guarded SSH readback today. Reverse DMA is experimental. | Card writes versus host reads versus TCP and SSH, exact tails/cleanup and native digests. **Pending.** | Prefer the measured reverse path independently; never extrapolate PhiChat's upload. Publish only after integrity and cleanup. |

Proposed fallback order for **bulk only**, subject to measured crossover and
capability discovery: qualified SCIF write -> nonce-bound TCP -> existing SSH
stream/SCP. Do not put unqualified read/vwrite/mmap ahead of established paths.
For small/control traffic start with SSH. A refused/unavailable capability before
data starts may select the next path. Mid-transfer failure may fall back only
after exact cleanup/boot identity is confirmed and the operation is safely
restartable. Integrity failure or bugcheck ends the turn; it never triggers
automatic fallback or another DMA attempt.

## S11-02 implementation plan and project advice

1. Factor transport selection beneath `tools/card_run`'s existing admission,
   strict SSH, boot guards, watchdog and cleanup. Keep metadata/control separate
   from bulk bytes. Discovery returns capability, selected node/port, limits and
   unsupported reason; it does not silently change the card.
2. Preserve staging-name, exact-length, duplicate/symlink, mode and total-memory
   checks. Feed the same validated pack to a receiver over the chosen transport.
   Use a private incomplete file, bounded windows, no data publication before
   exact length plus digest comparison, and atomic final rename. Preserve partial
   failure diagnostics without keeping huge abandoned payloads.
3. Define a progress deadline based on observed progress plus a total job budget;
   distinguish host scheduling/load from connection failure. Return separate
   bootstrap, register, transfer, hash, IO, publication and cleanup times. Never
   hide fallback cost or mark it as DMA throughput.
4. Keep a small stable transport API for `harness/card/run_suite.py`: stage a
   bundle once, run existing jobs, collect results through the same ownership
   contract. The engineer does not edit the protected harness in S11-01; the lead
   must grant S11-02's precise protected-path scope before implementation there.
5. Add actual disconnect, cancellation, short/excess data, stale nonce, changed
   boot, failed unregister and corruption cases in S11-02's authorized acceptance
   scope. Do not recover by killing an in-flight DMA process and retrying. Qualify
   direction and multi-window tails natively, then do the paired rollout measure.
6. PhiNix later: reuse the transport boundary and artifact lifecycle, not an
   application-specific receiver's paths/tokens. First qualify its exact workload
   and ownership model; do not introduce a service or privileged shared filesystem.

Advice for the lead to relay (nothing was sent): PhiWeather should retain its
approved SSH path while the 0x7E remains unattributed, preserve the dump/timeline,
and qualify reverse write/read separately in the small serial experiment before
reintroducing assembly load. PhiChat should keep its cleanup-confirmed fallback,
document which buffer revision each result measures, and treat eight copy workers
and its upload performance as workload-specific observations. Neither project
should infer reverse reliability or a safe forced-exit policy from successful uploads.

Draft ADR decision for the lead: authenticated SSH owns control and lifecycle;
bulk transfer is a bounded, capability-selected channel with exact length and
in-memory payload digest comparison, explicit completion before page reuse,
and cleanup-confirmed fallback. Retain SSH as the default until this card's native
direction/load matrix and S11-02's paired end-to-end results justify promotion.
No new privileged configuration or vendor redistribution. An unexplained bugcheck,
integrity error or uncertain DMA cleanup stops rather than retries.
