eps = 5e-6;
delta = 1e-6;
N = 100;
k = 0;
x0 = 1.0;
while(1)
    x1 = x0 - func2_2(x0) / func2_2_1(x0);
    k = k + 1;
    if(k > N)
        disp('failed')
        break;
    end
    if(abs(x1 - x0) < eps || abs(func2_2(x1)) < delta)
        fprintf('%f', x1);
        break;
    end
    if(abs(func2_2_1(x0)) < delta)
        break;
    end
    x0 = x1;
end

function y = func2_2(x)
    y = x * x * x + x * x - 3 * x - 3;
end

function y = func2_2_1(x)
    y = 3 * x * x + 2 * x - 3;
end