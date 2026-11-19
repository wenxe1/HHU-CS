"""
种子数据：内置「数据结构与算法」课程知识点和题库。

使用方法：
  cd backend && python -m app.seed
"""
import asyncio
from beanie import init_beanie

from app.config import MONGODB_URL
from app.models.course import Course
from app.models.knowledge_point import KnowledgePoint, DifficultyLevel
from app.models.knowledge_graph import KnowledgeGraphState
from app.models.question import Question, QuestionType
from app.models.user import User, UserRole


async def seed():
    await init_beanie(
        connection_string=MONGODB_URL,
        document_models=[User, Course, KnowledgePoint, KnowledgeGraphState, Question],
    )

    # 创建默认用户
    existing_user = await User.find_one({"email": "demo@eduagent.local"})
    if not existing_user:
        user = User(
            name="演示学生",
            email="demo@eduagent.local",
            role=UserRole.STUDENT,
        )
        await user.insert()
        print(f"创建用户: {user.id}")
    else:
        user = existing_user
        print(f"用户已存在: {user.id}")

    # 创建课程
    existing_course = await Course.find_one({"name": "数据结构与算法"})
    if not existing_course:
        course = Course(
            name="数据结构与算法",
            description="面向计算机专业本科生的数据结构与算法课程",
        )
        await course.insert()
        print(f"创建课程: {course.id}")
    else:
        course = existing_course
        print(f"课程已存在: {course.id}")

    # 知识点定义：(章节, 名称, 难度, 前置知识点索引列表)
    kp_definitions = [
        ("第一章 绪论", "数据结构与算法概述", DifficultyLevel.BASIC, []),
        ("第一章 绪论", "时间复杂度分析", DifficultyLevel.BASIC, [0]),
        ("第二章 线性表", "数组", DifficultyLevel.BASIC, [0]),
        ("第二章 线性表", "链表（单链表/双链表）", DifficultyLevel.BASIC, [2]),
        ("第三章 栈与队列", "栈的概念与实现", DifficultyLevel.BASIC, [3]),
        ("第三章 栈与队列", "队列的概念与实现", DifficultyLevel.BASIC, [3]),
        ("第四章 树", "树的基本概念与遍历", DifficultyLevel.MEDIUM, [4]),
        ("第四章 树", "二叉搜索树", DifficultyLevel.MEDIUM, [6]),
        ("第四章 树", "平衡二叉树（AVL）", DifficultyLevel.HARD, [7]),
        ("第四章 树", "堆与优先队列", DifficultyLevel.MEDIUM, [6]),
        ("第五章 图", "图的基本概念与存储", DifficultyLevel.MEDIUM, [5, 6]),
        ("第五章 图", "深度优先搜索（DFS）", DifficultyLevel.MEDIUM, [10]),
        ("第五章 图", "广度优先搜索（BFS）", DifficultyLevel.MEDIUM, [10]),
        ("第五章 图", "最短路径算法", DifficultyLevel.HARD, [11, 12]),
        ("第六章 查找与排序", "二分查找", DifficultyLevel.BASIC, [2]),
        ("第六章 查找与排序", "快速排序", DifficultyLevel.MEDIUM, [2, 3]),
        ("第六章 查找与排序", "归并排序", DifficultyLevel.MEDIUM, [2, 3]),
        ("第七章 动态规划", "动态规划基本思想", DifficultyLevel.HARD, [4, 5, 6]),
        ("第七章 动态规划", "经典 DP 问题（背包/LIS）", DifficultyLevel.HARD, [17]),
        ("第八章 综合应用", "数据结构与算法综合运用", DifficultyLevel.COMPREHENSIVE, [8, 9, 13, 14, 18]),
    ]

    existing_kps = await KnowledgePoint.find(
        KnowledgePoint.course_id == course.id
    ).to_list()
    if existing_kps:
        print(f"知识点已存在 {len(existing_kps)} 条，跳过创建")
        knowledge_points = existing_kps
    else:
        knowledge_points = []
        for chapter, name, difficulty, prereq_indices in kp_definitions:
            prerequisites = [knowledge_points[i].id for i in prereq_indices] if prereq_indices else []
            kp = KnowledgePoint(
                course_id=course.id,
                chapter=chapter,
                name=name,
                description=f"《数据结构与算法》—— {name}",
                difficulty=difficulty,
                prerequisites=prerequisites,
                order=len(knowledge_points) + 1,
            )
            await kp.insert()
            knowledge_points.append(kp)
        print(f"创建 {len(knowledge_points)} 条知识点")

    # 题库定义
    questions_data = [
        {
            "kp_index": 2,
            "type": QuestionType.CHOICE,
            "content": "数组的随机访问时间复杂度是多少？",
            "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
            "answer": "O(1)",
            "explanation": "数组通过下标直接访问元素，时间复杂度为 O(1)。",
            "difficulty": "basic",
        },
        {
            "kp_index": 3,
            "type": QuestionType.CHOICE,
            "content": "单链表中删除一个已知节点的后继节点，时间复杂度是多少？",
            "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
            "answer": "O(1)",
            "explanation": "已知当前节点，直接修改指针指向后继的后继即可，O(1)。",
            "difficulty": "basic",
        },
        {
            "kp_index": 4,
            "type": QuestionType.CHOICE,
            "content": "栈的典型操作特性是什么？",
            "options": ["FIFO（先进先出）", "LIFO（后进先出）", "随机访问", "按优先级出队"],
            "answer": "LIFO（后进先出）",
            "explanation": "栈是后进先出（LIFO）的数据结构，典型应用包括函数调用栈。",
            "difficulty": "basic",
        },
        {
            "kp_index": 5,
            "type": QuestionType.CHOICE,
            "content": "队列的典型操作特性是什么？",
            "options": ["LIFO（后进先出）", "FIFO（先进先出）", "随机访问", "按优先级出队"],
            "answer": "FIFO（先进先出）",
            "explanation": "队列是先进先出（FIFO），典型应用包括 BFS、任务调度。",
            "difficulty": "basic",
        },
        {
            "kp_index": 7,
            "type": QuestionType.CHOICE,
            "content": "在二叉搜索树中查找一个元素的最坏时间复杂度是多少？",
            "options": ["O(1)", "O(log n)", "O(n)", "O(n²)"],
            "answer": "O(n)",
            "explanation": "二叉搜索树退化为链表时，查找最坏为 O(n)。平衡 BST 则为 O(log n)。",
            "difficulty": "medium",
        },
        {
            "kp_index": 1,
            "type": QuestionType.CHOICE,
            "content": "一个程序中有循环嵌套：for i in range(n): for j in range(n): ... 时间复杂度是多少？",
            "options": ["O(n)", "O(n log n)", "O(n²)", "O(2ⁿ)"],
            "answer": "O(n²)",
            "explanation": "两层嵌套循环每层执行 n 次，时间复杂度为 O(n²)。",
            "difficulty": "basic",
        },
        {
            "kp_index": 11,
            "type": QuestionType.FILL,
            "content": "DFS 通常使用____（数据结构）来实现。",
            "answer": "栈",
            "explanation": "DFS 可以使用递归（系统栈）或显式栈来实现深度优先遍历。",
            "difficulty": "medium",
        },
        {
            "kp_index": 12,
            "type": QuestionType.FILL,
            "content": "BFS 通常使用____（数据结构）来实现。",
            "answer": "队列",
            "explanation": "BFS 使用队列来保证按照层次顺序逐层遍历。",
            "difficulty": "medium",
        },
        {
            "kp_index": 15,
            "type": QuestionType.FILL,
            "content": "二分查找要求数据是____的。",
            "answer": "有序",
            "explanation": "二分查找的前提是数据有序排列，每次折半缩小搜索范围。",
            "difficulty": "basic",
        },
        {
            "kp_index": 16,
            "type": QuestionType.CHOICE,
            "content": "快速排序的平均时间复杂度是多少？",
            "options": ["O(n)", "O(n log n)", "O(n²)", "O(log n)"],
            "answer": "O(n log n)",
            "explanation": "快速排序平均时间复杂度为 O(n log n)，最坏情况（已排序）为 O(n²)。",
            "difficulty": "medium",
        },
        {
            "kp_index": 17,
            "type": QuestionType.CHOICE,
            "content": "动态规划的两个核心要素是什么？",
            "options": [
                "递归和分治",
                "最优子结构和重叠子问题",
                "贪心选择和排序",
                "回溯和剪枝",
            ],
            "answer": "最优子结构和重叠子问题",
            "explanation": "动态规划适用于具有最优子结构和重叠子问题的问题，通过存储子问题结果避免重复计算。",
            "difficulty": "medium",
        },
        {
            "kp_index": 18,
            "type": QuestionType.CODE,
            "content": "编写一个函数 fibonacci(n)，使用动态规划计算第 n 个斐波那契数（n >= 0，F(0)=0, F(1)=1）。",
            "answer": "def fibonacci(n):\n    if n <= 1:\n        return n\n    dp = [0] * (n + 1)\n    dp[0] = 0\n    dp[1] = 1\n    for i in range(2, n + 1):\n        dp[i] = dp[i-1] + dp[i-2]\n    return dp[n]",
            "explanation": "自底向上的动态规划，时间复杂度 O(n)，空间复杂度 O(n)，可进一步优化为 O(1)。",
            "difficulty": "hard",
        },
    ]

    existing_questions = await Question.find_all().to_list()
    if existing_questions:
        print(f"题目已存在 {len(existing_questions)} 道，跳过创建")
    else:
        for q in questions_data:
            question = Question(
                knowledge_point_id=knowledge_points[q["kp_index"]].id,
                question_type=q["type"],
                content=q["content"],
                options=q.get("options"),
                answer=q["answer"],
                explanation=q.get("explanation"),
                difficulty=q["difficulty"],
            )
            await question.insert()
        print(f"创建 {len(questions_data)} 道题目")

    print("\n种子数据创建完成！")
    print(f"  课程 ID: {course.id}")
    print(f"  用户 ID: {user.id}")
    print(f"  知识点数: {len(knowledge_points)}")


if __name__ == "__main__":
    asyncio.run(seed())
