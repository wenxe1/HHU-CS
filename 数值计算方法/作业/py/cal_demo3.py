x0 = 4
n = 1
while True:
    x1 = 4/5*x0 + 235.4/5*pow(x0, -4)
    print("x[%d] = %.5lf" % (n, x1))
    print("x[%d] = %lf" % (n, x1))
    if abs(x1 - x0) < 1/2 * 1e-4:
        break
    n += 1
    x0 = x1