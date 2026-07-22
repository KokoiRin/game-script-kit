"""用真实 Star 桌面 adapter 操作视觉靶场并独立验收结果。

本工具只负责本机手动 smoke：它通过靶场 API 重置和读取真值，但所有场景动作
必须由 Star 截图、识图和鼠标点击完成。它不参与自动 pytest 套件。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any
from urllib.request import Request, urlopen

from game_automation.platform.local_desktop.composition import run_script_on_local_desktop
from game_automation.portable.domain import (
    Click,
    ImageExists,
    ImageTarget,
    ImageTemplate,
    ScreenWindow,
    Script,
    WaitUntil,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAB_IMAGE_ROOT = PROJECT_ROOT / "src" / "star_visual_lab" / "static" / "images"


def main(argv: list[str] | None = None) -> int:
    """重置靶场、用真实 Star 完成任务并读取真值验收。"""
    parser = argparse.ArgumentParser(description="Run Star against the local visual lab.")
    parser.add_argument("--url", default="http://127.0.0.1:8770", help="Running visual lab URL.")
    parser.add_argument(
        "--target-app",
        default="Safari",
        help="Application Star activates before operating the visual lab.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.9,
        help="Minimum OpenCV template confidence.",
    )
    parser.add_argument(
        "--start-delay",
        type=float,
        default=0,
        help="Seconds to wait after reset so the browser can be brought to the foreground.",
    )
    args = parser.parse_args(argv)
    if args.start_delay < 0:
        parser.error("--start-delay must be greater than or equal to 0")

    _post_json(
        args.url,
        "/api/reset",
        {"mode": "normal", "loading_delay_seconds": 0.6},
    )
    if args.start_delay:
        print(f"Visual lab smoke starts in {args.start_delay:g}s; keep the lab browser visible.")
        time.sleep(args.start_delay)
    result = run_script_on_local_desktop(
        _build_smoke_script(min_confidence=args.min_confidence),
        dry_run=False,
        target_application=args.target_app,
    )
    truth = _get_json(args.url, "/api/state")
    events = _get_json(args.url, "/api/events")["events"]
    print(
        "Visual lab smoke: "
        f"finish_reason={result.finish_reason} truth_state={truth['state']} events={len(events)}"
    )
    if result.finish_reason != "completed" or truth["state"] != "completed":
        return 1
    return 0


def _build_smoke_script(*, min_confidence: float) -> Script:
    """构造依次识别并点击三个目标、等待完成标识的 smoke 脚本。"""
    open_tasks = ImageTemplate(str(LAB_IMAGE_ROOT / "open-tasks.png"))
    target_task = ImageTemplate(str(LAB_IMAGE_ROOT / "target-task.png"))
    confirm_task = ImageTemplate(str(LAB_IMAGE_ROOT / "confirm-task.png"))
    completed = ImageTemplate(str(LAB_IMAGE_ROOT / "completed.png"))
    return Script(
        name="visual-lab-real-smoke",
        window=ScreenWindow(),
        steps=(
            _wait_for(open_tasks, min_confidence=min_confidence),
            Click(ImageTarget(open_tasks, min_confidence=min_confidence)),
            _wait_for(target_task, min_confidence=min_confidence),
            Click(ImageTarget(target_task, min_confidence=min_confidence)),
            _wait_for(confirm_task, min_confidence=min_confidence),
            Click(ImageTarget(confirm_task, min_confidence=min_confidence)),
            _wait_for(completed, min_confidence=min_confidence),
        ),
    )


def _wait_for(template: ImageTemplate, *, min_confidence: float) -> WaitUntil:
    """构造适合本机浏览器状态刷新的图片等待步骤。"""
    return WaitUntil(
        ImageExists(template, min_confidence=min_confidence),
        timeout_seconds=8,
        interval_seconds=0.2,
    )


def _get_json(base_url: str, path: str) -> dict[str, Any]:
    """读取靶场 JSON 真值接口。"""
    with urlopen(f"{base_url.rstrip('/')}{path}", timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("visual lab truth response must be an object")
    return payload


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """向靶场发送 JSON 设置请求并返回响应。"""
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=3) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("visual lab setup response must be an object")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
