"""校验原子组合键的纯值契约。

本模块为直接任务上下文校验输入键名，不发送输入、不读取平台状态。
"""

from string import ascii_lowercase, digits

_SUPPORTED_KEYS = frozenset(ascii_lowercase + digits) | {
    "command",
    "ctrl",
    "alt",
    "shift",
    "enter",
    "tab",
    "esc",
    "space",
}


def validate_hotkey_keys(keys: tuple[str, ...]) -> None:
    """拒绝空组合、重复键名和输入契约之外的键名。"""
    if not isinstance(keys, tuple) or not keys:
        raise ValueError("hotkey keys must be a non-empty tuple")
    for key in keys:
        if not isinstance(key, str) or key not in _SUPPORTED_KEYS:
            raise ValueError(f"unsupported hotkey key: {key!r}")
    if len(set(keys)) != len(keys):
        raise ValueError("hotkey keys must not contain duplicates")
