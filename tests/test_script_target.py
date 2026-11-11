"""验证文件脚本目标绑定与原生同步/后台路径，不访问真实桌面。"""
import json
from dataclasses import replace
import pytest
from game_automation.portable.domain import Script, ScreenWindow, Click, Point, Rect
from game_automation.portable.domain.script import ScriptTarget
from game_automation.portable.application.script_run import run_script
from game_automation.portable.application.ports import FocusedApplicationWindow
from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.scripts_manager.catalog import ScriptCatalog


def target():
    """给出通用测试应用的预期逻辑尺寸。"""
    return ScriptTarget('Example','Target window',80,60)


@pytest.mark.parametrize('bad',[{'application':''},{'window_title':' '},{'width':True},{'height':0},{'width':80.0}])
def test_target_rejects_incomplete_or_ambiguous_values(bad):
    """字段必须完整且尺寸是正整数。"""
    with pytest.raises(ValueError):
        replace(target(),**bad)


def test_json_loads_target_and_old_files_keep_screen_coordinates(tmp_path):
    """新文件保存目标声明，旧格式不改变坐标语义。"""
    data={'name':'sample','steps':[{'wait':0}],'target':{'application':'Example','window_title':'Target window','width':80,'height':60}}
    path=tmp_path/'sample.json'
    path.write_text(json.dumps(data))
    assert load_config_scripts(tmp_path,asset_root=tmp_path)[0].target==target()
    del data['target']
    path.write_text(json.dumps(data))
    assert load_config_scripts(tmp_path,asset_root=tmp_path)[0].target is None
    data['target']={'application':'Example'}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_config_scripts(tmp_path,asset_root=tmp_path)


class Environment:
    """记录激活、选窗和输入设备事件。"""
    def __init__(self,size=(80,60)):
        """提供有屏幕偏移的假窗口。"""
        self.events=[]
        self.size=size
    def activate(self,application):
        """记录激活，保持无设备副作用。"""
        self.events.append(('activate',application))
    def focus_window(self,application,title):
        """返回移动后的窗口位置。"""
        self.events.append(('focus',application,title))
        return FocusedApplicationWindow(title,Rect(120,220,*self.size))
    def click(self,point):
        """记录最终屏幕坐标。"""
        self.events.append(('click',point))
    def wait(self,seconds):
        """不进行真实等待。"""


def sample():
    """构造含目标声明的最小脚本。"""
    return Script('sample',ScreenWindow(),(Click(Point(5,6)),),target=target())


def test_declared_window_maps_relative_clicks_after_activation():
    """每次运行根据窗口当前原点换算，而非缓存旧屏幕坐标。"""
    env=Environment()
    result=run_script(sample(),dry_run=False,real_application_activator_factory=lambda:env,
        real_application_window_controller_factory=lambda:env,real_device_factory=lambda:env)
    assert result.finish_reason=='completed'
    assert env.events==[('activate','Example'),('focus','Example','Target window'),('click',Point(125,226))]


def test_wrong_size_never_creates_input_device():
    """不适配的布局在创建设备或点击前失败。"""
    env=Environment((81,60))
    def forbidden():
        """尺寸不符时不允许初始化输入。"""
        raise AssertionError('device initialized')
    result=run_script(sample(),dry_run=False,real_application_activator_factory=lambda:env,
        real_application_window_controller_factory=lambda:env,real_device_factory=forbidden)
    assert result.finish_reason=='configuration_failed' and '尺寸' in result.error_message


def test_dry_run_never_uses_declared_target_desktop():
    """模拟运行保留无桌面副作用。"""
    def forbidden():
        """模拟时不允许调用真实环境工厂。"""
        raise AssertionError('desktop touched')
    result=run_script(sample(),dry_run=True,real_application_activator_factory=forbidden,
        real_application_window_controller_factory=forbidden)
    assert result.finish_reason=='completed'


@pytest.mark.parametrize('background',[False,True])
def test_control_paths_honor_declared_target(tmp_path,background):
    """原生所用后台路径与同步入口都传递现有选窗工厂。"""
    env=Environment()
    app=LocalControlApplication(catalog=ScriptCatalog((sample(),)),project_root=tmp_path,
        real_application_activator_factory=lambda:env,real_application_window_controller_factory=lambda:env,
        real_device_factory=lambda:env)
    if background:
        app.start_named_script('sample',dry_run=False)
        assert app.wait_for_script_stop(2)
        result=app.current_script_run()
    else:
        result=app.run_named_script('sample',dry_run=False)
    assert result.finish_reason=='completed' and env.events[-1]==('click',Point(125,226))
