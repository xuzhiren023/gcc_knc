# Calibration cases

Kernels whose native measurement isolates one model parameter (a dependent chain for a
latency, independent ops for a throughput, a cold stream for memory latency). Each case is a
kernel JSON here plus, once measured, its `measurement.json` (schema
`knc-twin.native-measurement/1`) and the `request.json` it answers.

Currently empty. The measured parameters in `profiles/card-7120-measured.json` were imported
from the gcc_knc project's own characterization binaries (S6-03, S8-01, S8-10, S8-12, S8-17;
job ids in the profile), not from kernels in this directory.

Candidates for the first requests (each isolates a parameter the model is uncertain about):

- `vector_load_to_use`: `vmovaps` load followed by a dependent `vaddps`, L1-resident, one thread
  (decides between the measured 12 and the documented 3 for `latency.vector_load_l1`).
- `dec_jnz_pairing`: a counted loop with `dec/jnz` vs `cmp/jne` (decides whether `dec/jnz`
  pairs like `cmp/jcc`).
- `fence_latency`: `lock addl` in a dependent chain (`latency.fence`, unknown).
- `l1_two_accesses_per_cycle`: paired scalar load + vector store (`l1.accesses_per_cycle`).

Procedure: `references/calibration.md`.
