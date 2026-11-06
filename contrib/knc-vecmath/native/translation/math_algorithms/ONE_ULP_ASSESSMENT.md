# Derived one-ULP evaluation of the frozen DP exp sample

The original strict host DP exp result remains byte-exact at
`host-exp-full/85ff40f7a26b4f99b48f5a3b28c57a8f/experiment.json` under
`artifacts/test-state/`, SHA256
`cc3869c8a61387c9c5f53ed1456fee000f4a5154c4fd8870efc9d154326f606d`.
Its earlier four-ULP field is historical. A separate evaluation now directly
enforces the tighter <=1 ULP target on every actual frozen output lane.

The derived result is
`artifacts/test-state/host-exp-one-ulp/ec2f6cacf52d4093b49e1779eed73a8f/assessment.json`,
SHA256 `1881484a32abe05c9e40c2c0323291bb804251b9f44cfe170fc37fc9880703a2`.
New `scripts/Assess-HostExpFullOneUlp.py` authenticates the prior receipt and
only its relevant input/reference/output/oracle sources. It recomputes
independent exact bounds/reference for all 1,375,996 input lanes and compares
each actual finite error bound to Fraction(1). The reference bytes must agree
with the frozen independent reference. No compiler, kernel or card is rerun;
this is a numeric policy evaluation, not another native test or review gate.

Off and fast have zero mismatches, with exact maximum-bound numerators and
denominators stored in the result. Their displayed conservative maxima are
0.505430639581543 and 0.5043706063521957 ULP. There are 1,107,108 finite and
268,888 exact-special comparisons per variant. Source/artifact drift is empty.
Original native exception evidence remains in the unchanged prior result.

Two focused controls in `tests/test_host_exp_one_ulp.py` prove that the
separate comparator rejects an error of two ULP despite the old four-ULP
guard, and rejects special-value/payload mismatches. These are algorithm/
assay controls, not new hardware evidence. The original sampled-domain,
nearest-rounding, errno/trap/target/ABI limitations remain unchanged; G5 stays
false. Exact new file whitelist: the assessment script, its test and this
document. Existing source/report bytes are not changed.
