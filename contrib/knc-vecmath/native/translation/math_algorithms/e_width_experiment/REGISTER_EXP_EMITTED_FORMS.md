# Actual first DP8 exp emission: unknown forms

The root-owned first emission `677ed99fa8a54090815a91bf1b7fd086` generated zero gathers.
Its retained report has **246 unknown sites across35 mnemonics**. This additive
inventory reconciles every site with that report; no translator, compiler or
card was rerun. Exact literals/line anchors and consumed input identities are
in [REGISTER_EXP_EMITTED_FORMS.json](REGISTER_EXP_EMITTED_FORMS.json).

The source-only readiness note records the earlier preparation state. This
document records the subsequently completed root emission. Neither inventory
nor zero-gather emission qualifies an instruction, ABI boundary or G5 export.

| Group | Unknown sites | Next source work |
| --- | ---: | --- |
| Scalar integer control | 13 | BTR bit63 and CMOVA need exact scalar register/EFLAGS semantics; do not infer support from the broad integer catalog. |
| DP arithmetic memory and unmeasured FMA tuples | 17 | Reuse register DP arithmetic structure and calibrated binary64 rational lanes; qualify exact tuples,8B broadcast or64B stack staging and declared physical scratch effects. |
| Fixed shard selection and mask plumbing | 70 | Reuse fixed aligned-load/permutation, shifts and raw Boolean structures; new K1-K4 zeroing-permute semantics, equality0,TERNLOG254 truth table and32 readonly bindings require exact qualification. |
| Integer predicate lowering | 93 | Reuse shifts/logical/qword carry structures where applicable; add exact vector equality, signed dword-to-qword extension and VTEST flags semantics. |
| Block and lane transfer | 23 | Reuse measured block recipes for new tuples; unpack-high and ALIGNQ need independent exact lane equations. Preserve upper-zero and scratch effects. |
| Masked qword memory and byte blend | 28 | New sign-bit-selected qword memory must prove suppression and complete effects; byte-sign blend is distinct from the measured dword predicate family. |
| Typed register copy | 2 | Reuse measured low256 copy and upper256-zero structure for these two literal register tuples. |

The smallest DP arithmetic slice has17 sites:10 FMA,4 memory MUL and3
memory ADD. The10 FMA sites contain3 register triples,5 readonly8B broadcasts
and2 aligned64B stack inputs. MUL contains3 readonly8B broadcasts and1
aligned64B stack input; ADD contains1 readonly8B broadcast and2 aligned64B
stack inputs. Existing register ADD/MUL/SUB already translated7/3/3 sites.
They are not part of the new17-form qualification domain.

| Line | Held DP arithmetic literal |
| ---: | --- |
| 263 | `vfmadd132pd arm_math_exp_data(%rip){1to8}, %zmm2, %zmm4` |
| 282 | `vfmadd231pd arm_math_exp_data+8(%rip){1to8}, %zmm5, %zmm1` |
| 284 | `vfmadd132pd arm_math_exp_data+16(%rip){1to8}, %zmm1, %zmm5` |
| 370 | `vfmadd213pd arm_math_exp_data+24(%rip){1to8}, %zmm5, %zmm0` |
| 373 | `vfmadd213pd arm_math_exp_data+40(%rip){1to8}, %zmm5, %zmm7` |
| 380 | `vfmadd231pd %zmm14, %zmm0, %zmm15` |
| 393 | `vfmadd231pd %zmm7, %zmm1, %zmm15` |
| 410 | `vfmadd132pd %zmm15, %zmm3, %zmm3` |
| 454 | `vfmadd132pd 256(%rsp), %zmm5, %zmm5` |
| 455 | `vmulpd .LC57(%rip){1to8}, %zmm5, %zmm10` |
| 514 | `vmulpd 192(%rsp), %zmm11, %zmm13` |
| 583 | `vmulpd .LC61(%rip){1to8}, %zmm1, %zmm13` |
| 603 | `vaddpd 384(%rsp), %zmm14, %zmm10` |
| 629 | `vaddpd 448(%rsp), %zmm10, %zmm6` |
| 884 | `vaddpd .LC60(%rip){1to8}, %zmm12, %zmm8` |
| 1129 | `vfmadd132pd 256(%rsp), %zmm11, %zmm11` |
| 1130 | `vmulpd .LC57(%rip){1to8}, %zmm11, %zmm3` |

The next prototype stages memory bits into reserved ZMM31 before a full
eight-lane DP operation. Scalar broadcasts use an8B R11/private-stack staging
path; full-vector stack loads require the concrete GCC-aligned frame. New
exact tuples need their own probe and independent complete-state binary64
qualification. The SP expf receipt and literal FMA manifest do not broaden.

The remaining dominant source gap is vector predicate lowering: VPMASKMOVQ
and VMASKMOVPD use sign bits in vector masks, and VTEST affects flags. Their
semantics cannot be substituted by a dword masked-memory recipe. Static
table permutation also uses K1-K4 zeroing and32 separate readonly spans.
No generic alignment/proof engine, runner or automatic registration is added.
