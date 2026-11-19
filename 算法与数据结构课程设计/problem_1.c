#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char name[10];
    int x;
    int y;
} City;

typedef struct Node {
    City data;
    struct Node* next;
} Node;

Node* findCityByName(Node* head, char* name);
Node* findCityByCoords(Node* head, int x, int y);
int insertCity(Node* head, char* name, int x, int y);
int deleteCityByName(Node* head, char* name);
int deleteCityByCoords(Node* head, int x, int y);
int updateCityByName(Node* head, char* oldName, char* newName, int newX, int newY);
int updateCityByCoords(Node* head, int oldX, int oldY, char* newName, int newX, int newY);

int main() { 
	Node* cityList = (Node*)malloc(sizeof(Node));  // 头结点不存储数据 
    cityList->next = NULL; 
    
	insertCity(cityList, (char*)"南京", 119, 32);  // 经纬度四舍五入为整数 
	insertCity(cityList, (char*)"常州", 120, 32);
	insertCity(cityList, (char*)"北京", 116, 40);
	insertCity(cityList, (char*)"厦门", 118, 24);
	insertCity(cityList, (char*)"深圳", 114, 23);
	insertCity(cityList, (char*)"丽江", 100, 27);
	insertCity(cityList, (char*)"昆明", 103, 25);
	
	// 1 上海 121 31
	// 2 上海 
	// 3 121 31
	// 4 常州 
	// 5 118 24
	// 6 昆明 厦门 118 24 
	// 7 118 24 昆明 103 25 
	// 0 
	while(1) {
		printf("---------------------------------------------------\n");
		printf("菜单：\n"); 
		printf("0.退出程序   1.插入城市   2.用名字查找 3.用坐标查找\n"); 
		printf("4.用名字删除 5.用坐标删除 6.用名字更新 7.用坐标更新\n"); 
		printf("请输入您想进行的操作：");
		int choice = 0;
		scanf("%d", &choice);
		while(getchar() != '\n');
		char name[11], newName[11];
		int x, y, newX, newY;
		Node* foundNode = NULL;
		switch(choice) {
			case 1:
				printf("请输入城市名字: ");
				scanf("%10s", name);
				printf("请输入城市坐标 (x y): ");
				scanf("%d %d", &x, &y);
				if(insertCity(cityList, name, x, y)) 
					printf("插入成功\n");
				else
					printf("插入失败\n");
				break;
			case 2:
				printf("请输入要查找的城市名字: ");
				scanf("%10s", name);
				foundNode = findCityByName(cityList, name);
				if(foundNode) 
					printf("查找成功: %s (%d, %d)\n", foundNode->data.name, foundNode->data.x, foundNode->data.y);
				else
					printf("查找失败\n");
				break;
			case 3:
				printf("请输入要查找的城市坐标 (x y): ");
				scanf("%d %d", &x, &y);
				foundNode = findCityByCoords(cityList, x, y);
				if(foundNode)
					printf("找查找成功: %s (%d, %d)\n", foundNode->data.name, foundNode->data.x, foundNode->data.y);
				else
					printf("查找失败\n");
				break;
			case 4:
				printf("请输入要删除的城市名字: ");
				scanf("%10s", name);
				if(deleteCityByName(cityList, name)) 
					printf("删除成功\n");
				else
					printf("删除失败\n");
				break;
			case 5:
				printf("请输入要删除的城市坐标 (x y): ");
				scanf("%d %d", &x, &y);
				if(deleteCityByCoords(cityList, x, y)) 
					printf("删除成功\n");
				else
					printf("删除失败\n");
				break;
			case 6:
				printf("请输入要更新的城市名字: ");
				scanf("%10s", name);
				printf("请输入新的城市名字:");
				scanf("%10s", newName);
				printf("请输入新的城市坐标 (x y): ");
				scanf("%d %d", &newX, &newY);;
				if(updateCityByName(cityList, name, newName, newX, newY))
					printf("更新成功\n");
				else
					printf("更新失败\n");
				break;
			case 7:
				printf("请输入要更新的城市坐标 (x y): ");
				scanf("%d %d", &x, &y);
				printf("请输入新的城市名字: ");
				scanf("%10s", newName);
				printf("请输入新的城市坐标 (x y): ");
				scanf("%d %d", &newX, &newY);
				if(updateCityByCoords(cityList, x, y, newName, newX, newY)) 
					printf("更新成功\n");
				else
					printf("更新失败\n");
				break;
			case 0:
				return 0;
		}
	}	
	return 0;
}

Node* findCityByName(Node* head, char* name) {
	if(head == NULL || head->next == NULL)
		return NULL;
	Node* p = head;
    while(p->next != NULL) {
    	p = p->next;
        if(strcmp(p->data.name, name) == 0)
            return p;
    }
    return NULL;
}

Node* findCityByCoords(Node* head, int x, int y) {
	if(head == NULL || head->next == NULL)
		return NULL;
	Node* p = head;
    while(p->next != NULL) {
    	p = p->next;
        if(p->data.x == x && p->data.y == y)
            return p;
    }
    return NULL;
}

int insertCity(Node* head, char* name, int x, int y) {
	Node* newCity = (Node*)malloc(sizeof(Node));
    if(newCity == NULL || head == NULL) 
		return 0;
    strcpy(newCity->data.name, name);
    newCity->data.x = x;
    newCity->data.y = y;
    newCity->next = NULL;
	Node* p = head;
	while(p->next != NULL) {
		p = p->next;
	}
	p->next = newCity;
	return 1;
}


int deleteCityByName(Node* head, char* name) {
	if(head == NULL || head->next == NULL)
		return 0;
	Node* pre = NULL;
	Node* p = head;
    while(p->next != NULL) {
    	pre = p;
		p = p->next;
        if(strcmp(p->data.name, name) == 0) {
        	pre->next = p->next;
        	free(p);
        	return 1;	
		}
    }
    return 0;
}

int deleteCityByCoords(Node* head, int x, int y) {
	if(head == NULL || head->next == NULL)
		return 0;
	Node* pre = NULL;
	Node* p = head;
    while(p->next != NULL) {
    	pre = p;
		p = p->next;
        if(p->data.x == x && p->data.y == y) {
        	pre->next = p->next;
        	free(p);
        	return 1;	
		}
    }
    return 0;
}

int updateCityByName(Node* head, char* oldName, char* newName, int newX, int newY) {
	Node* node = findCityByName(head, oldName);
	if(node == NULL)
		return 0;
	strcpy(node->data.name, newName);
	node->data.x = newX;
	node->data.y = newY;
	return 1;
}

int updateCityByCoords(Node* head, int oldX, int oldY, char* newName, int newX, int newY) {
	Node* node = findCityByCoords(head, oldX, oldY);
	if(node == NULL)
		return 0;
	strcpy(node->data.name, newName);
	node->data.x = newX;
	node->data.y = newY;
	return 1;
}
