eps = 5e-4;
delta = 1e-4;
x0 = 1.5;
n = 0;
N = 100;
while(1)
    x1 = power(1+x0*x0, 1/3);
    n = n + 1;
    if(n > N)
        break;
    end
    if(abs(x1 - x0) < eps || power(1+x1*x1, 1/3) < delta)
        fprintf('%.3f', x1);
        break;
    end
    x0 = x1;
end