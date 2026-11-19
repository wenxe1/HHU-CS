# method1
n = 1
sum = 0
while(n <= 10000):
    sum += pow(n, -2)
    n += 1
print("sum1 = %.30lf" % (sum))

# method2
n = 10000
sum = 0
while(n >= 1):
    sum += pow(n, -2)
    n -= 1
print("sum2 = %.30lf" % (sum))