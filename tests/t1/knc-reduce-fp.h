/* Same source for reassociated trees and the strict in-order folds.  */
float
sum_f32 (const float *a, int n)
{
  float r = 0;
  for (int i = 0; i < n; ++i)
    r += a[i];
  return r;
}

double
sum_f64 (const double *a, int n)
{
  double r = 0;
  for (int i = 0; i < n; ++i)
    r += a[i];
  return r;
}
