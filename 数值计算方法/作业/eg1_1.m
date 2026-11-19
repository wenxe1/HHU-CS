% method1
y0 = log(6.0 / 5.0);
fprintf('y[%d]=%f\n', 0, y0)
n = 1;
while(1)
    y1 = 1.0/n-5*y0;
    fprintf('y[%d]=%f\n', n, y1);
    if(n >= 40) 
        break;
    end
    y0 = y1;
    n = n + 1;
end

% method2
% y0 = (1/205 + 1/246) / 2;
% n = 40;
% fprintf('y[%d]= %f\n', n, y0);
% while(1)
%     y1 = 1/(5*n) - y0/5;
%     fprintf('y[%d]=%f\n', n-1, y1);
%     if(n <= 1)
%         break;
%     end
%     y0 = y1;
%     n = n - 1;
% end