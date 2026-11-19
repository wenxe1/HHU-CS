#include <stdio.h>
#include <stdlib.h>
#include <limits.h>

#define INF INT_MAX

typedef struct {
    int numV;        
    char* names[8];          
    int adjM[8][8];    
} Graph;

typedef struct {
    int length;  // 从起点到此点的最短路径长度
    int preV;  // 最短路径上的前一个节点
} Path;

void printPath(Path dist[], int start, int curNode, char* names[]) {
    if(curNode == start || dist[curNode].preV == -1) {
        printf("%s", names[curNode]);
        return;
    }
    printPath(dist, start, dist[curNode].preV, names);
    printf(" -> %s", names[curNode]);
}

void dijkstra(Graph* g, int start, int end) {
    // 初始化 
	Path dist[8];  // 存储到各点的最短距离和前驱
    int visited[8];  
    for(int i = 0; i < g->numV; i++) {
        dist[i].length = g->adjM[start][i];  // 从起点到各点的直接距离
        if(dist[i].length != INF) 
            dist[i].preV = start;  // 如果直连，前驱是起点
        else
            dist[i].preV = -1; 
        visited[i] = 0;
    }
    dist[start].length = 0;
    dist[start].preV = -1; 
    visited[start] = 1;  

    // 循环 8-1 次，每次确定一个最短路径
    for(int i = 0; i < g->numV - 1; i++) {
        int minDist = INF, minNode = -1;

        // 找到未访问节点中，距离起点最近的节点minNode（初始化为-1） 
        for(int j = 0; j < g->numV; j++) {
            if(!visited[j] && dist[j].length < minDist) {
                minDist = dist[j].length;
                minNode = j;
            }
        }

        // 如果找不到（图不连通），则退出
        if(minNode == -1) break;
		
        visited[minNode] = 1;
        // 更新minNode的所有邻居的距离
        for(int j = 0; j < g->numV; j++) {
            // 如果j未访问，且通过minNode到j的路径更短
            if(!visited[j] && g->adjM[minNode][j] != INF &&
                	(dist[minNode].length + g->adjM[minNode][j] < dist[j].length)) {
                dist[j].length = dist[minNode].length + g->adjM[minNode][j];  // 更新距离
                dist[j].preV = minNode;  // 更新前驱
            }
        }
    }
	
	printf("最短路径为:\n");
    printPath(dist, start, end, g->names);
    printf("\n总距离为: %d\n", dist[end].length);
}

int main() {
	char* names[8] = {
        "计算机院", "电气院", "图书馆", "会议中心",
        "体育场", "理学院", "力学院", "公管院"
    };

	// 不临接为INF，自己为0 
    int adjM[8][8] = {
		{  0,   2, INF, INF,   3, INF, INF, INF}, 
	    {  2,   0,   2, INF, INF,   4, INF, INF},
	    {INF,   2,   0,   2, INF,   2, INF, INF}, 
	    {INF, INF,   2,   0,   3, INF, INF, INF},
	    {  3, INF, INF,   3,   0, INF, INF, INF}, 
	    {INF,   4,   2, INF, INF,   0, INF,   4}, 
	    {INF, INF, INF, INF, INF, INF,   0,   1}, 
	    {INF, INF, INF, INF, INF,   4,   1,   0}
    };
	Graph hhu;
    hhu.numV = 8;
    for(int i = 0; i < 8; i++) {
        hhu.names[i] = names[i];
        for(int j = 0; j < 8; j++) {
            hhu.adjM[i][j] = adjM[i][j];
        }
    }
    while(1) {
    	printf("----------------------------------------\n");
	    printf("部门列表:\n");
	    for(int i = 0; i < 8; i++) {
	        printf("%d.%s ", i, hhu.names[i]);
	        if(i == 3) puts("");
	    }
	    int start, end;
	    printf("\n请输入起点编号: ");
	    scanf("%d", &start);
	    printf("请输入终点编号: ");
	    scanf("%d", &end);
	    dijkstra(&hhu, start, end);
	}
	
	return 0;
}
