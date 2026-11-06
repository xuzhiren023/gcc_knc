# Compensated atan2 source revision

The first unchanged musl-style rounded ratio→atan→quadrant composition failed
the strict1ULP screen at y=`6cf75f52a6cfd6a4`, x=`6d0193790d703a98`, with a
1.0078621130864913ULP bound. The original `atan_e.c`, first assay source and
failed receipt `host-atan-e/d74e20c29d954bc092beb2486bab29d5` stay unchanged.

`atan_e_v2.c` is a new source revision. It uses exact bit normalization and
common power scaling for moderate ratio exponents, then Dekker split products
to recover the division residual. The resulting angle correction is carried
inside the unrounded atan sum. A FastTwoSum low part is retained into a
compensated negative-x quadrant subtraction, avoiding an extra rounded atan
boundary. The underlying pinned Sun reductions, coefficients and special
classification remain the same; no scalar atan/atan2 fallback or relaxed
tolerance is introduced.

The focused falsifiable repair predicts removal of the retained failing pair
and ≤1ULP on a fresh seeded32K screen, followed only after passage by a fresh
≥1M corpus per operation. Include the old failing pair explicitly. Stop and
retain evidence if any over1ULP or mask/zero/severe-status failure persists.
Unchanged consumed sine/cosine/tangent sources are neither edited nor rerun.
