# y0 = 0
# h = 0.2
#
# for i in range(0, 5):
#     x0 = i * h
#     y1 = y0 + 2 * x0 * (1 - y0)
#     print("y{} = {}".format(i+1, y1))
#     y0 = y1

y0 = 0
h = 0.2

for i in range(0, 5):
    x0 = i * h
    x1 = x0 + h
    y1 = y0 + 2 * x0 * (1 - y0)
    y2 = y0 + x0 * (1 - y0) + x1 * (1 - y1)
    print("y%d = %lf" % (i+1, y2))
    y0 = y2

# import numpy as np
#
# A0 = np.array([[7, 3, -2], [3, 4, -1], [-2, -1, 3]])
# V0 = np.array([[1], [1], [1]])
# U0 = V0
# i = 1
#
# while True:
#     V1 = A0 @ U0
#     print("V{} = {}".format(i, V1))
#
#     U1 = V1 / np.max(V1)
#     print("U{} = {}".format(i, U1))
#
#     if abs(np.max(V1) - np.max(V0)) < 1e-2:
#         print(np.max(V1))
#         print(np.max(V0))
#         print(abs(np.max(V1) - np.max(V0)))
#         print(U1)
#         break
#
#     i = i + 1
#     U0 = U1
#     V0 = V1