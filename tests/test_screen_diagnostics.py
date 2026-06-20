"""验证屏幕诊断应用用例和诊断产物接口。

这些测试覆盖 ScreenDiagnosticsUseCase 这个 application seam；它不经过 HTTP/CLI，
也不依赖 LocalControlApplication 的 facade 实现细节。
"""

from PIL import Image

from game_automation.portable.application.screen_diagnostics import ScreenDiagnosticsUseCase
from game_automation.portable.domain import ImageBatchMatchResult, ImageMatch, Point, Rect


def test_screen_diagnostics_captures_screen_debug_screenshot(tmp_path) -> None:
    """验证屏幕诊断用例可把真实截图保存到项目内诊断文件。"""
    captured_paths = []

    def screen_capture(path):
        """保存一张非黑测试截图。"""
        captured_paths.append(path)
        Image.new("RGB", (20, 10), "white").save(path)

    use_case = ScreenDiagnosticsUseCase(
        project_root=tmp_path,
        screen_capture_factory=lambda: screen_capture,
    )

    result = use_case.capture_screen_screenshot()

    screenshot_path = tmp_path / ".star" / "debug" / "screenshots" / "latest-screen.png"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == f"saved screenshot: {screenshot_path}\n"
    assert result.screenshot_path == str(screenshot_path)
    with Image.open(screenshot_path) as screenshot:
        assert screenshot.size == (20, 10)
    assert captured_paths == [screenshot_path]


def test_screen_diagnostics_warns_when_screen_debug_screenshot_is_black(tmp_path) -> None:
    """验证普通截图疑似全黑时返回用户可见警告。"""

    def screen_capture(path):
        """保存一张纯黑测试截图。"""
        Image.new("RGB", (20, 10), "black").save(path)

    use_case = ScreenDiagnosticsUseCase(
        project_root=tmp_path,
        screen_capture_factory=lambda: screen_capture,
    )

    result = use_case.capture_screen_screenshot()

    assert result.exit_code == 0
    assert "captured screenshot appears all black" in result.stderr


def test_screen_diagnostics_diagnoses_setup_with_probe_summary(tmp_path) -> None:
    """验证屏幕诊断用例会先截图再执行一轮状态探测。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        """
        {
          "groups": [
            {
              "state": "主页",
              "searches": [
                {"name": "主页标题", "image": "home.png"}
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    Image.new("RGB", (4, 4), "black").save(assets / "home.png")
    captured_paths = []
    batch_requests = []

    def screen_capture(path):
        """保存一张非黑测试截图。"""
        captured_paths.append(path)
        Image.new("RGB", (20, 10), "white").save(path)

    class FakeBatchLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """记录探测请求并返回主页命中。"""
            batch_requests.append((tuple(requests), stop_on_first_match))
            return (
                ImageBatchMatchResult(
                    requests[0].template,
                    ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                    elapsed_ms=4.0,
                ),
            )

    use_case = ScreenDiagnosticsUseCase(
        project_root=tmp_path,
        screen_capture_factory=lambda: screen_capture,
        real_image_batch_locator_factory=FakeBatchLocator,
    )

    result = use_case.diagnose_screen_setup(min_confidence=0.75)

    screenshot_path = tmp_path / ".star" / "debug" / "screenshots" / "latest-screen.png"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.screenshot_path == str(screenshot_path)
    assert captured_paths == [screenshot_path]
    assert batch_requests[0][0][0].min_confidence == 0.75
    assert batch_requests[0][1] is True
    lines = result.stdout.splitlines()
    assert lines[0:2] == [
        f"saved screenshot: {screenshot_path}",
        "current_state=主页",
    ]
    assert lines[3] == (
        "candidate=主页/主页标题 status=matched elapsed_ms=4.00 "
        "confidence=0.910 best_confidence=0.910 best_rect=x=10,y=20,w=30,h=40"
    )


def test_screen_diagnostics_captures_region_diagnostics(tmp_path) -> None:
    """验证屏幕诊断用例可生成带状态区域框的诊断截图。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        """
        {
          "regions": {
            "主页标题": {"left": 10, "top": 5, "width": 20, "height": 10}
          },
          "groups": [
            {
              "state": "主页",
              "searches": [
                {"name": "主页标题", "image": "home.png", "region": "主页标题"}
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    Image.new("RGB", (4, 4), "black").save(assets / "home.png")

    def screen_capture(path):
        """保存测试用截图。"""
        Image.new("RGB", (200, 100), "white").save(path)

    use_case = ScreenDiagnosticsUseCase(
        project_root=tmp_path,
        screen_capture_factory=lambda: screen_capture,
        screen_size_factory=lambda: Point(100, 50),
    )

    result = use_case.capture_screen_region_diagnostics()

    diagnostic_path = tmp_path / ".star" / "debug" / "screenshots" / "latest-screen-regions.png"
    assert result.exit_code == 0
    assert result.stdout == f"saved region diagnostics screenshot: {diagnostic_path}\n"
    assert result.screenshot_path == str(diagnostic_path)
    with Image.open(diagnostic_path) as diagnostic:
        assert diagnostic.size == (200, 100)
        assert diagnostic.getpixel((20, 10)) != (255, 255, 255)


def test_screen_diagnostics_captures_probe_crops(tmp_path) -> None:
    """验证屏幕诊断用例可导出候选最佳匹配位置裁剪图。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        """
        {
          "groups": [
            {
              "state": "主页",
              "searches": [
                {"name": "主页标题", "image": "home.png"}
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    Image.new("RGB", (4, 4), "black").save(assets / "home.png")
    crop_root = tmp_path / ".star" / "debug" / "screenshots" / "probe-crops"
    crop_root.mkdir(parents=True)
    stale_crop = crop_root / "stale.png"
    stale_crop.write_bytes(b"old")
    keep_note = crop_root / "keep.txt"
    keep_note.write_text("manual note", encoding="utf-8")

    class FakeBatchLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """返回未命中候选的最佳位置。"""
            return (
                ImageBatchMatchResult(
                    requests[0].template,
                    None,
                    elapsed_ms=4.0,
                    best_confidence=0.7,
                    best_rect=Rect(10, 5, 20, 10),
                ),
            )

    def screen_capture(path):
        """保存一张 2x 缩放的测试截图。"""
        Image.new("RGB", (200, 100), "white").save(path)

    use_case = ScreenDiagnosticsUseCase(
        project_root=tmp_path,
        screen_capture_factory=lambda: screen_capture,
        screen_size_factory=lambda: Point(100, 50),
        real_image_batch_locator_factory=FakeBatchLocator,
    )

    result = use_case.capture_screen_probe_crops(min_confidence=0.75)

    crop_path = crop_root / "01_主页_主页标题.png"
    assert result.exit_code == 0
    assert result.stdout == f"saved probe crop: {crop_path}\n"
    assert result.screenshot_path == str(crop_root)
    assert not stale_crop.exists()
    assert keep_note.read_text(encoding="utf-8") == "manual note"
    with Image.open(crop_path) as crop:
        assert crop.size == (40, 20)
