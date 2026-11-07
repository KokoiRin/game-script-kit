"""对冻结图片执行只读、可重复的素材搜索请求负载。

本工具复用窗口 probe 的批量识别，不创建窗口源、不捕获屏幕、不发送输入；
重复已登记候选只测请求规模，不代表同等数量的不同真实模板或实机全流程。
"""

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import sys
from time import perf_counter

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from game_automation.platform.macos.adapters.window_state_probe import MacOSWindowStateProbe
from game_automation.portable.application.window_state_rules import WindowStateRules, load_window_state_rules
from game_automation.portable.domain import Rect
from game_automation.portable.preparation.models import DesktopWindow


class FrozenSource:
    """只提供预先解码的内存画面与规则声明的逻辑尺寸。"""
    def __init__(self, image, rules) -> None:
        """绑定经过像素来源校验的冻结图。"""
        self.image = image
        self.logical_size = (rules.width, rules.height)

    def screenshot(self):
        """返回同一张内存图，不访问桌面或文件。"""
        return self.image

    def size(self):
        """保留真实规则的逻辑到像素比例。"""
        return self.logical_size

    def close(self) -> None:
        """冻结图由基准调用方拥有，无平台资源需要回收。"""


def summarize(values: list[float]) -> dict:
    """输出 nearest-rank 分位数及实际成功样本数。"""
    ordered = sorted(values)
    return {'sample_count': len(values),
            'p50_ms': None if not values else ordered[math.ceil(len(values) * 0.5) - 1],
            'p95_ms': None if not values else ordered[math.ceil(len(values) * 0.95) - 1],
            'max_ms': max(values) if values else None}


def run_benchmark(workspace: Path, frame: Path, *, counts=(2, 10, 50, 100), iterations=20) -> dict:
    """分别用配置ROI和全窗口搜索，计时包含批量probe及图像转换开销。"""
    if type(iterations) is not int or not 1 <= iterations <= 10000:
        raise ValueError('iterations 必须为 1 到 10000')
    if not counts or any(type(n) is not int or not 1 <= n <= 10000 for n in counts):
        raise ValueError('counts 必须为 1 到 10000 的正整数列表')
    rules = load_window_state_rules(workspace)
    if not rules.candidates:
        raise ValueError('没有可重复搜索的状态素材')
    with Image.open(frame) as original:
        image = original.convert('RGB')
    if image.size != (rules.pixel_width, rules.pixel_height):
        raise ValueError('输入帧像素尺寸与已登记素材不同，不能猜测缩放')
    cases = []
    try:
        for count in counts:
            for mode in ('configured_roi', 'full_window'):
                candidates = tuple(rules.candidates[i % len(rules.candidates)] for i in range(count))
                if mode == 'full_window':
                    candidates = tuple(replace(c, search=replace(c.search, region=None)) for c in candidates)
                repeated = WindowStateRules(candidates, rules.width, rules.height, rules.pixel_width, rules.pixel_height)
                probe = MacOSWindowStateProbe(DesktopWindow('offline', 'offline', 'offline',
                    Rect(0, 0, rules.width, rules.height)), repeated, source=FrozenSource(image, rules))
                warm, first_ms, failures, completed_requests, last_found, errors = [], None, 0, 0, None, []
                try:
                    for index in range(iterations + 1):
                        started = perf_counter()
                        try:
                            result = probe.read()
                            elapsed = (perf_counter() - started) * 1000
                            if len(result.candidates) != count:
                                raise RuntimeError('批量结果数量与请求数量不同')
                            completed_requests += len(result.candidates)
                            last_found = sum(candidate.found for candidate in result.candidates)
                            if index == 0:
                                first_ms = elapsed
                            else:
                                warm.append(elapsed)
                        except Exception as exc:
                            failures += 1
                            if len(errors) < 5:
                                errors.append(str(exc)[:1024])
                finally:
                    probe.close()
                cases.append({'request_count': count, 'mode': mode,
                    'limited_roi_requests': sum(c.search.region is not None for c in candidates),
                    'first_ms': first_ms, 'warm': summarize(warm), 'failures': failures,
                    'completed_requests': completed_requests, 'last_found': last_found, 'errors': errors})
    finally:
        image.close()
    return {'synthetic_repeated_requests': True, 'distinct_registered_templates': len({c.template.path for c in rules.candidates}),
            'frame_pixels': [rules.pixel_width, rules.pixel_height], 'logical_size': [rules.width, rules.height],
            'cold_first_ms': cases[0]['first_ms'], 'iterations_per_case': iterations,
            'measurement': '重复已存请求，不代表不同真实模板。计时包含内存图转换、模板读取/缓存及批量probe开销；不含磁盘帧解码、截图、UI、调频等待。',
            'cold_scope': 'cold_first_ms仅本进程第一次probe.read；其余case first_ms可能已共享OpenCV和模板缓存。warm仅统计各case首轮之后的成功轮，失败单独计数。不能外推实机全流程或据此宣称性能优劣。',
            'cases': cases}


def main(argv=None) -> int:
    """读取冻结图和规则，输出JSON，不写工作区或采集新画面。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--frame', type=Path, required=True)
    parser.add_argument('--counts', default='2,10,50,100')
    parser.add_argument('--iterations', type=int, default=20)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(args.workspace, args.frame, counts=tuple(int(n) for n in args.counts.split(',')), iterations=args.iterations)
        if args.output:
            target = args.output.expanduser().resolve()
            if target in (args.frame.resolve(),) or target.is_relative_to((args.workspace / 'assets').resolve()):
                raise ValueError('输出不能位于素材目录内，且不能覆盖输入帧')
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if any(case['failures'] for case in report['cases']) else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
