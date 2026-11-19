x=[2.5 7.5 10];
y=[4.0 7.0 5.0];
df_x0 = 0.13;
df_x2 = -0.13;

% 绘图
pp = csape(x, y, 'clamped', [df_x0, df_x2]);
xx = linspace(min(x), max(x), 1000);
yy = ppval(pp, xx);

plot(x, y, 'bo', xx, yy, 'b-');
xlabel('x');
ylabel('y');
title('三次样条插值');

% 提取系数
coeffs = pp.coefs;
breaks = pp.breaks;

% 打印公式
for i = 1:size(coeffs, 1)
    a = coeffs(i, 1); % x^3 的系数
    b = coeffs(i, 2); % x^2 的系数
    c = coeffs(i, 3); % x^1 的系数
    d = coeffs(i, 4); % 常数项
    fprintf('在区间 [%.1f, %.1f] 的插值公式: ', breaks(i), breaks(i + 1));
    fprintf('P%d(x) = %.4f * (x - %.1f)^3 + %.4f * (x - %.1f)^2 + %.4f * (x - %.1f) + %.4f\n', ...
        i, a, breaks(i), b, breaks(i), c, breaks(i), d)
end