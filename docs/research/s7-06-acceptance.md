# S7-06: shared libgcc native acceptance

Card results: `docs/research/card-runs-s7.md` (2026-11-07, all payloads pass with the donor and the
candidate `libgcc_s.so.1`). Owner decision, 2026-11-07: GCC-KNC's runtime lives in a private
directory on the card; the donor `/lib64/libgcc_s.so.1` stays untouched; rollback is deleting that
directory.
