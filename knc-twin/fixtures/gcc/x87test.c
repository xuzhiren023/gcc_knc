void f(const double *p, double *out) {
    out[0] = (p[0] - p[1]) / p[2] + p[0] * p[1];
    out[1] = p[2] - p[0] * p[1];
}
float g(const float *x, int n) {
    float s = 0.0f;
    for (int i = 0; i < n; i++) s += x[i] * x[i];
    return s;
}
void h(int *a, const int *b, int n) {
    for (int i = 0; i < n; i++) a[i] = b[i] * 3 + (b[i] >> 2);
}
