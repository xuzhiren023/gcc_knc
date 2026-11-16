# GCC-KNC output audit (knc-twin adapter)

Per function: instructions, how many the twin reads (parser), knows (isa), executes exactly (functional) and can time with the profile (timing). A loop is complete when every instruction in it passes. Native seconds come from the weights file when given.

| file | function | instrs | parser | isa | functional | timing | unknown mnemonics / blockers | innermost loops (label: instrs, functional, timing) | native s |
|---|---|---:|---:|---:|---:|---:|---|---|---:|
| compiler-donor.s | donor_csr_raw | 45 | 45 | 45 | 45 | 45 |  | .L4: 8, yes, yes; .L15: 13, yes, yes | 2.625 |
| compiler-donor.s | donor_hpcg_raw | 41 | 41 | 41 | 41 | 41 |  | .L19: 8, yes, yes; .L29: 13, yes, yes |  |
| compiler-donor.s | donor_csr_scalar | 8 | 8 | 8 | 8 | 8 |  |  |  |
| compiler-donor.s | donor_hpcg_scalar | 8 | 8 | 8 | 8 | 8 |  |  |  |
| compiler-donor.s | donor_lone_scalar | 21 | 21 | 21 | 21 | 21 |  | .L34: 8, yes, yes; .L33: 5, yes, yes |  |
| compiler-donor.s | donor_shape_spmv | 53 | 53 | 53 | 53 | 53 |  | .L40: 8, yes, yes; .L49: 13, yes, yes |  |
| compiler-donor.s | donor_shape_forward | 41 | 41 | 41 | 41 | 41 |  | .L53: 8, yes, yes |  |
| compiler-donor.s | donor_shape_backward | 52 | 52 | 52 | 52 | 52 |  | .L64: 8, yes, yes |  |
| compiler-knc.s | knc_csr_raw | 113 | 113 | 113 | 113 | 113 |  | .L6: 43, yes, yes; .L7: 8, yes, yes; .L8: 8, yes, yes | 2.525 |
| compiler-knc.s | knc_hpcg_raw | 110 | 110 | 110 | 110 | 110 |  | .L32: 42, yes, yes; .L33: 8, yes, yes; .L34: 8, yes, yes |  |
| compiler-knc.s | knc_csr_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-knc.s | knc_hpcg_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-knc.s | knc_lone_scalar | 86 | 86 | 86 | 86 | 86 |  | .L51: 42, yes, yes; .L52: 8, yes, yes; .L53: 8, yes, yes |  |
| compiler-knc.s | knc_shape_spmv | 41 | 41 | 41 | 41 | 41 |  | .L65: 8, yes, yes; .L74: 11, yes, yes |  |
| compiler-knc.s | knc_shape_forward | 44 | 44 | 44 | 44 | 44 |  | .L78: 8, yes, yes |  |
| compiler-knc.s | knc_shape_backward | 61 | 61 | 61 | 61 | 61 |  | .L89: 8, yes, yes |  |
| compiler-enabled.s | enabled_csr_raw | 270 | 270 | 270 | 270 | 270 |  | .L7: 14, yes, yes; .L17: 43, yes, yes; .L18: 8, yes, yes; .L55: 25, yes, yes; .L19: 8, yes, yes; .L10: 43, yes, yes; .L11: 8, yes, yes; .L12: 8, yes, yes | 2.525 |
| compiler-enabled.s | enabled_hpcg_raw | 345 | 345 | 345 | 345 | 345 |  | .L65: 12, yes, yes; .L77: 43, yes, yes; .L78: 8, yes, yes; .L110: 24, yes, yes; .L79: 8, yes, yes; .L71: 42, yes, yes; .L72: 8, yes, yes; .L67: 42, yes, yes; .L68: 8, yes, yes; .L73: 8, yes, yes; .L69: 8, yes, yes |  |
| compiler-enabled.s | enabled_csr_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-enabled.s | enabled_hpcg_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-enabled.s | enabled_lone_scalar | 119 | 119 | 119 | 119 | 119 |  | .L119: 14, yes, yes; .L121: 42, yes, yes; .L122: 8, yes, yes; .L120: 8, yes, yes |  |
| compiler-enabled.s | enabled_shape_spmv | 155 | 155 | 155 | 155 | 155 |  | .L146: 12, yes, yes; .L139: 31, yes, yes; .L154: 9, yes, yes; .L149: 8, yes, yes; .L143: 8, yes, yes; .L144: 8, yes, yes |  |
| compiler-enabled.s | enabled_shape_forward | 138 | 138 | 138 | 138 | 138 |  | .L185: 12, yes, yes; .L188: 8, yes, yes; .L182: 8, yes, yes; .L183: 8, yes, yes |  |
| compiler-enabled.s | enabled_shape_backward | 179 | 179 | 179 | 179 | 179 |  | .L226: 12, yes, yes; .L223: 8, yes, yes; .L231: 8, yes, yes; .L224: 8, yes, yes |  |
| compiler-fast.s | fast_csr_raw | 270 | 270 | 270 | 270 | 270 |  | .L7: 14, yes, yes; .L17: 43, yes, yes; .L18: 8, yes, yes; .L55: 25, yes, yes; .L19: 8, yes, yes; .L10: 43, yes, yes; .L11: 8, yes, yes; .L12: 8, yes, yes | 2.55 |
| compiler-fast.s | fast_hpcg_raw | 345 | 345 | 345 | 345 | 345 |  | .L65: 12, yes, yes; .L77: 43, yes, yes; .L78: 8, yes, yes; .L110: 24, yes, yes; .L79: 8, yes, yes; .L71: 42, yes, yes; .L72: 8, yes, yes; .L67: 42, yes, yes; .L68: 8, yes, yes; .L73: 8, yes, yes; .L69: 8, yes, yes |  |
| compiler-fast.s | fast_csr_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-fast.s | fast_hpcg_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-fast.s | fast_lone_scalar | 119 | 119 | 119 | 119 | 119 |  | .L119: 14, yes, yes; .L121: 42, yes, yes; .L122: 8, yes, yes; .L120: 8, yes, yes |  |
| compiler-fast.s | fast_shape_spmv | 155 | 155 | 155 | 155 | 155 |  | .L146: 12, yes, yes; .L139: 31, yes, yes; .L154: 9, yes, yes; .L149: 8, yes, yes; .L143: 8, yes, yes; .L144: 8, yes, yes |  |
| compiler-fast.s | fast_shape_forward | 138 | 138 | 138 | 138 | 138 |  | .L185: 12, yes, yes; .L188: 8, yes, yes; .L182: 8, yes, yes; .L183: 8, yes, yes |  |
| compiler-fast.s | fast_shape_backward | 179 | 179 | 179 | 179 | 179 |  | .L226: 12, yes, yes; .L223: 8, yes, yes; .L231: 8, yes, yes; .L224: 8, yes, yes |  |
| compiler-min4.s | min4_csr_raw | 270 | 270 | 270 | 270 | 270 |  | .L7: 14, yes, yes; .L17: 43, yes, yes; .L18: 8, yes, yes; .L55: 25, yes, yes; .L19: 8, yes, yes; .L10: 43, yes, yes; .L11: 8, yes, yes; .L12: 8, yes, yes | 2.55 |
| compiler-min4.s | min4_hpcg_raw | 345 | 345 | 345 | 345 | 345 |  | .L65: 12, yes, yes; .L77: 43, yes, yes; .L78: 8, yes, yes; .L110: 24, yes, yes; .L79: 8, yes, yes; .L71: 42, yes, yes; .L72: 8, yes, yes; .L67: 42, yes, yes; .L68: 8, yes, yes; .L73: 8, yes, yes; .L69: 8, yes, yes |  |
| compiler-min4.s | min4_csr_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-min4.s | min4_hpcg_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-min4.s | min4_lone_scalar | 119 | 119 | 119 | 119 | 119 |  | .L119: 14, yes, yes; .L121: 42, yes, yes; .L122: 8, yes, yes; .L120: 8, yes, yes |  |
| compiler-min4.s | min4_shape_spmv | 155 | 155 | 155 | 155 | 155 |  | .L146: 12, yes, yes; .L139: 31, yes, yes; .L154: 9, yes, yes; .L149: 8, yes, yes; .L143: 8, yes, yes; .L144: 8, yes, yes |  |
| compiler-min4.s | min4_shape_forward | 138 | 138 | 138 | 138 | 138 |  | .L185: 12, yes, yes; .L188: 8, yes, yes; .L182: 8, yes, yes; .L183: 8, yes, yes |  |
| compiler-min4.s | min4_shape_backward | 179 | 179 | 179 | 179 | 179 |  | .L226: 12, yes, yes; .L223: 8, yes, yes; .L231: 8, yes, yes; .L224: 8, yes, yes |  |
| compiler-manual.s | manual_csr_raw | 185 | 185 | 185 | 185 | 185 |  | .L14: 43, yes, yes; .L15: 8, yes, yes; .L9: 17, yes, yes; .L16: 8, yes, yes | 2.55 |
| compiler-manual.s | manual_hpcg_raw | 197 | 197 | 197 | 197 | 197 |  | .L57: 42, yes, yes; .L58: 8, yes, yes; .L53: 13, yes, yes; .L74: 15, yes, yes; .L59: 8, yes, yes |  |
| compiler-manual.s | manual_csr_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-manual.s | manual_hpcg_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-manual.s | manual_lone_scalar | 121 | 121 | 121 | 121 | 121 |  | .L89: 42, yes, yes; .L90: 8, yes, yes; .L84: 16, yes, yes; .L91: 8, yes, yes |  |
| compiler-manual.s | manual_shape_spmv | 133 | 133 | 133 | 133 | 133 |  | .L112: 8, yes, yes; .L100: 59, yes, yes; .L109: 13, yes, yes; .L107: 15, yes, yes |  |
| compiler-manual.s | manual_shape_forward | 136 | 136 | 136 | 136 | 136 |  | .L141: 8, yes, yes; .L138: 13, yes, yes |  |
| compiler-manual.s | manual_shape_backward | 194 | 194 | 194 | 194 | 194 |  | .L177: 8, yes, yes; .L174: 13, yes, yes; .L204: 27, yes, yes |  |
| compiler-twin.s | twin_csr_raw | 240 | 240 | 240 | 240 | 240 |  | .L16: 43, yes, yes; .L17: 8, yes, yes; .L18: 8, yes, yes; .L8: 43, yes, yes; .L9: 8, yes, yes; .L50: 27, yes, yes; .L11: 8, yes, yes | 2.605 |
| compiler-twin.s | twin_hpcg_raw | 232 | 232 | 232 | 232 | 232 |  | .L67: 42, yes, yes; .L68: 8, yes, yes; .L69: 8, yes, yes; .L60: 42, yes, yes; .L61: 8, yes, yes; .L86: 26, yes, yes; .L63: 8, yes, yes |  |
| compiler-twin.s | twin_csr_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-twin.s | twin_hpcg_scalar | 9 | 9 | 9 | 9 | 9 |  |  |  |
| compiler-twin.s | twin_lone_scalar | 86 | 86 | 86 | 86 | 86 |  | .L95: 42, yes, yes; .L96: 8, yes, yes; .L97: 8, yes, yes |  |
| compiler-twin.s | twin_shape_spmv | 41 | 41 | 41 | 41 | 41 |  | .L109: 8, yes, yes; .L118: 11, yes, yes |  |
| compiler-twin.s | twin_shape_forward | 44 | 44 | 44 | 44 | 44 |  | .L122: 8, yes, yes |  |
| compiler-twin.s | twin_shape_backward | 61 | 61 | 61 | 61 | 61 |  | .L133: 8, yes, yes |  |
| hpcg-shapes-on.s | sparse_rows | 270 | 270 | 270 | 270 | 270 |  | .L7: 14, yes, yes; .L17: 43, yes, yes; .L18: 8, yes, yes; .L55: 25, yes, yes; .L19: 8, yes, yes; .L10: 43, yes, yes; .L11: 8, yes, yes; .L12: 8, yes, yes |  |
| hpcg-shapes-on.s | sparse_slice | 133 | 133 | 133 | 133 | 133 |  | .L62: 14, yes, yes; .L65: 43, yes, yes; .L66: 28, yes, yes; .L67: 8, yes, yes |  |
| hpcg-shapes-on.s | sparse_hpcg | 345 | 345 | 345 | 345 | 345 |  | .L96: 12, yes, yes; .L108: 43, yes, yes; .L109: 8, yes, yes; .L141: 24, yes, yes; .L110: 8, yes, yes; .L102: 42, yes, yes; .L103: 8, yes, yes; .L98: 42, yes, yes; .L99: 8, yes, yes; .L104: 8, yes, yes; .L100: 8, yes, yes |  |
| hpcg-shapes-on.s | sparse_struct_spmv | 155 | 155 | 155 | 155 | 155 |  | .L151: 12, yes, yes; .L144: 31, yes, yes; .L159: 9, yes, yes; .L154: 8, yes, yes; .L148: 8, yes, yes; .L149: 8, yes, yes |  |
| hpcg-shapes-on.s | sparse_struct_forward | 139 | 139 | 139 | 139 | 139 |  | .L190: 12, yes, yes; .L193: 8, yes, yes; .L187: 8, yes, yes; .L188: 8, yes, yes |  |
| hpcg-shapes-on.s | sparse_struct_backward | 179 | 179 | 179 | 179 | 179 |  | .L231: 12, yes, yes; .L228: 8, yes, yes; .L236: 8, yes, yes; .L229: 8, yes, yes |  |
| hpcg-shapes-on.s | explicit_struct | 34 | 34 | 34 | 34 | 34 |  | .L269: 10, yes, yes |  |
| hpcg-shapes-on.s | alias_bounds | 149 | 149 | 149 | 149 | 149 |  | .L285: 14, yes, yes; .L289: 43, yes, yes; .L290: 22, yes, yes; .L291: 8, yes, yes |  |
| hpcg-shapes-on.s | explicit_csr | 33 | 33 | 33 | 33 | 33 |  | .L324: 6, yes, yes; .L320: 12, yes, yes |  |
| hpcg-shapes-on.s | explicit_rowlocal | 32 | 32 | 32 | 32 | 32 |  | .L336: 11, yes, yes |  |
| hpcg-shapes-on.s | explicit_hpcg | 29 | 29 | 29 | 29 | 29 |  | .L344: 9, yes, yes |  |
| hpcg-shapes-on.s | explicit_loop | 64 | 64 | 64 | 64 | 64 |  | .L360: 39, yes, yes; .L361: 6, yes, yes; .L362: 6, yes, yes |  |
| hpcg-shapes-on.s | volatile_indices | 86 | 86 | 86 | 86 | 86 |  | .L369: 42, yes, yes; .L370: 9, yes, yes; .L371: 9, yes, yes |  |
| hpcg-shapes-on.s | sentinel_slice | 29 | 29 | 29 | 29 | 29 |  | .L381: 15, yes, yes; .L376: 6, yes, yes |  |
| hpcg-shapes-on.s | explicit_indirect | 11 | 11 | 11 | 11 | 11 |  |  |  |
| hpcg-shapes-on.s | explicit_stream | 5 | 5 | 5 | 5 | 5 |  |  |  |
| application-cg.s | conj_grad_._omp_fn.0 | 1637 | 1637 | 1637 | 1637 | 1628 | missing parameter(s): latency.fence, latency.fence; missing parameter(s): occupancy.scatter_cycles_per_line | .L6: 18, yes, yes; .Lknc_gather209: 3, yes, yes; .Lknc_scatter211: 3, yes, no; .Lknc_scatter212: 3, yes, no; .L13: 31, yes, yes; .L14: 8, yes, yes; .L40: 257, yes, no; .L45: 93, yes, yes; .L47: 9, yes, yes; .L48: 9, yes, yes; .L69: 16, yes, yes; .Lknc_gather873: 3, yes, yes; .Lknc_gather874: 3, yes, yes; .Lknc_scatter878: 3, yes, no; .L24: 93, yes, yes; .L26: 9, yes, yes; .L32: 24, yes, yes; .Lknc_gather1238: 3, yes, yes; .Lknc_gather1239: 3, yes, yes; .L61: 39, yes, yes; .Lknc_gather1423: 3, yes, yes; .Lknc_gather1424: 3, yes, yes; .Lknc_scatter1429: 3, yes, no; .Lknc_gather1432: 3, yes, yes; .Lknc_gather1435: 3, yes, yes; .Lknc_scatter1448: 3, yes, no; .L53: 23, yes, yes; .Lknc_gather1555: 3, yes, yes; .Lknc_gather1556: 3, yes, yes; .L27: 9, yes, yes; .L55: 60, yes, yes; .L63: 28, yes, yes; .L71: 11, yes, yes; .L15: 7, yes, yes; .L34: 64, yes, yes; .L8: 10, yes, yes |  |
| application-cg.s | MAIN__._omp_fn.2 | 96 | 96 | 96 | 96 | 95 | missing parameter(s): occupancy.scatter_cycles_per_line | .L182: 8, yes, yes; .Lknc_scatter2265: 3, yes, no; .L184: 6, yes, yes |  |
| application-cg.s | MAIN__._omp_fn.1 | 283 | 283 | 283 | 283 | 282 | missing parameter(s): occupancy.scatter_cycles_per_line | .L195: 58, yes, yes; .L196: 11, yes, yes; .L202: 14, yes, yes; .Lknc_gather2599: 3, yes, yes; .Lknc_scatter2601: 3, yes, no; .L197: 10, yes, yes; .L204: 9, yes, yes |  |
| application-cg.s | MAIN__._omp_fn.3 | 336 | 336 | 336 | 336 | 335 | missing parameter(s): occupancy.scatter_cycles_per_line | .L227: 58, yes, yes; .L228: 11, yes, yes; .L235: 14, yes, yes; .Lknc_gather3030: 3, yes, yes; .Lknc_scatter3032: 3, yes, no; .L229: 10, yes, yes; .L237: 9, yes, yes |  |
| application-cg.s | MAIN__ | 511 | 511 | 511 | 511 | 511 |  | .L260: 8, yes, yes; .L262: 26, yes, yes; .L263: 38, yes, yes; .L263: 38, yes, yes; .L264: 25, yes, yes; .L275: 62, yes, yes; .L275: 62, yes, yes |  |
| application-cg.s | conj_grad_ | 23 | 23 | 23 | 23 | 23 |  |  |  |
| application-cg.s | sparse_ | 1081 | 1081 | 1081 | 1081 | 1078 | missing parameter(s): occupancy.scatter_cycles_per_line | .L301: 10, yes, yes; .L308: 39, yes, yes; .L309: 7, yes, yes; .L314: 16, yes, yes; .L316: 767, yes, no; .L320: 11, yes, yes; .Lknc_gather4269: 3, yes, yes; .Lknc_scatter4271: 3, yes, no; .L326: 23, yes, yes; .L329: 10, yes, yes; .L329: 10, yes, yes; .L333: 12, yes, yes; .L336: 10, yes, yes; .L347: 40, yes, yes; .L348: 6, yes, yes; .L354: 16, yes, yes; .L356: 395, yes, no; .L360: 11, yes, yes; .Lknc_gather4864: 3, yes, yes; .Lknc_scatter4866: 3, yes, no; .L366: 47, yes, yes; .L371: 16, yes, yes; .Lknc_gather5058: 3, yes, yes; .Lknc_gather5059: 3, yes, yes; .Lknc_scatter5062: 3, yes, no; .L306: 7, yes, yes; .L321: 9, yes, yes; .L349: 6, yes, yes; .L361: 9, yes, yes; .L373: 11, yes, yes |  |
| application-cg.s | vecset_ | 28 | 28 | 28 | 28 | 28 |  | .L493: 9, yes, yes |  |
| application-cg.s | sprnvc_ | 84 | 84 | 84 | 84 | 84 |  | .L502: 40, yes, yes; .L502: 40, yes, yes; .L501: 6, yes, yes |  |
| application-cg.s | makea_ | 191 | 191 | 191 | 191 | 191 |  | .L513: 4, yes, yes; .L518: 51, yes, yes; .L520: 11, yes, yes; .L521: 50, yes, yes |  |
| application-cg.s | MAIN__._omp_fn.0 | 432 | 432 | 432 | 432 | 430 | missing parameter(s): occupancy.scatter_cycles_per_line | .L539: 39, yes, yes; .Lknc_gather6046: 3, yes, yes; .Lknc_scatter6049: 3, yes, no; .L546: 8, yes, yes; .Lknc_scatter6145: 3, yes, no; .L540: 28, yes, yes; .L548: 6, yes, yes |  |
| application-cg.s | icnvrt_ | 12 | 12 | 12 | 12 | 12 |  |  |  |
| application-cg.s | main | 10 | 10 | 10 | 10 | 10 |  |  |  |
| application-spmv.s | _Z15ComputeSPMV_refRK19SparseMatrix_STRUCTR13Vector_STRUCTS3_._omp_fn.0 | 165 | 165 | 165 | 165 | 165 |  | .L13: 12, yes, yes; .L45: 10, yes, yes; .L41: 14, yes, yes; .L16: 10, yes, yes; .L8: 8, yes, yes; .L10: 8, yes, yes; .L11: 8, yes, yes |  |
| application-spmv.s | _Z15ComputeSPMV_refRK19SparseMatrix_STRUCTR13Vector_STRUCTS3_ | 35 | 35 | 35 | 35 | 35 |  |  |  |
| application-symgs.s | _Z16ComputeSYMGS_refRK19SparseMatrix_STRUCTRK13Vector_STRUCTRS2_ | 321 | 321 | 321 | 321 | 321 |  | .L9: 12, yes, yes; .L20: 12, yes, yes; .L13: 8, yes, yes; .L17: 8, yes, yes; .L6: 8, yes, yes; .L18: 8, yes, yes; .L7: 8, yes, yes; .L25: 8, yes, yes |  |
| kernels.s | char_kernel_0 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_1 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_2 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_3 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_4 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_5 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_6 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_7 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_8 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_9 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_10 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_11 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_12 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_13 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_14 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_15 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_16 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_17 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_18 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_19 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_20 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_21 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_22 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_23 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_24 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_25 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_26 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_27 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_28 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_29 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_30 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_31 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_32 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_33 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_34 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_35 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_36 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_37 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_38 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_39 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_40 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_41 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_42 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_43 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_44 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_45 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_46 | 82 | 82 | 82 | 82 | 82 |  |  |  |
| kernels.s | char_kernel_47 | 82 | 82 | 82 | 82 | 82 |  |  |  |
| kernels.s | char_kernel_48 | 82 | 82 | 82 | 82 | 82 |  |  |  |
| kernels.s | char_kernel_49 | 82 | 82 | 82 | 82 | 82 |  |  |  |
| kernels.s | char_kernel_50 | 82 | 82 | 82 | 82 | 82 |  |  |  |
| kernels.s | char_kernel_51 | 82 | 82 | 82 | 82 | 82 |  |  |  |
| kernels.s | char_kernel_52 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_53 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_54 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_55 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_56 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_57 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_58 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_59 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_60 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_61 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_62 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_63 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_64 | 89 | 89 | 89 | 89 | 89 |  |  |  |
| kernels.s | char_kernel_65 | 89 | 89 | 89 | 89 | 89 |  |  |  |
| kernels.s | char_kernel_66 | 89 | 89 | 89 | 89 | 89 |  |  |  |
| kernels.s | char_kernel_67 | 89 | 89 | 89 | 89 | 89 |  |  |  |
| kernels.s | char_kernel_68 | 89 | 89 | 89 | 89 | 89 |  |  |  |
| kernels.s | char_kernel_69 | 89 | 89 | 89 | 89 | 89 |  |  |  |
| kernels.s | char_kernel_70 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_71 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_72 | 169 | 169 | 169 | 169 | 169 |  |  |  |
| kernels.s | char_kernel_73 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_74 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_75 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_76 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_77 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_78 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_79 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_80 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_81 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_82 | 107 | 107 | 107 | 107 | 107 |  |  |  |
| kernels.s | char_kernel_83 | 107 | 107 | 107 | 107 | 107 |  |  |  |
| kernels.s | char_kernel_84 | 75 | 75 | 75 | 75 | 75 |  |  |  |
| kernels.s | char_kernel_85 | 75 | 75 | 75 | 75 | 75 |  |  |  |
| kernels.s | char_kernel_86 | 171 | 171 | 171 | 171 | 171 |  |  |  |
| kernels.s | char_kernel_87 | 139 | 139 | 139 | 139 | 139 |  |  |  |
| kernels.s | char_kernel_88 | 171 | 171 | 171 | 171 | 171 |  |  |  |
| kernels.s | char_kernel_89 | 139 | 139 | 139 | 139 | 139 |  |  |  |
| kernels.s | char_kernel_90 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_91 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_92 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_93 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_94 | 137 | 137 | 137 | 137 | 137 |  |  |  |
| kernels.s | char_kernel_95 | 169 | 169 | 169 | 169 | 169 |  |  |  |
| kernels.s | char_kernel_96 | 201 | 201 | 201 | 201 | 201 |  |  |  |
| kernels.s | char_kernel_97 | 233 | 233 | 233 | 233 | 233 |  |  |  |
| kernels.s | char_kernel_98 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_99 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_100 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_101 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_102 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_103 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_104 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_105 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_106 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_107 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_108 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_109 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_110 | 78 | 78 | 78 | 78 | 77 | missing parameter(s): latency.fence, latency.fence |  |  |
| kernels.s | char_kernel_111 | 78 | 78 | 78 | 78 | 77 | missing parameter(s): latency.fence, latency.fence |  |  |
| kernels.s | char_kernel_112 | 78 | 78 | 78 | 78 | 77 | missing parameter(s): latency.fence, latency.fence |  |  |
| kernels.s | char_kernel_113 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_114 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_115 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_116 | 74 | 74 | 74 | 74 | 74 |  |  |  |
| kernels.s | char_kernel_117 | 235 | 235 | 235 | 235 | 235 |  |  |  |
| kernels.s | char_kernel_118 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_119 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_120 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_121 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_122 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_123 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_124 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_125 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_126 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_127 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_128 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_129 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_130 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_131 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_132 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_133 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_134 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_135 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_136 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_137 | 395 | 395 | 395 | 395 | 395 |  |  |  |
| kernels.s | char_kernel_138 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_139 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_140 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_141 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_142 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_143 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_144 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_145 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_146 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_147 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_148 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_149 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_150 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_151 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_152 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_153 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_154 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_155 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_156 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_157 | 587 | 587 | 587 | 587 | 587 |  |  |  |
| kernels.s | char_kernel_158 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_159 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_160 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_161 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_162 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_163 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_164 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_165 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_166 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_167 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_168 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_169 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_170 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_171 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_172 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_173 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_174 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_175 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_176 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_177 | 587 | 587 | 587 | 587 | 587 |  |  |  |
| kernels.s | char_kernel_178 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_179 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_180 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_181 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_182 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_183 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_184 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_185 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_186 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_187 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_188 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_189 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_190 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_191 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_192 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_193 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_194 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_195 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_196 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_197 | 587 | 587 | 587 | 587 | 587 |  |  |  |
| kernels.s | char_kernel_198 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_199 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_200 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_201 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_202 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_203 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_204 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_205 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_206 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_207 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_208 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_209 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_210 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_211 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_212 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_213 | 843 | 843 | 843 | 843 | 843 |  |  |  |
| kernels.s | char_kernel_214 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_215 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_216 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_217 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_218 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_219 | 73 | 73 | 73 | 73 | 73 |  |  |  |
| kernels.s | char_kernel_220 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_221 | 105 | 105 | 105 | 105 | 105 |  |  |  |
| kernels.s | char_kernel_222 | 76 | 76 | 76 | 76 | 76 |  |  |  |
| kernels.s | char_kernel_223 | 77 | 77 | 77 | 77 | 77 |  |  |  |
| kernels.s | char_kernel_224 | 42 | 42 | 42 | 42 | 42 |  |  |  |
| kernels.s | char_kernel_225 | 43 | 43 | 43 | 43 | 43 |  |  |  |
| kernels.s | char_kernel_226 | 45 | 45 | 45 | 45 | 45 |  |  |  |
| kernels.s | char_kernel_227 | 43 | 43 | 43 | 43 | 43 |  |  |  |
| kernels.s | char_kernel_228 | 45 | 45 | 45 | 45 | 45 |  |  |  |
| kernels.s | char_kernel_229 | 49 | 49 | 49 | 49 | 49 |  |  |  |
| kernels.s | char_kernel_230 | 235 | 235 | 235 | 235 | 235 |  |  |  |
| kernels.s | char_kernel_231 | 235 | 235 | 235 | 235 | 235 |  |  |  |
| kernels.s | char_kernel_232 | 139 | 139 | 139 | 139 | 139 |  |  |  |
| kernels.s | char_kernel_233 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_234 | 139 | 139 | 139 | 139 | 139 |  |  |  |
| kernels.s | char_kernel_235 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_236 | 235 | 235 | 235 | 235 | 235 |  |  |  |
| kernels.s | char_kernel_237 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_238 | 235 | 235 | 235 | 235 | 235 |  |  |  |
| kernels.s | char_kernel_239 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_240 | 331 | 331 | 331 | 331 | 331 |  |  |  |
| kernels.s | char_kernel_241 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_242 | 331 | 331 | 331 | 331 | 331 |  |  |  |
| kernels.s | char_kernel_243 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_244 | 427 | 427 | 427 | 427 | 427 |  |  |  |
| kernels.s | char_kernel_245 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_246 | 427 | 427 | 427 | 427 | 427 |  |  |  |
| kernels.s | char_kernel_247 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_248 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_249 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_250 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_251 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_252 | 619 | 619 | 619 | 619 | 619 |  |  |  |
| kernels.s | char_kernel_253 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_254 | 619 | 619 | 619 | 619 | 619 |  |  |  |
| kernels.s | char_kernel_255 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_256 | 715 | 715 | 715 | 715 | 715 |  |  |  |
| kernels.s | char_kernel_257 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_258 | 715 | 715 | 715 | 715 | 715 |  |  |  |
| kernels.s | char_kernel_259 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_260 | 811 | 811 | 811 | 811 | 811 |  |  |  |
| kernels.s | char_kernel_261 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_262 | 811 | 811 | 811 | 811 | 811 |  |  |  |
| kernels.s | char_kernel_263 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_264 | 907 | 907 | 907 | 907 | 907 |  |  |  |
| kernels.s | char_kernel_265 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_266 | 907 | 907 | 907 | 907 | 907 |  |  |  |
| kernels.s | char_kernel_267 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_268 | 1003 | 1003 | 1003 | 1003 | 1003 |  |  |  |
| kernels.s | char_kernel_269 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_270 | 1003 | 1003 | 1003 | 1003 | 1003 |  |  |  |
| kernels.s | char_kernel_271 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_272 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_273 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_274 | 1099 | 1099 | 1099 | 1099 | 1099 |  |  |  |
| kernels.s | char_kernel_275 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_276 | 1195 | 1195 | 1195 | 1195 | 1195 |  |  |  |
| kernels.s | char_kernel_277 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_278 | 1195 | 1195 | 1195 | 1195 | 1195 |  |  |  |
| kernels.s | char_kernel_279 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_280 | 1291 | 1291 | 1291 | 1291 | 1291 |  |  |  |
| kernels.s | char_kernel_281 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_282 | 1291 | 1291 | 1291 | 1291 | 1291 |  |  |  |
| kernels.s | char_kernel_283 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_284 | 1387 | 1387 | 1387 | 1387 | 1387 |  |  |  |
| kernels.s | char_kernel_285 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_286 | 1387 | 1387 | 1387 | 1387 | 1387 |  |  |  |
| kernels.s | char_kernel_287 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_288 | 1483 | 1483 | 1483 | 1483 | 1483 |  |  |  |
| kernels.s | char_kernel_289 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_290 | 1483 | 1483 | 1483 | 1483 | 1483 |  |  |  |
| kernels.s | char_kernel_291 | 299 | 299 | 299 | 299 | 299 |  |  |  |
| kernels.s | char_kernel_292 | 1579 | 1579 | 1579 | 1579 | 1579 |  |  |  |
| kernels.s | char_kernel_293 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_294 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_295 | 203 | 203 | 203 | 203 | 203 |  |  |  |
| kernels.s | char_kernel_296 | 1675 | 1675 | 1675 | 1675 | 1675 |  |  |  |
| kernels.s | char_kernel_297 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_298 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_299 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_300 | 1771 | 1771 | 1771 | 1771 | 1771 |  |  |  |
| kernels.s | char_kernel_301 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_302 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_303 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_304 | 1867 | 1867 | 1867 | 1867 | 1867 |  |  |  |
| kernels.s | char_kernel_305 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_306 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_307 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_308 | 1963 | 1963 | 1963 | 1963 | 1963 |  |  |  |
| kernels.s | char_kernel_309 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_310 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_311 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_312 | 2059 | 2059 | 2059 | 2059 | 2059 |  |  |  |
| kernels.s | char_kernel_313 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_314 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_315 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_316 | 2155 | 2155 | 2155 | 2155 | 2155 |  |  |  |
| kernels.s | char_kernel_317 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_318 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_319 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_320 | 2251 | 2251 | 2251 | 2251 | 2251 |  |  |  |
| kernels.s | char_kernel_321 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_322 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_323 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_324 | 2347 | 2347 | 2347 | 2347 | 2347 |  |  |  |
| kernels.s | char_kernel_325 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_326 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_327 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_328 | 2443 | 2443 | 2443 | 2443 | 2443 |  |  |  |
| kernels.s | char_kernel_329 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_330 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_331 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_332 | 2539 | 2539 | 2539 | 2539 | 2539 |  |  |  |
| kernels.s | char_kernel_333 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_334 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_335 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_336 | 2635 | 2635 | 2635 | 2635 | 2635 |  |  |  |
| kernels.s | char_kernel_337 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_338 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_339 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_340 | 2731 | 2731 | 2731 | 2731 | 2731 |  |  |  |
| kernels.s | char_kernel_341 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_342 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_343 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_344 | 2827 | 2827 | 2827 | 2827 | 2827 |  |  |  |
| kernels.s | char_kernel_345 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_346 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_347 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_348 | 2923 | 2923 | 2923 | 2923 | 2923 |  |  |  |
| kernels.s | char_kernel_349 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_350 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_351 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_352 | 3019 | 3019 | 3019 | 3019 | 3019 |  |  |  |
| kernels.s | char_kernel_353 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_354 | 1643 | 1643 | 1643 | 1643 | 1643 |  |  |  |
| kernels.s | char_kernel_355 | 459 | 459 | 459 | 459 | 459 |  |  |  |
| kernels.s | char_kernel_356 | 3115 | 3115 | 3115 | 3115 | 3115 |  |  |  |
| kernels.s | char_kernel_357 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_358 | 1803 | 1803 | 1803 | 1803 | 1803 |  |  |  |
| kernels.s | char_kernel_359 | 363 | 363 | 363 | 363 | 363 |  |  |  |
| kernels.s | char_kernel_360 | 3211 | 3211 | 3211 | 3211 | 3211 |  |  |  |
| kernels.s | char_kernel_361 | 523 | 523 | 523 | 523 | 523 |  |  |  |
| kernels.s | char_kernel_362 | 1803 | 1803 | 1803 | 1803 | 1803 |  |  |  |
| kernels.s | char_kernel_363 | 619 | 619 | 619 | 619 | 619 |  |  |  |
| x87test.s | f | 15 | 15 | 15 | 15 | 15 |  |  |  |
| x87test.s | g | 92 | 92 | 92 | 92 | 92 |  | .L6: 55, yes, yes; .L7: 7, yes, yes; .L8: 7, yes, yes |  |
| x87test.s | h | 124 | 124 | 124 | 124 | 124 |  | .L16: 90, yes, yes; .L17: 9, yes, yes; .L18: 9, yes, yes |  |

Totals: 455 functions, 219772 instructions; 357 innermost loops with 7209 instructions, 357 loops complete for functional execution, 341 complete for timing (5751 instructions).
