import asyncio
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PAPERBANANA_ROOT = Path(__file__).resolve().parents[1] / "integrations" / "PaperBanana"
sys.path.insert(0, str(PAPERBANANA_ROOT))
try:
    from utils.paperviz_processor import PaperVizProcessor  # noqa: E402
    from agents.visualizer_agent import VisualizerAgent  # noqa: E402
finally:
    sys.path.remove(str(PAPERBANANA_ROOT))


class _CriticReturnsNan:
    async def process(self, data, source="stylist"):
        data["target_diagram_critic_suggestions0"] = math.nan
        return data


class _VisualizerSucceeds:
    async def process(self, data):
        data["target_diagram_critic_desc0_base64_jpg"] = "fake-image"
        return data


class PaperBananaUpstreamSyncTest(unittest.TestCase):
    def test_critic_nan_suggestions_do_not_abort_iteration(self):
        processor = PaperVizProcessor(
            exp_config=SimpleNamespace(),
            vanilla_agent=None,
            planner_agent=None,
            visualizer_agent=_VisualizerSucceeds(),
            stylist_agent=None,
            critic_agent=_CriticReturnsNan(),
            retriever_agent=None,
            polish_agent=None,
        )

        result = asyncio.run(
            processor._run_critic_iterations(
                {},
                task_name="diagram",
                max_rounds=1,
                source="stylist",
            )
        )

        self.assertEqual(result["eval_image_field"], "target_diagram_critic_desc0_base64_jpg")

    def test_visualizer_raises_when_image_generation_returns_error_sentinel(self):
        agent = VisualizerAgent(
            exp_config=SimpleNamespace(
                task_name="diagram",
                image_gen_model_name="nano-banana-pro",
                temperature=0.7,
            )
        )

        with patch("utils.generation_utils.should_use_grsai_image_generation", return_value=True):
            with patch(
                "utils.generation_utils.call_grsai_image_generation_with_retry_async",
                return_value=["Error"],
            ):
                with self.assertRaisesRegex(RuntimeError, "nano-banana-pro"):
                    asyncio.run(
                        agent.process(
                            {
                                "target_diagram_stylist_desc0": "Draw a scientific flowchart.",
                                "additional_info": {"rounded_ratio": "16:9"},
                            }
                        )
                    )


if __name__ == "__main__":
    unittest.main()
