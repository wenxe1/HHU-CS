tic;    % 掐表计时
eps = 5e-6;
x0 = 1.4;
x1 = 1.6;
n = 0;
while(1)
    x2 = x1 - f(x1) / (f(x1) - f(x0)) *(x1 - x0);
    n = n + 1;
    if(abs(x1 - x0) < eps)
        break;
    end
    x0 = x1;
    x1 = x2;
end
fprintf('n = %d\nx0 = %f\n', n, x0);
toc;    % 掐表输出
function y = f(x)
    y = x * x - 2; 
end