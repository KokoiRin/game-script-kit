"""验证离线素材规模基准的输入、工作量与只读边界。

本 module 使用临时规则和小型内存图，不访问屏幕或真实游戏资料。
"""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def benchmark():
    """独立导入工具，不执行命令行。"""
    path = Path(__file__).resolve().parents[1] / "tools/benchmark_observation.py"
    spec = importlib.util.spec_from_file_location("benchmark_observation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_benchmark_uses_all_requests_without_mutating_rules(
    benchmark, tmp_path, monkeypatch
):
    """相同帧重复请求全部执行，两种ROI模式均不采集屏幕或写规则。"""
    import numpy as np
    from PIL import Image

    import game_automation.platform.macos.adapters.window_state_probe as probe

    def forbidden(*args, **kwargs):
        """任何真实窗口源创建都会使测试失败。"""
        pytest.fail("real window source must not be constructed")

    monkeypatch.setattr(probe, "WindowFrameSource", forbidden)
    assets = tmp_path / "assets"
    assets.mkdir()
    image = Image.fromarray(
        np.random.default_rng(42).integers(0, 255, (60, 80, 3), dtype=np.uint8)
    )
    image.save(tmp_path / "frame.png")
    image.crop((10, 10, 20, 20)).save(assets / "target.png")
    path = assets / "window-states.json"
    config = {
        "window_size": {"width": 40, "height": 30},
        "pixel_size": {"width": 80, "height": 60},
        "groups": [
            {
                "state": "A",
                "searches": [
                    {
                        "name": "target",
                        "image": "target.png",
                        "region": {"left": 0, "top": 0, "width": 20, "height": 20},
                    }
                ],
            }
        ],
    }
    path.write_text(json.dumps(config))
    original = path.read_bytes()
    report = benchmark.run_benchmark(
        tmp_path, tmp_path / "frame.png", counts=(2, 4), iterations=2
    )
    assert path.read_bytes() == original
    assert len(report["cases"]) == 4
    for case in report["cases"]:
        assert case["warm"]["sample_count"] == 2
        assert case["completed_requests"] == case["request_count"] * 3
        assert case["failures"] == 0
        assert case["last_found"] == case["request_count"]
    output = tmp_path.parent / (tmp_path.name + "-result.json")
    assert (
        benchmark.main(
            [
                "--workspace",
                str(tmp_path),
                "--frame",
                str(tmp_path / "frame.png"),
                "--counts",
                "2",
                "--iterations",
                "1",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text())["synthetic_repeated_requests"] is True
    Image.new("RGB", (81, 60)).save(tmp_path / "wrong.png")
    with pytest.raises(ValueError, match="尺寸"):
        benchmark.run_benchmark(
            tmp_path, tmp_path / "wrong.png", counts=(2,), iterations=1
        )


@pytest.mark.parametrize(
    "counts,iterations", [((0,), 1), ((2,), 0), ((True,), 2), ((), 2)]
)
def test_invalid_load_is_rejected_before_reading_workspace(
    benchmark, tmp_path, counts, iterations
):
    """非法负载在读取素材或图像之前报错。"""
    with pytest.raises(ValueError):
        benchmark.run_benchmark(
            tmp_path, tmp_path / "absent.png", counts=counts, iterations=iterations
        )
