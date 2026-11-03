// S1-06: donor linuxk1om.h ABI, x87 precision in 16-byte storage.
_Static_assert(__LDBL_MANT_DIG__ == 64, "KNC long double has x87 precision");
_Static_assert(__SIZEOF_LONG_DOUBLE__ == 16, "KNC long double occupies 16 bytes");
_Static_assert(__SIZEOF_FLOAT128__ == 16, "KNC float128 occupies 16 bytes");
_Static_assert(sizeof(long double) == 16, "long double storage matches its macro");
int knc_link_defaults(void) { return 0; }
