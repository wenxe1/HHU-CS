from collections.abc import AsyncIterator, Sequence
from typing import Any


class FakeAIClient:
    async def stream_text(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        use_reasoning: bool = False,
    ) -> AsyncIterator[str]:
        for chunk in ("AI tutor ", "answer."):
            yield chunk

    async def generate_json(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        use_reasoning: bool = False,
    ) -> dict[str, Any]:
        if agent_name == "Document Agent":
            return {
                "title": "AI 课程讲义",
                "overview": "AI generated lecture overview.",
                "learning_objectives": ["objective"],
                "sections": [{"heading": "concept", "points": ["point"]}],
                "self_check": ["check"],
            }
        if agent_name == "Exercise Agent":
            return {
                "title": "AI 练习题",
                "question_bank": [
                    {
                        "question_id": "q1",
                        "type": "single_choice",
                        "difficulty": "easy",
                        "stem": "stem",
                        "options": ["A", "B"],
                        "answer": "A",
                        "explanation": "explanation",
                    }
                ],
                "grading_rubric": ["rubric"],
            }
        if agent_name == "Mindmap Agent":
            return {
                "title": "AI 思维导图",
                "root": {"id": "root", "label": "topic", "children": []},
                "review_path": ["root"],
            }
        if agent_name == "Slide Agent":
            return {
                "title": "AI PPT 大纲",
                "slides": [
                    {
                        "slide_no": 1,
                        "title": "slide",
                        "bullets": ["bullet"],
                        "speaker_notes": "notes",
                    }
                ],
                "estimated_minutes": 10,
            }
        if agent_name == "Code Lab Agent":
            return {
                "title": "AI 代码实操",
                "scenario": "scenario",
                "environment": {"language": "Python", "entry_file": "main.py"},
                "tasks": ["task"],
                "starter_code": "def solve():\n    pass",
                "reference_solution": "def solve():\n    return None",
                "test_cases": [{"name": "case", "input": "in", "expected": "out"}],
            }
        if agent_name == "Tutor Agent":
            return {
                "answer": "AI tutor answer.",
                "guidance_steps": ["step1", "step2", "step3"],
                "follow_up_questions": ["question"],
                "personalization": {
                    "agent": "Tutor Agent",
                    "reasoning_basis": ["profile", "rag"],
                    "evidence_gap": None,
                },
            }
        if agent_name == "Code Review Agent":
            return {
                "summary": "AI code review summary.",
                "issues": [
                    {
                        "category": "syntax_error",
                        "severity": "error",
                        "title": "syntax",
                        "detail": "missing colon",
                        "suggestion": "fix syntax",
                        "line": 1,
                    }
                ],
                "suggestions": ["fix syntax"],
                "next_steps": ["rerun tests"],
            }
        if agent_name == "Safety Agent":
            return {
                "status": "approved",
                "risk_level": "low",
                "issues": [],
                "citations": [
                    {
                        "source_type": "rag_document",
                        "source_id": "doc",
                        "title": "course material",
                    }
                ],
                "hallucination_checks": ["checked against retrieved context"],
            }
        if agent_name == "Classroom Agent":
            return {
                "title": "BFS 广度优先搜索 互动课堂",
                "description": "AI generated classroom.",
                "learning_goals": ["goal"],
                "agents": [
                    {
                        "id": "agent_teacher",
                        "name": "AI 教师",
                        "role": "teacher",
                        "persona": "clear",
                        "capabilities": ["teach"],
                    }
                ],
                "scenes": [
                    self._scene("teacher_explain", 1, "AI 教师"),
                    self._scene("classmate_question", 2, "AI 同学"),
                    self._scene("whiteboard", 3, "AI 教师"),
                    self._scene("quiz", 4, "测验出题者"),
                    self._scene("code_interactive", 5, "项目导师"),
                    self._scene("pbl", 6, "项目导师"),
                    self._scene("homework", 7, "AI 教师"),
                    self._scene("summary", 8, "AI 教师"),
                ],
            }
        if agent_name == "Quiz Agent":
            return {
                "title": "BFS chapter quiz",
                "questions": [
                    {
                        "question_id": "q1",
                        "type": "single_choice",
                        "stem": "Why is BFS suitable for unweighted shortest paths?",
                        "options": [
                            "It expands by layers",
                            "It uses recursion",
                            "It ignores visited nodes",
                            "It only works on trees",
                        ],
                        "answer": "It expands by layers",
                        "explanation": "BFS reaches nodes in increasing edge distance.",
                        "option_explanations": {
                            "It expands by layers": "This matches BFS visiting nodes by distance layers.",
                            "It uses recursion": "Recursion is not the defining reason BFS solves this problem.",
                            "It ignores visited nodes": "BFS must track visited nodes to avoid repeated work.",
                            "It only works on trees": "BFS also works on general graphs.",
                        },
                    }
                ],
            }
        if agent_name == "Flashcard Agent":
            return {
                "title": "Graph search flashcards",
                "cards": [
                    {
                        "card_id": "card1",
                        "front": "What data structure does BFS use?",
                        "back": "A queue.",
                    }
                ],
            }
        if agent_name == "User Profile Agent":
            return {
                "summary": "近期学习记录显示你能主动提问，并开始通过练习检验理解。",
                "radar": [
                    {
                        "key": "conceptual_understanding",
                        "label": "概念理解",
                        "score": 72,
                        "reason": "对话和测验记录显示基础概念已有一定掌握。",
                    },
                    {
                        "key": "application_transfer",
                        "label": "应用迁移",
                        "score": 66,
                        "reason": "测验作答能反映初步迁移能力。",
                    },
                    {
                        "key": "metacognition",
                        "label": "元认知提问",
                        "score": 70,
                        "reason": "有主动向 AI 澄清问题的行为。",
                    },
                    {
                        "key": "study_consistency",
                        "label": "学习节奏",
                        "score": 64,
                        "reason": "已有多类学习行为，但仍需要稳定复盘。",
                    },
                    {
                        "key": "memory_recall",
                        "label": "记忆巩固",
                        "score": 68,
                        "reason": "闪卡记录能支持记忆巩固判断。",
                    },
                    {
                        "key": "engagement",
                        "label": "投入度",
                        "score": 74,
                        "reason": "对话和练习行为均有发生。",
                    },
                ],
                "learning_traits": ["主动提问", "愿意练习", "适合短周期复盘"],
                "strengths": ["能够结合 AI 解释推进理解。"],
                "risks": ["练习样本仍偏少，画像需要继续更新。"],
                "recommendations": [
                    {
                        "title": "复盘最近错题",
                        "detail": "把答错的题交给 AI 解释，再做一次同类题。",
                        "priority": "high",
                    }
                ],
                "learning_resources": [
                    {
                        "title": "中国大学MOOC",
                        "url": "https://www.icourse163.org/",
                        "language": "zh",
                        "reason": "优先查找当前知识点的中文公开课。",
                    },
                    {
                        "title": "OI Wiki",
                        "url": "https://oi-wiki.org/",
                        "language": "zh",
                        "reason": "适合复习算法与数据结构概念。",
                    },
                ],
            }
        return {}

    async def embed_texts(
        self,
        texts: Sequence[str],
        embedding_domain: str = "para",
    ) -> list[list[float]]:
        return [self._embedding(text) for text in texts]

    def _embedding(self, text: str) -> list[float]:
        checksum = sum(ord(char) for char in text) % 997
        return [float(len(text) % 97), float(checksum), 1.0]

    def _scene(self, scene_type: str, order: int, speaker: str) -> dict[str, Any]:
        return {
            "scene_type": scene_type,
            "title": scene_type,
            "speaker": speaker,
            "content": {"text": scene_type},
            "actions": [],
            "order": order,
        }
