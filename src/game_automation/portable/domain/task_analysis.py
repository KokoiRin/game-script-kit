"""从函数任务声明产生静态依赖事实。

本模块为详情、资源检查与端口装配提供同一份依赖声明。
它不分析 Python 控制流、不解析文件，也不访问桌面能力。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain.point_aliases import ImageRef, PointRef, SearchRef
from game_automation.portable.domain.task import FunctionTask

type ImageDependencySource = ImageRef | SearchRef
type TaskDependency = PointRef | ImageDependencySource


@dataclass(frozen=True, slots=True)
class TaskAnalysis:
    """保存声明中的资源引用、状态名称和取色需求。"""

    references: tuple[TaskDependency, ...] = ()
    state_names: tuple[str, ...] = ()
    uses_colors: bool = False

    @property
    def point_names(self) -> tuple[str, ...]:
        """按声明顺序返回命名点位。"""
        return tuple(ref.name for ref in self.references if isinstance(ref, PointRef))

    @property
    def image_sources(self) -> tuple[ImageDependencySource, ...]:
        """按声明顺序返回命名图片和搜索引用。"""
        return tuple(
            ref for ref in self.references if isinstance(ref, ImageRef | SearchRef)
        )


def analyze_task(task: FunctionTask) -> TaskAnalysis:
    """从显式依赖声明生成去重且顺序稳定的事实。"""
    return TaskAnalysis(
        references=tuple(
            dict.fromkeys(
                (
                    *tuple(PointRef(name) for name in task.requires.points),
                    *tuple(ImageRef(name) for name in task.requires.images),
                    *tuple(SearchRef(name) for name in task.requires.searches),
                )
            )
        ),
        state_names=tuple(dict.fromkeys(task.requires.states)),
        uses_colors=task.requires.colors,
    )
