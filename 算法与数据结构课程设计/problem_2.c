#include <stdio.h>

void print(int* maze, int n, int m) {
	for(int i = 0; i < n; i++) {
        for(int j = 0; j < m; j++) {
			if(maze[i * m + j] == 2)
				printf("* ");
			else if(maze[i * m + j] == 1) 
				printf("# ");
			else
				printf("  ");
        }
        printf("\n");
    }
}

int findPath(int* maze, int n, int m, int x, int y, int endX, int endY) {	
	maze[x * m + y] = 2;
	if(x == endX && y == endY) {
        maze[x*m + y] = 2;
        return 1;
    }
	
	int dx[4] = {-1, 0, 1, 0}, dy[4] = {0, 1, 0, -1};
	for(int i = 0; i < 4; i++) {
		int nx = x + dx[i], ny = y + dy[i];
		if(nx >= 0 && nx <n && ny >= 0 && ny < m && maze[nx * m + ny] == 0) {
			if(findPath(maze, n, m, nx, ny, endX, endY))
				return 1;
			maze[nx * m + ny] = 0; 
		}
	}
	
    return 0;
}

int main() {
	// 墙壁为1，路为0，出口为边界上的0，走过的路为2 
	int maze[6][6] = {
						{1, 1, 1, 1, 1, 1},
						{1, 0, 0, 0, 1, 1},
						{1, 0, 1, 0, 0, 0},
				  		{1, 0, 1, 1, 1, 1},
						{1, 0, 0, 0, 0, 1},
						{1, 1, 1, 1, 1, 1}
					};

	int startX = 1, startY = 1;
	int endX = 2, endY = 5;
	
	if(findPath(maze, 6, 6, startX, startY, endX, endY))
		// 墙壁为#，找到的路径为* 
		print(maze, 6, 6);
	else
		printf("");
	
	return 0;
} 
