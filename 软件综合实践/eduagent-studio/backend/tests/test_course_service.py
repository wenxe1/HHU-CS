import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.course import KnowledgeGraphUpdateRequest
from app.services.course_service import (
    _fallback_incremental_graph,
    _graph_for_storage,
    _normalize_agent_graph,
)


class KnowledgeGraphNormalizationTest(unittest.TestCase):
    def test_new_nodes_are_chinese_and_deduplicated_by_label(self):
        current_graph = {
            "nodes": [
                {
                    "id": "tcp",
                    "label": "TCP",
                    "description": "传输控制协议",
                    "importance": "core",
                    "mastery": "unknown",
                }
            ],
            "edges": [],
        }
        generated = {
            "nodes": [
                {"id": "tcp", "label": "TCP", "importance": "core"},
                {"id": "english", "label": "Reliable transport"},
                {"id": "reliable", "label": "TCP 可靠传输"},
                {"id": "reliable-copy", "label": "TCP可靠传输"},
            ],
            "edges": [
                {"source": "tcp", "target": "reliable", "relation": "advanced"},
                {
                    "source": "tcp",
                    "target": "reliable-copy",
                    "relation": "advanced",
                },
            ],
        }

        graph = _normalize_agent_graph(
            generated,
            "course-network",
            "计算机网络",
            current_graph=current_graph,
        )

        self.assertEqual(
            [node["label"] for node in graph["nodes"]],
            ["TCP", "TCP 可靠传输"],
        )
        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(graph["edges"][0]["target"], "reliable")

    def test_fallback_incremental_nodes_are_chinese_and_not_repeated(self):
        current_graph = {
            "nodes": [
                {
                    "id": "tcp",
                    "label": "TCP",
                    "description": "传输控制协议",
                    "importance": "core",
                    "mastery": "unknown",
                },
                {
                    "id": "reliable-existing",
                    "label": "TCP可靠传输",
                    "description": "已有知识点",
                    "importance": "important",
                    "mastery": "unknown",
                },
            ],
            "edges": [],
        }
        request = KnowledgeGraphUpdateRequest(
            course_name="计算机网络",
            selected_node_id="tcp",
            selected_node_name="TCP",
            current_graph=current_graph,
        )

        graph = _fallback_incremental_graph(
            "course-network",
            "计算机网络",
            current_graph,
            request,
            "测试兜底更新",
        )
        added_nodes = graph["nodes"][len(current_graph["nodes"]):]

        self.assertEqual(
            [node["label"] for node in added_nodes],
            ["拥塞窗口", "TCP 三次握手"],
        )
        self.assertTrue(
            all(any("\u3400" <= char <= "\u9fff" for char in node["label"]) for node in added_nodes)
        )

    def test_graph_storage_keeps_terminal_node_coordinates(self):
        graph = _graph_for_storage(
            "notebook-1",
            "数据结构",
            {
                "nodes": [
                    {
                        "id": "tree",
                        "label": "树与二叉树",
                        "description": "树结构基础",
                        "importance": "core",
                        "mastery": "unknown",
                        "x": 318.5,
                        "y": 226,
                    }
                ],
                "edges": [],
            },
        )

        self.assertEqual(graph["nodes"][0]["x"], 318.5)
        self.assertEqual(graph["nodes"][0]["y"], 226.0)


if __name__ == "__main__":
    unittest.main()
