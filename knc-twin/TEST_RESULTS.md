# Test results, knc-twin 0.1.0

Actual run of `python scripts/knc_twin.py selftest` on 2026-11-15T18:18:14Z (host: Windows 10, Python 3.8.5). 72 tests, 0 failures, 0 errors, 0 skipped.

These are synthetic model tests (the engine behaves as specified) plus checks against independent oracles
(binary64 double-rounding oracle for binary32 add/sub/mul, Python binary64 for f64, hand-derived FMA/rounding/
special-value vectors, Python integers for integer semantics, hand-derived bounds). They are not validation against
hardware: `tests/heldout_native/` is empty and `card-7120-measured` says `held_out_validation_cases: 0`.

The example suite (`examples/run_examples.py`, results in `examples/RESULTS.md`) ran 31 commands: 24 with status ok and
7 that exercise the explicit non-ok statuses (functional_mismatch, needs_parameters, unsupported, missing_parameter x2,
budget_exhausted, incompatible), each with the matching exit code.

## test_asm (4)

- TestAsm.test_asm_fixture_matches_records: ok
- TestAsm.test_emit_round_trip: ok
- TestAsm.test_operand_forms: ok
- TestAsm.test_rejections: ok

## test_bounds (9)

- TestLoopBounds.test_critical_path_vs_ii: ok
- TestLoopBounds.test_recurrence_one_accumulator: ok
- TestLoopBounds.test_simulation_never_beats_bound: ok
- TestLoopBounds.test_two_accumulators_are_resource_bound: ok
- TestSearch.test_budget_not_exhausted_reported: ok
- TestSearch.test_exhaustive_search_finds_known_optimum: ok
- TestTraceBounds.test_bound_never_above_simulation: ok
- TestTraceBounds.test_critical_path_term: ok
- TestTraceBounds.test_issue_and_spacing_terms: ok

## test_cli (11)

- TestCLI.test_analytic_scales: ok
- TestCLI.test_bounds_loop_and_search: ok
- TestCLI.test_capabilities: ok
- TestCLI.test_compare_rules: ok
- TestCLI.test_invalid_input: ok
- TestCLI.test_output_dir_must_be_fresh: ok
- TestCLI.test_prepare_and_import_native: ok
- TestCLI.test_simulate_fields_and_statuses: ok
- TestCLI.test_statuses_and_exit_codes: ok
- TestCLI.test_synthetic_profile_is_labeled: ok
- TestCLI.test_validate_and_result_fields: ok

## test_fp (13)

- TestBinary32Oracle.test_add_mul_match_double_rounding_oracle: ok
- TestBinary32Oracle.test_binary64_matches_python: ok
- TestBinary32Oracle.test_sub_matches_oracle: ok
- TestFMA.test_fma_exact_integers: ok
- TestFMA.test_fma_f64: ok
- TestFMA.test_fnmadd_fmsub: ok
- TestFMA.test_fused_differs_from_unfused: ok
- TestRoundingAndSpecials.test_compare: ok
- TestRoundingAndSpecials.test_conversions: ok
- TestRoundingAndSpecials.test_directed_rounding: ok
- TestRoundingAndSpecials.test_exact_zero_sign: ok
- TestRoundingAndSpecials.test_infinities_and_nans: ok
- TestRoundingAndSpecials.test_subnormals_ftz_daz: ok

## test_functional (15)

- TestChecksAndRejections.test_contexts_communicating_through_memory_rejected: ok
- TestChecksAndRejections.test_deliberately_wrong_candidate_is_caught: ok
- TestChecksAndRejections.test_fixture_expectations_hold: ok
- TestChecksAndRejections.test_nan_compare_policy: ok
- TestChecksAndRejections.test_timing_only_instruction_rejected_in_functional: ok
- TestChecksAndRejections.test_unknown_instruction_rejected_at_load: ok
- TestMaskAndVector.test_conversions_and_broadcast: ok
- TestMaskAndVector.test_gather_clears_mask_and_touches_lines: ok
- TestMaskAndVector.test_kortest_and_logic: ok
- TestMaskAndVector.test_masked_merge_and_compare: ok
- TestMaskAndVector.test_misaligned_vector_access_is_rejected: ok
- TestScalar.test_flags_add_overflow_and_sub_borrow: ok
- TestScalar.test_inc_dec_keep_cf_and_loop: ok
- TestScalar.test_memory_round_trip_and_uninitialized_read: ok
- TestScalar.test_shift_imul_lea: ok

