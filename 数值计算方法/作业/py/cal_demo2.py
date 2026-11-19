x0 = 1.5
n = 1
while True:
    x1 = pow(1+pow(x0, 2), 1/3)
    print("x%d = %.5lf" % (n, x1))
    if abs(x1 - x0) < 1/2 * 1e-4:
        break
    x0 = x1
    n += 1