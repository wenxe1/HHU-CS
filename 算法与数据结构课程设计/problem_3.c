#include <stdio.h>
#include <stdlib.h>

typedef struct Tree {
	int data;
	struct Tree* leftLink;
	struct Tree* rightLink;	
} Tree; 

Tree* newNode(int data) {
    Tree* node = (Tree*)malloc(sizeof(Tree));
    node->data = data;
    node->leftLink = NULL;
    node->rightLink = NULL;
    return node;
}

int isCompleteTree(Tree* tree, int num) {
	if(tree == NULL)
		return 1;
	Tree* queue[2 * num];  // 扩大容量，避免边界问题 
	int head = 0;
	int tail = -1;
	queue[++tail] = tree;
	int found = 0;  // 记录是否遇到左右孩子有空缺 
	while(head <= tail) {
		Tree* cur = queue[head++];
		if(cur->leftLink) {
			if(found)
				return 0;
			queue[++tail] = cur->leftLink;
		} else {
			found = 1;
		}

		if (cur->rightLink) {
			if(found) {
				return 0;
			}
			queue[++tail] = cur->rightLink; 
		} else {
			found = 1;
		}
	}
	return 1; 
}

int main() {
	printf("--- 测试用例 1 ---\n");
    Tree* testTree1 = newNode(1);
    testTree1->leftLink = newNode(2);
    testTree1->rightLink = newNode(3);
    testTree1->leftLink->leftLink = newNode(4);
	if(isCompleteTree(testTree1, 4))
		printf("该树是完全二叉树\n");
	else
		printf("该树不是完全二叉树\n"); 
		
	printf("--- 测试用例 2 ---\n");
    Tree* testTree2 = newNode(1);
    testTree2->leftLink = newNode(2);
    testTree2->rightLink = newNode(3);
    testTree2->rightLink->leftLink = newNode(6);
	if(isCompleteTree(testTree2, 4))
		printf("该树是完全二叉树\n");
	else
		printf("该树不是完全二叉树\n"); 
	
	return 0;
}
