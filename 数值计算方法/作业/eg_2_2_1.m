eps = 5e-6;
delta = 1e-6;
a = 1;
b = 2;
fa = f2_1(a);
fb = f2_1(b);
n = 1;
while (1)
    if(fa * fb > 0)
        break;
    end
    
    c = (a + b) / 2;
    fc = f2_1(c);
    if(abs(fc) < delta)
        break;
    elseif(fa * fc < 0)
        b = c;
        fb = fc;
    else
        a = c;
        fa = fc;
    end
    if(b - a < eps)
        break;
    end
    fprintf('n=%d c=%f fc=%f\n', n, c, fc);
    n = n + 1;
end

function output = f2_1(x)
    output = x * x * x + 4 * x * x - 10;
end