## test_timing (20)

- TestBudgetsAndDeterminism.test_branch_scenarios: ok
- TestBudgetsAndDeterminism.test_concurrent_runs_share_no_state: ok
- TestBudgetsAndDeterminism.test_cycle_budget_reports_partial: ok
- TestBudgetsAndDeterminism.test_deterministic: ok
- TestBudgetsAndDeterminism.test_missing_parameter_is_explicit: ok
- TestLatencyAndSpacing.test_four_contexts_round_robin: ok
- TestLatencyAndSpacing.test_independent_ops_one_context_every_other_cycle: ok
- TestLatencyAndSpacing.test_producer_consumer_latency: ok
- TestLatencyAndSpacing.test_stalled_context_lets_others_progress: ok
- TestLatencyAndSpacing.test_two_contexts_fill_every_cycle: ok
- TestMemory.test_agi: ok
- TestMemory.test_demand_miss_stalls_context: ok
- TestMemory.test_fixed_level_l2: ok
- TestMemory.test_outstanding_miss_limit: ok
- TestMemory.test_prefetch_is_nonblocking_and_hides_latency: ok
- TestPairing.test_dependent_scalar_does_not_pair_but_cmp_jcc_does: ok
- TestPairing.test_encoding_hint_blocks_pairing: ok
- TestPairing.test_gather_occupies_both_pipes: ok
- TestPairing.test_two_vector_ops_do_not_pair: ok
- TestPairing.test_vector_plus_scalar_pairs: ok

## Coverage of the required test topics

| topic | tests |
|---|---|
| producer-to-consumer latency | test_timing.TestLatencyAndSpacing.test_producer_consumer_latency; test_bounds critical path |
| per-context issue-spacing | test_independent_ops_one_context_every_other_cycle; test_two_contexts_fill_every_cycle |
| progress by other eligible contexts | test_stalled_context_lets_others_progress; test_four_contexts_round_robin |
| legal and illegal pairing | TestPairing (vector+scalar, vector+vector, RAW inside a pair, cmp/jcc exception, encoding hint, gather both pipes) |
| demand-miss stalls vs prefetch | TestMemory.test_demand_miss_stalls_context, test_prefetch_is_nonblocking_and_hides_latency, test_outstanding_miss_limit, test_fixed_level_l2 |
| arithmetic and mask edge cases | test_fp (oracle, FMA, directed rounding, zero sign, inf/NaN, subnormal FTZ/DAZ, conversions, compare); test_functional (flags, inc/dec CF, shifts, imul, kortest, masked merge, gather, conversions) |
| deliberately incorrect candidates | test_functional.test_deliberately_wrong_candidate_is_caught; test_cli statuses (functional_mismatch, exit 6, no prediction reported) |
| unknown instructions, missing parameters | test_unknown_instruction_rejected_at_load; test_missing_parameter_is_explicit; test_cli statuses (unsupported 3, missing_parameter 4, needs_parameters 7) |
| deterministic results | test_deterministic (identical result and issue log across runs) |
| bounded execution, explicit timeout | test_cycle_budget_reports_partial; test_cli budget_exhausted (cycles and steps), partial block |
| independent concurrent runs | test_concurrent_runs_share_no_state (ThreadPoolExecutor, 12 runs vs serial) |
| bounds with known answers | test_bounds (RecMII 4 for one accumulator, ResMII 6 for two, spacing bound 11 met exactly, critical path 12, bound <= simulation on every fixture, exhaustive search finds the known optimum) |
