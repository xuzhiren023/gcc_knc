// S4-05 / ADR-0007 point 7: aligned loops (no peel) end in a masked IMCI
// epilogue: a GPR mask moved to k, guarded masked moves, cond_<op>, and no
// x87 remainder.  Unknown alignment keeps the x87 remainder.  The last
// label or jump before each masked memory move is its empty-mask guard
// (jkzd, or je/jz after a byte test) or the label a jknzd/jne guard
// branches to; never another jump, ret or the function entry.
// options: -O2 -ftree-vectorize
// scan-asm-func add_al_f32: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func add_al_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func add_al_f32: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func add_al_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func add_al_f32: \bjkn?zd\s
// scan-asm-func add_al_f32: \A(?![\s\S]*^(?!\s*jkzd\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovaps\s[^\n]*\([^\n]*\{%k)
// scan-asm-func add_al_f32: \A(?![\s\S]*\bfld)
// scan-asm-func add_al_f64: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func add_al_f64: \bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func add_al_f64: \bvaddpd\s[^\n]*\{%k[1-7]\}
// scan-asm-func add_al_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func add_al_f64: \btestb\s+%(\w+),\s*%\1\s*$
// scan-asm-func add_al_f64: \A(?![\s\S]*^(?!\s*j[ez]\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovapd\s[^\n]*\([^\n]*\{%k)
// scan-asm-func add_al_f64: \A(?![\s\S]*\bjkn?zd)
// scan-asm-func add_al_f64: \A(?![\s\S]*\bfld)
// scan-asm-func add_al_i32: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func add_al_i32: \bvmovdqa32\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func add_al_i32: \bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func add_al_i32: \bjkn?zd\s
// scan-asm-func add_al_i32: \A(?![\s\S]*^(?!\s*jkzd\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovdqa32\s[^\n]*\([^\n]*\{%k)
// scan-asm-func affine_al_f32: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func affine_al_f32: \bvfmadd231ps\s[^\n]*\{%k[1-7]\}
// scan-asm-func affine_al_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func affine_al_f32: \A(?![\s\S]*\bv(?:mul|add)ps\s)
// scan-asm-func affine_al_f32: \A(?![\s\S]*^(?!\s*jkzd\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovaps\s[^\n]*\([^\n]*\{%k)
// scan-asm-func affine_al_f32: \A(?![\s\S]*\bf(?:add|mul)[sl]?\s)
// scan-asm-func affine_al_f64: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func affine_al_f64: \bvfmadd231pd\s[^\n]*\{%k[1-7]\}
// scan-asm-func affine_al_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func affine_al_f64: \A(?![\s\S]*\bv(?:mul|add)pd\s)
// scan-asm-func affine_al_f64: \A(?![\s\S]*^(?!\s*j[ez]\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovapd\s[^\n]*\([^\n]*\{%k)
// scan-asm-func affine_al_f64: \A(?![\s\S]*\bjkn?zd)
// scan-asm-func affine_al_f64: \A(?![\s\S]*\bf(?:add|mul)[sl]?\s)
// scan-asm-func mul_al_f32: \bvmulps\s[^\n]*\{%k[1-7]\}
// scan-asm-func mul_al_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func mul_al_f32: \A(?![\s\S]*\bfld)
// scan-asm-func cst_al_f32: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func cst_al_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_al_f32: \A(?![\s\S]*^(?!\s*jkzd\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovaps\s[^\n]*\([^\n]*\{%k)
// scan-asm-func cst_al_f32: \A(?![\s\S]*\bfld)
// scan-asm-func add_f32: \bflds\s
// scan-asm-func add_f32: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-not: %(?:xmm|ymm)\d
#include "knc-mask-tail.h"
