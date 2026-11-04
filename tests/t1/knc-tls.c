/* S3-14: unforced TLS models must agree with the donor ABI, including PIC. */
__thread int tv;
extern __thread int te;

int read_defined(void)
{
  return tv;
}

int read_external(void)
{
  return te;
}
