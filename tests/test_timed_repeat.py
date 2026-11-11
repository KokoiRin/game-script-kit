"""验证按实际经过时间结束的循环、输入边界和模拟时间。

测试只使用公开领域、loader及运行用例；设备和单调时钟均为可控边界，不连接桌面。
"""
import json
from time import monotonic
import pytest
from game_automation.portable.domain import Click, ImageExists, ImageMatch, ImageTarget, ImageTemplate, Point, Rect, Repeat, Script, ScreenWindow, Wait, WaitUntil
from game_automation.portable.engine.runner import ScriptRunner, ScriptCancelledError
from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.application.script_run import run_script


class World:
    """用单调虚拟时钟记录真正执行的输入和识图成本。"""
    def __init__(self, recognition_cost=0):
        """保存当前时间及边界调用记录。"""
        self.now=0.0
        self.clicks=[]
        self.waits=[]
        self.recognition_cost=recognition_cost
        self.cancelled=False
        self.events=[]
    def clock(self):
        """返回假边界共享的单调时间。"""
        return self.now
    def click(self,point):
        """记录输入实际发生的时刻。"""
        self.clicks.append((self.now,point))
    def wait(self,seconds):
        """模拟真实等待并推进同一时钟。"""
        self.waits.append(seconds)
        self.now+=seconds
    def locate(self,template,**kwargs):
        """把识图耗时计入实际经过时间。"""
        self.now+=self.recognition_cost
        return ImageMatch(Rect(10,10,4,4),1)
    def is_cancelled(self):
        """在到期时也允许用户取消优先生效。"""
        return self.cancelled and self.now>=2
    def log(self,message):
        """测试只收集结构化事件。"""
    def log_event(self,event):
        """记录公开循环结束事件。"""
        self.events.append(event)


@pytest.mark.parametrize('seconds',[0,-1,float('inf'),float('nan'),True])
def test_duration_requires_positive_finite_seconds(seconds):
    """时间上限拒绝非有限值、非正值和布尔值。"""
    with pytest.raises(ValueError,match='max_seconds'):
        Repeat(None,(Wait(1),),max_seconds=seconds)


def test_timed_repeat_clips_wait_and_continues_following_steps():
    """到期中断本层长等待，后续步骤仍可正常执行。"""
    world=World()
    script=Script('limit',window=ScreenWindow(),steps=(Repeat(None,(Click(Point(1,1)),Wait(10),Click(Point(2,2))),max_seconds=3),Click(Point(9,9))))
    result=ScriptRunner(world,clock=world.clock,logger=world,emit_step_events=True).run(script)
    assert result.finish_reason=='completed'
    assert world.waits==[3]
    assert world.clicks==[(0,Point(1,1)),(3,Point(9,9))]
    assert any(e.event_type=='repeat_interrupted' and '时间上限' in e.details['reason'] for e in world.events)


def test_recognition_that_finishes_after_deadline_does_not_click():
    """慢识图也计入上限，到期后不再投递点击。"""
    world=World(recognition_cost=3.1)
    script=Script('slow',window=ScreenWindow(),steps=(Repeat(None,(Click(ImageTarget(ImageTemplate('x.png'))),),max_seconds=3),))
    result=ScriptRunner(world,image_locator=world,clock=world.clock).run(script)
    assert result.finish_reason=='completed'
    assert world.clicks==[]


def test_outer_duration_interrupts_nested_unbounded_wait():
    """外层上限穿透嵌套无限等待并保留正确作用域。"""
    world=World()
    class Missing:
        """提供始终不出现的目标。"""
        def locate(self,template,**kwargs):
            """不读取设备且返回未命中。"""
            return None
    script=Script('nested',window=ScreenWindow(),steps=(Repeat(None,(Repeat(None,(WaitUntil(ImageExists(ImageTemplate('x.png')),None,10),Click(Point(1,1))),max_seconds=99),Click(Point(2,2))),max_seconds=2),Click(Point(9,9))))
    result=ScriptRunner(world,image_locator=Missing(),clock=world.clock).run(script)
    assert result.finish_reason=='completed'
    assert world.waits==[2]
    assert world.clicks==[(2,Point(9,9))]


def test_finite_count_can_finish_before_duration():
    """次数和时间并存时先达到次数即结束。"""
    world=World()
    script=Script('finite',window=ScreenWindow(),steps=(Repeat(2,(Wait(.5),Click(Point(1,1))),max_seconds=3),))
    ScriptRunner(world,clock=world.clock).run(script)
    assert world.clicks==[(.5,Point(1,1)),(1,Point(1,1))]


def test_user_cancel_wins_over_deadline():
    """用户停止在时间上限处仍以取消返回。"""
    world=World()
    world.cancelled=True
    script=Script('cancel',window=ScreenWindow(),steps=(Repeat(None,(Wait(10),),max_seconds=2),))
    with pytest.raises(ScriptCancelledError):
        ScriptRunner(world,clock=world.clock,cancellation_token=world).run(script)


def test_loader_details_and_dry_run_support_duration(tmp_path,capsys):
    """正式JSON及模拟入口表达300秒循环，模拟等待不占用实际300秒。"""
    (tmp_path/'timed.json').write_text(json.dumps({'name':'timed','steps':[{'repeat':{'times':None,'max_seconds':300,'steps':[{'wait':1}]}}]}))
    script=load_config_scripts(tmp_path,asset_root=tmp_path)[0]
    assert script.steps[0].max_seconds==300
    from game_automation.portable.application.script_details import describe_script_details
    details=describe_script_details(script,asset_root=tmp_path,supported_image_suffixes=frozenset({'.png'}),state_names=())
    assert any('max_seconds=300' in line for line in details.steps)
    started=monotonic()
    result=run_script(script,dry_run=True)
    assert result.finish_reason=='completed'
    assert monotonic()-started<2
    assert len(capsys.readouterr().out.splitlines())<=301
