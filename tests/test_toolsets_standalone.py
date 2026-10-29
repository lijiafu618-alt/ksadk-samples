"""单独打包的 Toolsets 示例必须脱离仓库目录结构加载。"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SAMPLE = (
    Path(__file__).resolve().parents[1]
    / "02-use-cases/agentengine-toolsets/langgraph"
)


@pytest.mark.parametrize("legacy_names", [False, True])
def test_toolsets_imports_outside_repository(tmp_path, legacy_names):
    project = tmp_path / "code"
    project.mkdir()
    shutil.copy2(SAMPLE / "agent.py", project / "agent.py")
    env = os.environ.copy()
    for name in ("OPENAI_MODEL_NAME", "MODEL_NAME", "OPENAI_BASE_URL", "OPENAI_API_BASE"):
        env.pop(name, None)
    env.update({
        "OPENAI_API_KEY": "test-key",
        "MODEL_NAME" if legacy_names else "OPENAI_MODEL_NAME": "test-model",
        "OPENAI_API_BASE" if legacy_names else "OPENAI_BASE_URL": "https://example.com/v1",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import importlib.abc
import runpy
import sys

class NoRepositoryCommon(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "common" or fullname.startswith("common."):
            raise AssertionError("Standalone sample imports repository common")

sys.meta_path.insert(0, NoRepositoryCommon())
agent = runpy.run_path(sys.argv[1])
assert agent["root_agent"].get_graph()
model = agent["make_langchain_chat_model"]()
assert model.model_name == "test-model"
assert str(model.openai_api_base).rstrip("/") == "https://example.com/v1"
assert model.temperature == 0
""",
            str(project / "agent.py"),
        ],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
