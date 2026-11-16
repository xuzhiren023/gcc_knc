/* Independent host reference for PolyBench 4.2.1 inputs, S13-01.
   Compile with host cc -O0 -ffp-contract=off. No benchmark or donor code is
   linked here. Initialization formulas and live-out shapes follow each
   package program's init_array/print_array; algorithms below are independent.
   Output belongs in the program's ordinary or sealed reference directory. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static double *allocate(size_t n) {
  double *p = calloc(n, sizeof *p);
  if (!p) exit(2);
  return p;
}
static double lower(int row, int col, int n) {
  return row < col ? 0. : row == col ? 1. : 1. - (double)col/n;
}
static void output(const char *name, double *x, size_t count) {
  size_t i;
  printf("[{\"array\":\"%s\",\"values\":[", name);
  for (i=0; i<count; ++i) {
    if (!isfinite(x[i])) exit(3);
    printf("%s%.17g", i ? "," : "", x[i]);
  }
  puts("]}]");
}
/* Thomas elimination on a complete tridiagonal system with unit endpoints.
   RHS formation and solution are separate from the benchmark's fused sweeps. */
static void solve(int n, double off, double diag, double *rhs, double *x) {
  double *d = allocate(n), *v = allocate(n);
  int j;
  d[1] = diag; v[1] = rhs[1] - off;
  for (j=2; j<n-1; ++j) {
    double factor = off/d[j-1];
    d[j] = diag - factor*off;
    v[j] = rhs[j] - factor*v[j-1];
  }
  x[0] = x[n-1] = 1.;
  for (j=n-2; j>0; --j) x[j] = (v[j]-off*x[j+1])/d[j];
  free(d); free(v);
}
int main(int argc, char **argv) {
  int n, m, steps, i, j, k, t;
  size_t count;
  double *out, *a, *b;
  const char *name = "A", *program;
  if (argc != 5) return 2;
  program=argv[1]; n=atoi(argv[2]); m=atoi(argv[3]); steps=atoi(argv[4]);
  if (n<3 || m<3 || steps<1) return 2;
  count=(!strcmp(program,"durbin") || !strcmp(program,"atax") || !strcmp(program,"ludcmp")) ? n : (size_t)n*n;
  out=allocate(count); a=allocate(count); b=allocate(count);
  if (!strcmp(program,"gemm")) {
    name="C";
    for (i=0; i<n; ++i) for (j=0; j<n; ++j) {
      double value=1.2*((i*j+1)%n)/(double)n;
      for (k=0; k<n; ++k)
        value += 1.5*((i*(k+1))%n)/(double)n * ((k*(j+2))%n)/(double)n;
      out[i*n+j]=value;
    }
  } else if (!strcmp(program,"atax")) {
    name="y"; count=n;
    for (i=0; i<m; ++i) {
      double dot=0.;
      for (j=0; j<n; ++j) dot += ((i+j)%n)/(5.*m)*(1.+j/(double)n);
      for (j=0; j<n; ++j) out[j] += ((i+j)%n)/(5.*m)*dot;
    }
  } else if (!strcmp(program,"cholesky")) {
    /* The input is L L^T, with positive unit diagonal L. Its unique
       Cholesky factor is therefore the independently initialized L itself. */
    count=0;
    for (i=0; i<n; ++i) for (j=0; j<=i; ++j) out[count++]=lower(i,j,n);
  } else if (!strcmp(program,"ludcmp")) {
    /* Solve L z = rhs, L^T x = z instead of the tested LU decomposition. */
    name="x"; count=n;
    for (i=0; i<n; ++i) {
      double value=(i+1)/(double)n/2.+4.;
      for (j=0; j<i; ++j) value -= lower(i,j,n)*a[j];
      a[i]=value;
    }
    for (i=n-1; i>=0; --i) {
      double value=a[i];
      for (j=i+1; j<n; ++j) value -= lower(j,i,n)*out[j];
      out[i]=value;
    }
  } else if (!strcmp(program,"jacobi-2d")) {
    for (i=0; i<n; ++i) for (j=0; j<n; ++j) {
      a[i*n+j]=(i*(double)(j+2)+2.)/n;
      b[i*n+j]=(i*(double)(j+3)+3.)/n;
    }
    for (t=0; t<2*steps; ++t) {
      double *src=t%2 ? b:a, *dst=t%2 ? a:b;
      for (i=1; i<n-1; ++i) for (j=1; j<n-1; ++j) {
        int index=i*n+j;
        dst[index]=(src[index]+src[index-1]+src[index+1]+src[index+n]+src[index-n])*0.2;
      }
    }
    memcpy(out,a,count*sizeof *a);
  } else if (!strcmp(program,"heat-3d")) {
    size_t stride=(size_t)n*n, index;
    count=stride*n;
    free(a); free(b); free(out);
    a=allocate(count); b=allocate(count); out=allocate(count);
    for (i=0; i<n; ++i) for (j=0; j<n; ++j) for (k=0; k<n; ++k)
      a[i*stride+j*n+k]=b[i*stride+j*n+k]=(i+j+(n-k))*10./n;
    for (t=0; t<2*steps; ++t) {
      double *src=t%2 ? b:a, *dst=t%2 ? a:b;
      for (i=1; i<n-1; ++i) for (j=1; j<n-1; ++j) for (k=1; k<n-1; ++k) {
        index=i*stride+j*n+k;
        dst[index]=src[index]+0.125*(src[index+stride]-2.*src[index]+src[index-stride])
          +0.125*(src[index+n]-2.*src[index]+src[index-n])
          +0.125*(src[index+1]-2.*src[index]+src[index-1]);
      }
    }
    memcpy(out,a,count*sizeof *a);
  } else if (!strcmp(program,"adi")) {
    double dx=1./n, dt=1./steps;
    double mx=2.*dt/(dx*dx), my=dt/(dx*dx);
    double *rhs=allocate(n), *solution=allocate(n);
    name="u";
    for (i=0; i<n; ++i) for (j=0; j<n; ++j) a[i*n+j]=(i+(double)n-j)/n;
    for (t=0; t<steps; ++t) {
      for (i=1; i<n-1; ++i) {
        for (j=1; j<n-1; ++j)
          rhs[j]=(my/2.)*a[j*n+i-1]+(1.-my)*a[j*n+i]+(my/2.)*a[j*n+i+1];
        solve(n,-mx/2.,1.+mx,rhs,solution);
        for (j=0; j<n; ++j) b[j*n+i]=solution[j];
      }
      for (i=1; i<n-1; ++i) {
        for (j=1; j<n-1; ++j)
          rhs[j]=(mx/2.)*b[(i-1)*n+j]+(1.-mx)*b[i*n+j]+(mx/2.)*b[(i+1)*n+j];
        solve(n,-my/2.,1.+my,rhs,solution);
        for (j=0; j<n; ++j) a[i*n+j]=solution[j];
      }
    }
    memcpy(out,a,count*sizeof *a); free(rhs); free(solution);
  } else if (!strcmp(program,"durbin")) {
    double reflection=-(n+1.), energy=1.;
    name="y"; count=n; out[0]=reflection;
    for (k=1; k<n; ++k) {
      double dot=0.;
      energy *= 1.-reflection*reflection;
      for (j=0; j<k; ++j) dot += (n+1.-(k-j-1))*out[j];
      reflection=-(n+1.-k+dot)/energy;
      memcpy(a,out,k*sizeof *out);
      for (j=0; j<k; ++j) out[j]=a[j]+reflection*a[k-j-1];
      out[k]=reflection;
    }
  } else return 2;
  output(name,out,count);
  free(out); free(a); free(b);
  return ferror(stdout) ? 2 : 0;
}
