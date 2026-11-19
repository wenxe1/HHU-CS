# method1
import math

y0 = math.log(6 / 5)
print("y[0] = %lf" % (y0))
n = 1
while(n <= 40):
    y1 = 1/n -5*y0
    print("y[%d] = %lf" % (n, y1))
    y0 = y1
    n += 1

#method2
y1 = 1/2 * (1/205 + 1/246)
n = 40
print("y[40] = %lf" % (y1))
while(n-1 >= 0):
    y0 = 1/(5*n) - 1/5*y1
    print("y[%d] = %lf" % (n-1, y0))
    y1 = y0
    n -= 1