# Exact17 DP arithmetic source controls

The exact retained DP exp arithmetic inventory is implemented in
`translator/candidates/d3_exp_register_dp_forms.py`,
`d3_exp_register_dp_candidate.py` and `d3_exp_register_dp_reference.py`.
It remains source-only: production access rejects, both qualification fields
are false, and no assembler, native compiler or card action was performed.

The original three new groups passed in4.171 seconds at
`artifacts/test-state/exp-register-dp-source/14272253a4a64cbfa991b9c390c44d99/result.json`,
SHA256 `e39a7e2b39369de6255580200696c258105f0715e081c19f52c7e68ba317ef8f`.
They bind all17 retained line/literal anchors, integer-parse the eight official
Arm prefix words and three actual LC8B objects, compare complete6464 state
models for64 epochs per form, reject outside-domain sources/frames and refuse
production access. Candidate mismatches were zero; both completed negative
programs differed in all1,088 cases.

Integration then identified a fixture premise correction: the unchanged wire3
observer snapshots caller RSP, while separate raw metadata records leaf body
RSP. The initial source fixtures had equated them. The recipes and arithmetic
did not change. The candidate/reference now use only the explicit aligned body
RSP for original memory addresses and RSP-8 staging, preserving the captured
caller RSP untouched. Actual native admission must authenticate both values.
The original used files/results remain in their source snapshot.

Only the affected complete-state group was rerun after that correction. It
passed in4.331 seconds with caller RSP distinct from body RSP at
`artifacts/test-state/exp-register-dp-source/a01ecd115c364546ac04590246a24cae/result.json`,
SHA256 `2ae1f304247badaa8f2f7977837187035f735fdb23739fc06ffce87ed277d222`.
It again checked1,088 cases per variant, zero candidate mismatches and1,088
detected cases per wrong-operation/wrong-result variant, with no source drift.
The preceding runner-only discovery error and source snapshots are retained;
that error executed no tests, compiler or target code.

The stable source identities are forms
`3c78a4cfcb62f1b20aab2981fd3ef4900084005eff73b7a5a08031567ee76ca8`,
candidate `1b78dea7b693e0f85ec3ed0d7fe8befe80000d457c331e4b3e2c1abf3c71e334`
and reference `0cdc60ba2313bd33f127fe2fbc096e2112feda40db92f1ae295aae952ce75baf`.

Candidate APIs are `plan(source)`, `recipe(source, variant)` and
`simulate(source, before, page_base, body_rsp, symbols, variant)`. Independent
reference APIs are `source_result` and `physical_result` with the same context.
Variants are `candidate`, `wrong-operation`, `wrong-result`; the combined49
composition maps its `wrong-binding` label to the last complete program.
All sources are restricted to the17 exact retained literals.

Broadcast staging clobbers ZMM31 with eight copies of the original8B word,
R11 with that word and private scratch offsets120..127. Full64B stack staging
clobbers only ZMM31. Register FMA adds no scratch effect. The reference imports
no candidate/parser/program interpreter and uses existing calibrated exact
binary64 rational lanes, not host floating point. The forms module supplies
the exact64B Arm prefix and three8B LC payloads for future page-alias binding.

These checks support the combined49 source batch under separate ownership.
They establish neither emitted instruction semantics nor actual address/page
permissions, readonly bindings, ABI or G5. The missing native prerequisites
and bounded experiment declaration remain in
`REGISTER_EXP_DP_ARITHMETIC_PLAN.md`.
