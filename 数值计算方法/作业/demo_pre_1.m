tic;    % 掐表计时
eps = 5e-6;
a = 1; b = 2; n = 0;
while(1)
    % 计算区间中点x0，并更新边界
    x0 = (a + b) / 2;
    if(f(a) * f(x0) < 0)
        b = x0;
    else
        a = x0;
    end
    % 精度判断
    if(b - a < eps)
        break;
    end
    n = n + 1;
end
fprintf('n = %d\nans = %f\n', n, x0);
toc;    % 掐表输出
function y = f(x)
    y = x * x - 2;
end