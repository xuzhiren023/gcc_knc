/* S2-02: shared declarations, separate donor/GCC 16 translation units. */
struct df { double d; float f; };
struct ff { float a, b; };
float scalar_f(float);
double scalar_d(double);
double scalar_mixed(int, float, long, double, int, float);
float scalar_ten_f(float,float,float,float,float,float,float,float,float,float);
double scalar_ten_d(double,double,double,double,double,double,double,double,double,double);
struct df scalar_df(struct df);
struct ff scalar_ff(struct ff);
double scalar_callback(double (*)(double), double);
