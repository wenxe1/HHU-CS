eps = 5e-4;
delta = 1e-4;
x0 = 3;
n = 0;
N = 100;
while(1)
    x1 = 4/5*x0 + 1177/25*power(x0, -4);
    n = n + 1;
    if(n > N)
        break;
    end
    if(abs(x1 - x0) < eps || 4/5*x1 + 1177/25*power(x1, -4) < delta)
        fprintf('%.3f', x1);
        break;
    end
    if(abs(5*power(x1, 5-1)) < delta)
        break;
    end
    x0 = x1;
end