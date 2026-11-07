"""只读比较窗口采集成本、源时间和既有素材匹配，不替换生产adapter。

本实验只采集指定窗口且关闭音频，不请求权限、不发送输入、不写素材；
主Agent负责真实运行，fake测试负责时间、单槽、身份和清理契约。
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import threading
import time
from PIL import Image


@dataclass(frozen=True)
class Identity:
    """固定窗口编号、进程、标题和原始几何。"""
    window_id: int
    pid: int
    title: str | None
    width: int
    height: int
    pixel_width: int
    pixel_height: int

    def validate(self,item):
        """拒绝替代窗口与尺寸变化，允许窗口位置改变。"""
        if (int(item['kCGWindowNumber']),int(item['kCGWindowOwnerPID']),item.get('kCGWindowName'))!=(self.window_id,self.pid,self.title):
            raise RuntimeError('window identity changed')
        b=item['kCGWindowBounds']
        if (round(b['Width']),round(b['Height']))!=(self.width,self.height):raise RuntimeError('window geometry changed')

@dataclass(frozen=True)
class FrameResult:
    """一次独立RGB输出、源证明和成本，不把缓存读取时间当捕获时间。"""
    image: Image.Image
    sequence: int
    status: str
    pts_host_seconds: float | None
    display_host_seconds: float | None
    timings: dict
    metadata: dict

class LatestSlot:
    """仅保存最新完整帧，失效事件清空，关闭后拒绝迟到发布。"""
    def __init__(self):
        """初始化独占锁、单槽和事件计数。"""
        self.lock=threading.Lock();self.frame=None;self.sequence=0;self.closed=False;self.fault='waiting';self.statuses={}
    def publish(self,status,payload=None):
        """只对新complete递增帧序号，idle不制造新像素。"""
        with self.lock:
            if self.closed:return
            self.statuses[status]=self.statuses.get(status,0)+1
            if status=='complete':
                self.sequence+=1;self.frame=(self.sequence,payload);self.fault=''
            elif status in ('blank','suspended','stopped','error','invalid'):
                self.frame=None;self.fault=status
    def take(self):
        """读取同一不可变槽，重复读取不会递增帧计数。"""
        with self.lock:
            if self.closed:raise RuntimeError('stream closed')
            if self.frame is None:raise RuntimeError('stream '+self.fault)
            return self.frame
    def close(self):
        """幂等关闭并清除所有可交付证据。"""
        with self.lock:self.closed=True;self.frame=None;self.fault='stopped'

def summarize(values):
    """用实际成功样本计算nearest-rank分位数。"""
    a=sorted(values)
    return {'count':len(a),'p50':a[math.ceil(len(a)*.5)-1] if a else None,'p95':a[math.ceil(len(a)*.95)-1] if a else None,'min':min(a) if a else None,'max':max(a) if a else None}

def source_age(host,stamp):
    """源时间缺失、非有限或在未来时只报告诊断，不进入年龄分位。"""
    if stamp is None:return None,'missing'
    if not math.isfinite(stamp) or not math.isfinite(host):return None,'invalid'
    if stamp>host:return None,'future'
    return (host-stamp)*1000,'valid'

def validate_stream_geometry(identity,width,height,scale,factor,rect):
    """只接受原逻辑矩形和原像素比例，未知或非有限元数据失败。"""
    if scale is None or factor is None:raise RuntimeError('missing stream scaling metadata')
    expected=[0,0,identity.width,identity.height]
    if rect is None or len(rect)!=4 or any(not math.isfinite(a) or abs(a-b)>1 for a,b in zip(rect,expected)):
        raise RuntimeError('stream contentRect does not match original logical size: '+repr(rect))
    values=[float(scale),float(factor)]
    if not all(math.isfinite(v) for v in values) or abs(values[0]-1)>0.001 or abs(values[1]-identity.pixel_width/identity.width)>0.001:
        raise RuntimeError('stream content scaling changed')
    if (width,height)!=(identity.pixel_width,identity.pixel_height):raise RuntimeError('pixel geometry changed')

class SourceSetupError(RuntimeError):
    """构造失败时仍携带已创建流的回收结果和事件证据。"""
    def __init__(self,cause,stop_error,source_events,callback_errors,callback_error_count):
        """保存失败上下文，避免丢失构造期停止失败。"""
        super().__init__(str(cause));self.stop_error=stop_error;self.source_events=source_events
        self.callback_errors=callback_errors;self.callback_error_count=callback_error_count

class Native:
    """集中封装实验所需的macOS调用，普通导入不读取桌面。"""
    def __init__(self):
        """只在明确真实实验时加载系统接口。"""
        import Quartz,ScreenCaptureKit,CoreMedia,CoreFoundation,objc
        self.q=Quartz;self.sc=ScreenCaptureKit;self.cm=CoreMedia;self.cf=CoreFoundation;self.objc=objc
    def pump(self,seconds):
        """推进实验控制线程的运行循环，避免饿死异步回调。"""
        end=time.monotonic()+seconds
        while time.monotonic()<end:self.cf.CFRunLoopRunInMode(self.cf.kCFRunLoopDefaultMode,.002,False)
    def wait(self,start,timeout=3):
        """有界等待系统完成，不将超时解释为成功。"""
        done=threading.Event();result=[]
        def callback(*values):
            """保存一次完成值，后续重复完成无效。"""
            if not done.is_set():result.extend(values);done.set()
        start(callback);end=time.monotonic()+timeout
        while not done.is_set() and time.monotonic()<end:self.pump(.003)
        if not done.is_set():raise TimeoutError('native completion timeout')
        if result and result[-1] is not None:raise RuntimeError(str(result[-1]))
        return result[0] if len(result)>1 else None
    def window(self,number):
        """只查指定编号的可见窗口，不按标题重新选择。"""
        q=self.q
        rows=q.CGWindowListCopyWindowInfo(q.kCGWindowListOptionOnScreenOnly|q.kCGWindowListExcludeDesktopElements,0) or ()
        rows=[dict(x) for x in rows if int(x.get(q.kCGWindowNumber,-1))==number and x.get(q.kCGWindowLayer)==0]
        if len(rows)!=1:raise RuntimeError('selected window unavailable')
        return rows[0]
    def configure(self,identity,hz=5):
        """配置仅指定窗口的原分辨率SDR采集，无音频或鼠标。"""
        sc=self.sc;q=self.q
        content=self.wait(lambda cb:sc.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(True,True,cb))
        matches=[w for w in content.windows() if w.windowID()==identity.window_id and w.owningApplication().processID()==identity.pid]
        if len(matches)!=1:raise RuntimeError('SCK target unavailable')
        filt=sc.SCContentFilter.alloc().initWithDesktopIndependentWindow_(matches[0])
        config=sc.SCStreamConfiguration.alloc().init()
        config.setWidth_(identity.pixel_width);config.setHeight_(identity.pixel_height)
        config.setShowsCursor_(False);config.setCapturesAudio_(False);config.setPixelFormat_(q.kCVPixelFormatType_32BGRA)
        config.setIgnoreShadowsSingleWindow_(True);config.setColorSpaceName_(q.kCGColorSpaceSRGB)
        config.setMinimumFrameInterval_(self.cm.CMTimeMake(1,hz));config.setQueueDepth_(3)
        return filt,config
    def rgb(self,image):
        """显式渲染RGBA，处理CGImage排列和颜色空间差异。"""
        q=self.q;w=q.CGImageGetWidth(image);h=q.CGImageGetHeight(image);data=bytearray(w*h*4)
        ctx=q.CGBitmapContextCreate(data,w,h,8,w*4,q.CGColorSpaceCreateWithName(q.kCGColorSpaceSRGB),q.kCGImageAlphaPremultipliedLast|q.kCGBitmapByteOrder32Big)
        if ctx is None:raise RuntimeError('bitmap context unavailable')
        q.CGContextDrawImage(ctx,q.CGRectMake(0,0,w,h),image)
        return Image.frombytes('RGBA',(w,h),bytes(data)).convert('RGB')
    def content_rect(self,value):
        """归一化系统CGRect，未知形式必须报错而非猜测零偏移。"""
        if hasattr(value,'rectValue'):value=value.rectValue()
        if hasattr(value,'origin') and hasattr(value,'size'):
            return [float(value.origin.x),float(value.origin.y),float(value.size.width),float(value.size.height)]
        if isinstance(value,dict) or hasattr(value,'keys'):
            if all(k in value for k in ('X','Y','Width','Height')):return [float(value[k]) for k in ('X','Y','Width','Height')]
            ok,rect=self.q.CGRectMakeWithDictionaryRepresentation(value,None)
            if ok:return self.content_rect(rect)
        raise RuntimeError('unrecognized contentRect '+repr(value))
    def host_now(self):
        """只在CoreMedia host时间域内计算年龄。"""
        return self.cm.CMTimeGetSeconds(self.cm.CMClockGetTime(self.cm.CMClockGetHostTimeClock()))
    def payload(self,sample):
        """复制像素后释放系统缓冲，并保留原始帧元数据。"""
        q=self.q;cm=self.cm;sc=self.sc;t=time.perf_counter()
        image=cm.CMSampleBufferGetImageBuffer(sample)
        if image is None:raise RuntimeError('no image buffer')
        if q.CVPixelBufferLockBaseAddress(image,q.kCVPixelBufferLock_ReadOnly):raise RuntimeError('buffer lock failed')
        try:
            w=q.CVPixelBufferGetWidth(image);h=q.CVPixelBufferGetHeight(image);stride=q.CVPixelBufferGetBytesPerRow(image)
            data=bytes(q.CVPixelBufferGetBaseAddress(image).as_buffer(stride*h))
        finally:q.CVPixelBufferUnlockBaseAddress(image,q.kCVPixelBufferLock_ReadOnly)
        tm=cm.CMSampleBufferGetPresentationTimeStamp(sample)
        pts=cm.CMTimeGetSeconds(tm) if (tm.flags & 1 and tm.timescale>0) else None
        if pts is not None and not math.isfinite(pts):pts=None
        a=cm.CMSampleBufferGetSampleAttachmentsArray(sample,False)
        meta=dict(a[0]) if a else {}
        display=meta.get(sc.SCStreamFrameInfoDisplayTime)
        display_seconds=None
        if display is not None and int(display)>0:
            display_seconds=cm.CMTimeGetSeconds(cm.CMClockMakeHostTimeFromSystemUnits(int(display)))
        keys={'contentRect':sc.SCStreamFrameInfoContentRect,'contentScale':sc.SCStreamFrameInfoContentScale,'scaleFactor':sc.SCStreamFrameInfoScaleFactor}
        metadata={k:repr(meta.get(v)) for k,v in keys.items()}
        if sc.SCStreamFrameInfoContentRect in meta:metadata['content_rect_values']=self.content_rect(meta[sc.SCStreamFrameInfoContentRect])
        metadata['pixel_size']=[w,h];metadata['stride']=stride
        return data,w,h,stride,pts,display_seconds,(time.perf_counter()-t)*1000,metadata,meta

class CaptureSource:
    """封装请求式实验源与统一身份、RGB校验。"""
    def __init__(self,native,identity,method):
        """保存对照方法，启动成本由外层单独记录。"""
        self.n=native;self.identity=identity;self.method=method;self.seq=0;self.closed=False
        self.temp=tempfile.TemporaryDirectory(prefix='star-capture-baseline-');self.path=Path(self.temp.name)/'current.png'
        self.filter=self.config=None
        if method=='sck_shot':self.filter,self.config=native.configure(identity)
    def check(self):
        """每次核对固定窗口身份及原始逻辑尺寸。"""
        if self.closed:raise RuntimeError('source closed')
        self.identity.validate(self.n.window(self.identity.window_id))
    def capture(self):
        """采集本次图像，系统错误不回退到别的方法。"""
        start=time.perf_counter();self.check();pts=display=None;meta={};timings={'geometry_pre_ms':(time.perf_counter()-start)*1000}
        if self.method=='baseline':
            self.path.unlink(missing_ok=True);t=time.perf_counter()
            subprocess.run(['/usr/sbin/screencapture','-x','-o','-l',str(self.identity.window_id),str(self.path)],check=True,capture_output=True,timeout=3)
            timings['command_ms']=(time.perf_counter()-t)*1000;t=time.perf_counter()
            with Image.open(self.path) as raw:image=raw.convert('RGB')
            timings['decode_convert_ms']=(time.perf_counter()-t)*1000
        elif self.method=='quartz':
            q=self.n.q;t=time.perf_counter()
            cg=q.CGWindowListCreateImage(q.CGRectNull,q.kCGWindowListOptionIncludingWindow,self.identity.window_id,q.kCGWindowImageBoundsIgnoreFraming|q.kCGWindowImageBestResolution)
            timings['native_ms']=(time.perf_counter()-t)*1000
            if cg is None:raise RuntimeError('Quartz returned no image')
            t=time.perf_counter();image=self.n.rgb(cg);timings['convert_ms']=(time.perf_counter()-t)*1000
        else:
            t=time.perf_counter()
            sample=self.n.wait(lambda cb:self.n.sc.SCScreenshotManager.captureSampleBufferWithFilter_configuration_completionHandler_(self.filter,self.config,cb))
            timings['native_ms']=(time.perf_counter()-t)*1000
            data,w,h,stride,pts,display,copy_ms,meta,_=self.n.payload(sample)
            t=time.perf_counter();image=Image.frombytes('RGBA',(w,h),data,'raw','BGRA',stride).convert('RGB')
            timings.update(copy_ms=copy_ms,convert_ms=(time.perf_counter()-t)*1000)
        t=time.perf_counter();self.check();timings['geometry_post_ms']=(time.perf_counter()-t)*1000;self.seq+=1;self.validate(image)
        timings['capture_rgb_ms']=(time.perf_counter()-start)*1000
        return FrameResult(image,self.seq,'complete',pts,display,timings,meta)
    def validate(self,image):
        """拒绝系统隐式改尺寸，不缩放来迁就素材。"""
        if image.size!=(self.identity.pixel_width,self.identity.pixel_height):raise RuntimeError(f'pixel geometry changed {image.size}')
    def close(self):
        """释放请求式临时文件，重复关闭安全。"""
        if self.closed:return
        self.closed=True;self.temp.cleanup()

_SINK_CLASS = None

class StreamSource(CaptureSource):
    """常驻系统流仅保留最新完整帧，原始像素和元数据同槽发布。"""
    def __init__(self,native,identity,hz):
        """准备流并有界等待首个完整帧，费用归启动指标。"""
        super().__init__(native,identity,'stream');self.slot=LatestSlot();self.errors=[];self.error_count=0;self.stream=None;self.last_read=0
        from Foundation import NSObject
        global _SINK_CLASS
        n=native;sc=n.sc;objc=n.objc
        if _SINK_CLASS is None:
            class ExperimentCaptureSink(NSObject,protocols=[objc.protocolNamed('SCStreamOutput'),objc.protocolNamed('SCStreamDelegate')]):
                def stream_didOutputSampleBuffer_ofType_(self,stream,sample,kind):
                    """串行回调只复制合格像素，不运行模板匹配。"""
                    owner=self.owner;n=owner.n;sc=n.sc;objc=n.objc
                    if kind!=sc.SCStreamOutputTypeScreen:return
                    try:
                        with objc.autorelease_pool():
                            a=n.cm.CMSampleBufferGetSampleAttachmentsArray(sample,False)
                            status=int(a[0].get(sc.SCStreamFrameInfoStatus,-1)) if a else -1
                            names={0:'complete',1:'idle',2:'blank',3:'suspended',4:'started',5:'stopped'}
                            name=names.get(status,'invalid')
                            payload=n.payload(sample) if name=='complete' else None
                            if payload is not None:owner.check()
                            owner.slot.publish(name,payload)
                    except Exception as exc:
                        owner.record_error(exc)
                        owner.slot.publish('error')
                def stream_didStopWithError_(self,stream,error):
                    """记录系统停止错误并撤销可交付帧。"""
                    owner=self.owner
                    owner.record_error(error)
                    owner.slot.publish('error')
            _SINK_CLASS=ExperimentCaptureSink
        self.sink=_SINK_CLASS.alloc().init();self.sink.owner=self
        try:
            self.filter,self.config=n.configure(identity,hz)
            self.stream=sc.SCStream.alloc().initWithFilter_configuration_delegate_(self.filter,self.config,self.sink)
            ok,error=self.stream.addStreamOutput_type_sampleHandlerQueue_error_(self.sink,sc.SCStreamOutputTypeScreen,None,None)
            if not ok:raise RuntimeError(str(error))
            n.wait(lambda cb:self.stream.startCaptureWithCompletionHandler_(cb))
            end=time.monotonic()+3
            while self.slot.frame is None and time.monotonic()<end:n.pump(.003)
            if self.slot.frame is None:raise TimeoutError('no complete frame before deadline; events='+repr(self.slot.statuses))
            self.slot.take()
        except BaseException as cause:
            stop_error=None
            try:self.close()
            except Exception as exc:stop_error=str(exc)
            raise SourceSetupError(cause,stop_error,dict(self.slot.statuses),list(self.errors),self.error_count) from cause
    def record_error(self,error):
        """错误总数不截断，文本只保留前八条避免无限增长。"""
        self.error_count+=1
        if len(self.errors)<8:self.errors.append(str(error))
    def capture(self):
        """读取最新帧时保留真实源时间，重复序号显式标注。"""
        start=time.perf_counter();self.check();sequence,payload=self.slot.take()
        data,w,h,stride,pts,display,copy_ms,meta,rawmeta=payload
        scale=rawmeta.get(self.n.sc.SCStreamFrameInfoContentScale)
        factor=rawmeta.get(self.n.sc.SCStreamFrameInfoScaleFactor)
        rect=meta.get('content_rect_values')
        validate_stream_geometry(self.identity,w,h,scale,factor,rect)
        t=time.perf_counter();image=Image.frombytes('RGBA',(w,h),data,'raw','BGRA',stride).convert('RGB')
        timings={'convert_ms':(time.perf_counter()-t)*1000,'callback_copy_ms':copy_ms,'capture_rgb_ms':(time.perf_counter()-start)*1000}
        status='duplicate' if sequence==self.last_read else 'complete';self.last_read=sequence
        return FrameResult(image,sequence,status,pts,display,timings,meta)
    def close(self):
        """先封闭单槽，再有界停止系统流；超时明确失败。"""
        if self.closed:return
        self.slot.close()
        try:
            if self.stream is not None:self.n.wait(lambda cb:self.stream.stopCaptureWithCompletionHandler_(cb))
        finally:super().close()

class FrozenBackend:
    """让既有批量匹配只读取本次图像，所有候选共用该图。"""
    def __init__(self,image,identity):
        """绑定图像与原始逻辑尺寸，不采集真实窗口。"""
        self.image=image;self.identity=identity
    def screenshot(self):
        """返回本轮已经取得的图像。"""
        return self.image
    def size(self):
        """保留原始逻辑到像素比例。"""
        return self.identity.width,self.identity.height

def match_frame(frame,identity,rules):
    """在统一输出上检查所有既有素材并记录实际执行数。"""
    from game_automation.platform.desktop.adapters.image_matching import PyAutoGuiScreenImageLocator
    from game_automation.portable.domain import ImageSearchRequest
    requests=tuple(ImageSearchRequest(c.template,c.search.region,c.search.min_confidence or .9) for c in rules.candidates)
    results=PyAutoGuiScreenImageLocator(FrozenBackend(frame.image,identity)).locate_requests(requests,stop_on_first_match=False)
    found=[(c.name,r.match.confidence) for c,r in zip(rules.candidates,results,strict=True) if r.match]
    return {'checked':len(results),'state':max(found,key=lambda x:x[1])[0] if found else '未知','scores':[{'state':c.name,'score':r.best_confidence,'found':r.found} for c,r in zip(rules.candidates,results,strict=True)]}

def run_case(n,identity,rules,method,samples,round_index,evidence_dir=None):
    """一次启动及逐轮取帧，原始错误与停流结果都保留。"""
    source=None;rows=[];errors=[];startup=None;startup_attempt=None;stop_error=None;setup_failure=None
    cpu0=time.process_time();child0=resource.getrusage(resource.RUSAGE_CHILDREN);wall0=time.perf_counter()
    try:
        t=time.perf_counter();source=StreamSource(n,identity,int(method.split('_')[-1])) if method.startswith('stream_') else CaptureSource(n,identity,method)
        startup=(time.perf_counter()-t)*1000;startup_attempt=startup
        deadline=time.monotonic()
        for index in range(samples):
            n.pump(max(0,deadline-time.monotonic()));started=time.perf_counter()
            try:
                with n.objc.autorelease_pool():
                    frame=source.capture();read_completed=time.perf_counter();host=n.host_now()
                    result=match_frame(frame,identity,rules);ended=time.perf_counter()
                    pts_age,pts_status=source_age(host,frame.pts_host_seconds);display_age,display_status=source_age(host,frame.display_host_seconds)
                    delta=(frame.pts_host_seconds-frame.display_host_seconds)*1000 if pts_status=='valid' and display_status=='valid' else None
                    row={'index':index,'success':True,'sequence':frame.sequence,'status':frame.status,'hash':hashlib.sha256(frame.image.tobytes()).hexdigest(),'timings':frame.timings,'match_ms':(ended-read_completed)*1000,'read_match_ms':(ended-started)*1000,'pts_seconds':frame.pts_host_seconds if pts_status in ('valid','future') else None,'display_host_seconds':frame.display_host_seconds if display_status in ('valid','future') else None,'pts_age_ms':pts_age,'pts_time_status':pts_status,'display_age_ms':display_age,'display_time_status':display_status,'pts_display_delta_ms':delta,'metadata':frame.metadata,**result}
                    if evidence_dir and index==0:
                        evidence_dir.mkdir(parents=True,exist_ok=True);frame.image.save(evidence_dir/f'r{round_index}-{method}.png')
                    frame.image.close();rows.append(row)
            except Exception as exc:
                errors.append(str(exc));rows.append({'index':index,'success':False,'error':str(exc),'elapsed_ms':(time.perf_counter()-started)*1000})
            deadline=max(deadline+.2,time.monotonic())
    except Exception as exc:
        errors.append(str(exc))
        if startup_attempt is None:startup_attempt=(time.perf_counter()-t)*1000
        if isinstance(exc,SourceSetupError):
            setup_failure=exc;stop_error=exc.stop_error
            if stop_error:errors.append('stop: '+stop_error)
    finally:
        if source is not None:
            try:source.close()
            except Exception as exc:stop_error=str(exc);errors.append('stop: '+stop_error)
    wall=time.perf_counter()-wall0;child=resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu=time.process_time()-cpu0+child.ru_utime-child0.ru_utime+child.ru_stime-child0.ru_stime
    successful=[r for r in rows if r['success']]
    def metrics(records):
        """按明确样本集合汇总成本与源事件年龄。"""
        fields={'capture_rgb_ms':[r['timings']['capture_rgb_ms'] for r in records],'read_match_ms':[r['read_match_ms'] for r in records],'pts_age_ms':[r['pts_age_ms'] for r in records if r['pts_age_ms'] is not None],'display_age_ms':[r['display_age_ms'] for r in records if r['display_age_ms'] is not None]}
        return {k:summarize(v) for k,v in fields.items()}
    warm=[r for r in successful if r['index']>0]
    stream_source=source is not None and hasattr(source,'slot')
    source_events=dict(source.slot.statuses) if stream_source else setup_failure.source_events if setup_failure else None
    callback_errors=list(source.errors) if stream_source else setup_failure.callback_errors if setup_failure else []
    callback_count=source.error_count if stream_source else setup_failure.callback_error_count if setup_failure else 0
    time_counts={kind:{status:sum(r[kind+'_time_status']==status for r in successful) for status in ('valid','missing','invalid','future')} for kind in ('pts','display')}
    return {'round':round_index,'method':method,'startup_ms':startup,'startup_attempt_ms':startup_attempt,'requested_samples':samples,'attempts':len(rows),'read_successes':len(successful),'new_frame_successes':sum(r['status']=='complete' for r in successful),'successes':len(successful),'errors':errors,'stop_error':stop_error,'callback_errors':callback_errors,'callback_error_count':callback_count,'performance_eligible':not errors and callback_count==0,'time_status_counts':time_counts,'unique_sequences':len({r['sequence'] for r in successful}),'unique_hashes':len({r['hash'] for r in successful}),'duplicate_reads':sum(r['status']=='duplicate' for r in successful),'source_events':source_events,'cpu_seconds_parent_plus_children':cpu,'wall_seconds':wall,'cpu_one_core_percent':cpu/wall*100 if wall else None,'peak_rss_bytes_process_lifetime':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'rss_scope':'macOS bytes, process lifetime peak; not case-specific, excludes WindowServer/GPU','first_attempt':rows[0] if rows else None,'summary_all':metrics(successful),'summary_warm':metrics(warm),'samples':rows}

def main(argv=None):
    """运行明确窗口的多轮交替实验，不请求权限或操作目标应用。"""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,default=Path.cwd(),help='Star checkout used only for existing matching imports')
    p.add_argument('--window-id',type=int,required=True);p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--methods',default='baseline,quartz,sck_shot,stream_5,stream_10,stream_15');p.add_argument('--rounds',type=int,default=5);p.add_argument('--samples',type=int,default=8)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-dir',type=Path)
    args=p.parse_args(argv);methods=args.methods.split(',')
    if args.rounds<1 or args.samples<1 or any(m not in {'baseline','quartz','sck_shot','stream_5','stream_10','stream_15'} for m in methods):p.error('invalid rounds, samples or methods')
    sys.path.insert(0,str(args.source_root.resolve()/'src'))
    from game_automation.portable.application.window_state_rules import load_window_state_rules
    rules=load_window_state_rules(args.workspace)
    if args.output.resolve().is_relative_to((args.workspace/'assets').resolve()) or args.evidence_dir and args.evidence_dir.resolve().is_relative_to((args.workspace/'assets').resolve()):p.error('output cannot modify assets')
    n=Native()
    if not n.q.CGPreflightScreenCaptureAccess():raise RuntimeError('screen capture permission missing; not requesting')
    item=n.window(args.window_id);b=item['kCGWindowBounds']
    identity=Identity(args.window_id,int(item['kCGWindowOwnerPID']),item.get('kCGWindowName'),rules.width,rules.height,rules.pixel_width,rules.pixel_height);identity.validate(item)
    report={'scope':'exploration only, native control thread main runloop; no production worker equivalence claim','identity':identity.__dict__,'sample_reader_hz':5,'geometry_scope':'stream contentRect must parse and match original logical rectangle, contentScale1 and scaleFactor expected; an unrecognized metadata representation fails the read, pending real metadata validation','confirmation_scope':'read success is not new frame success; duplicate reads never count as new source frames; this tool does not implement two-frame confirmation','comparison':'capture_rgb is request duration for snapshots but cache read for streams; compare source age separately, not a speedup ratio','cpu_scope':'parent plus child CPU for whole case including capture, matching, hashes and optional evidence PNG; excludes report JSON outside case, WindowServer and GPU','time_scope':'display_age_ms is host-now minus SDK mach-absolute displayTime converted by CoreMedia; WindowServer event-to-read age, not input-to-display latency. pts_age_ms is unproven clock-domain diagnostic; compare pts_display_delta_ms, never a confirmed source latency.','legacy_quartz':'SDK deprecated14/obsoleted15; experiment only, not production default','cases':[]}
    try:
        for round_index in range(args.rounds):
            order=methods[round_index%len(methods):]+methods[:round_index%len(methods)]
            for method in order:
                print(f'round {round_index+1}/{args.rounds} {method}',file=sys.stderr,flush=True)
                case=run_case(n,identity,rules,method,args.samples,round_index,args.evidence_dir)
                report['cases'].append(case);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(f"completed {case['successes']}/{case['attempts']} errors={len(case['errors'])}",file=sys.stderr,flush=True)
                if case['stop_error']:raise RuntimeError('stream cleanup failed; refusing next case')
    finally:args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return 1 if any(not c['performance_eligible'] for c in report['cases']) else 0

if __name__=='__main__':raise SystemExit(main())
