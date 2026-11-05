"""Build the customer bundle and standalone, interactive introduction."""
import base64
import json
from pathlib import Path
import shutil
import stat
from zipfile import ZipFile,ZIP_DEFLATED,ZipInfo
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'library-files'
STAGE=ROOT.parent/'scratch'/'fatfish-v4-delivery'
NAME='大肥鱼-Codex演示交付-v4'
EXCLUDED={'data','legacy-v1','__pycache__','.git','.venv','node_modules'}

def intro(standalone=False):
 spec=json.loads((ROOT/'static/pets/manifest.json').read_text('utf-8'))
 if standalone:
  for form in spec['forms'].values():
   raw=(ROOT/'static'/form['atlas'].lstrip('/')).read_bytes()
   form['atlas']='data:image/png;base64,'+base64.b64encode(raw).decode()
  asset_base=''
 else:asset_base='项目/static/'
 player=(ROOT/'static/pet.js').read_text('utf-8')
 markup=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>大肥鱼 · Codex 工程演示</title><style>
 *{box-sizing:border-box}body{margin:0;background:#f8f9fc;color:#293f5c;font:14px/1.8 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1040px;margin:auto;padding:34px 38px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #dfe7f1;padding-bottom:20px;font-size:12px;color:#8295af}.brand{font-size:21px;font-weight:750;color:#3e6398}.tag{background:#e9f0fa;padding:5px 12px;border-radius:20px;font-size:10px}.hero{display:grid;grid-template-columns:1fr 1fr;gap:36px;align-items:center;margin:30px 0}.eyebrow{font-size:10px;letter-spacing:2px;color:#899fbc}h1{font-size:37px;line-height:1.35;letter-spacing:-1px;margin:15px 0}h1 em{font-style:normal;color:#6f91c5}.lead{color:#7d8ea6;font-size:13px}.pill{display:inline-block;padding:4px 9px;background:#edf2fa;border-radius:7px;font-size:10px;margin:4px 4px 4px 0;color:#6a83aa}.stage{border:1px solid #d9e4f3;border-radius:22px;background:radial-gradient(ellipse at 50% 65%,#fff 0,#edf3fe 70%);padding:13px 17px 14px}.stage-head{display:flex;justify-content:space-between;align-items:center;font-size:10px;color:#91a3bf}.switch{display:flex;gap:5px}.switch button{padding:5px 14px}.canvas-wrap{height:350px}canvas{width:100%;height:100%;display:block}.actions{display:flex;justify-content:center;gap:7px;flex-wrap:wrap}button{border:1px solid #cbd9ed;border-radius:9px;background:white;color:#5b7cac;padding:7px 13px;cursor:pointer;font:11px system-ui}button:hover,button.active{background:#dce8fa;border-color:#b5cbed;color:#345c98}.caption{font-size:10px;color:#99a5b6;margin:9px 0 0;text-align:center}.features{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin:24px 0}.feature{background:#fff;border:1px solid #e0e7f1;border-radius:13px;padding:17px}.feature b{display:block;font-size:13px;margin-bottom:6px}.feature p{font-size:11px;color:#8292a8;margin:0}.section{padding:22px 0;border-top:1px solid #dfe7f1}h2{font-size:19px;margin:0 0 13px}.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.step strong{font-size:12px;display:block;margin-bottom:6px}.number{font-size:10px;color:#9aacc3;margin-bottom:5px}.step p{font-size:11px;color:#7c8fa9;margin:0}.callout{padding:14px 17px;background:#ecf3fb;border-left:3px solid #b0c6e5;border-radius:0 9px 9px 0;font-size:11px;color:#748cae;margin-top:18px}a{color:#5b7eae}code{font-size:11px;color:#53739c}.demo{display:grid;grid-template-columns:1fr 1fr;gap:25px;font-size:11px;color:#7d8fa7}.demo p{margin:5px 0}.boundary{color:#8e9bb0;font-size:10px;line-height:1.9}footer{font-size:9px;line-height:1.9;color:#9aa8bb;border-top:1px solid #e0e7f0;padding:18px 0 0}.success{color:#5d8c79}.print-only{display:none}details{font-size:10px;color:#8a9eb8;margin-top:12px}summary{cursor:pointer}@media(max-width:650px){main{padding:20px}.hero{grid-template-columns:1fr;gap:22px}h1{font-size:31px}.features,.steps,.demo{grid-template-columns:1fr}.canvas-wrap{height:330px}.tag{font-size:9px}header{gap:8px}}@media print{@page{size:A4;margin:14mm}body{background:white;font-size:10px}main{padding:0;max-width:none}header{padding-bottom:10px}.hero{grid-template-columns:1fr 1fr;gap:22px;margin:12px 0}h1{font-size:29px}.lead{font-size:11px}.canvas-wrap{height:210px}.stage{padding:8px 13px}.actions,details,.caption{display:none}.stage-head{margin-bottom:0}.features{gap:10px;margin:11px 0}.feature{padding:12px}.feature p,.step p{font-size:9px}.section{padding:11px 0;break-inside:avoid}h2{font-size:15px;margin-bottom:10px}.steps{gap:15px}.callout{margin-top:12px;padding:11px;font-size:9px}.demo{font-size:9px;gap:20px}.boundary{font-size:9px}footer{font-size:8px;padding-top:10px}.print-only{display:inline}.eyebrow{font-size:8px}}
 </style></head><body><main>
 <header><span class="brand">≈ 大肥鱼</span><span class="tag">CODEX · ENGINEERING DEMO · v4</span></header>
 <section class="hero"><div><div class="eyebrow">FROM A PROMPT TO A WORKING COMPANION</div><h1>一句话，养出一只<br><em>会动、会聊、会工作的</em><br>鲸鱼娘。</h1><p class="lead">由 Codex 在这段对话中完成工程实现。<br>形象、动画、界面、接入、任务、验证与交付，<br>都能在包里的源码中找到。</p><span class="pill">Q 版 / 成熟版</span><span class="pill">原生桌宠</span><span class="pill">DeepSeek 接入</span><span class="pill">网页与截图</span></div>
 <div class="stage"><div class="stage-head"><div class="switch"><button id="chibi" class="active">Q 版</button><button id="mature">成熟版</button></div><span id="status">正在加载…</span></div><div class="canvas-wrap"><canvas id="preview" role="img" aria-label="鲸鱼娘离线动作预览"></canvas></div><div class="actions"><button data-action="wave">挥手</button><button data-action="jump">跳一下</button><button data-action="feed">喂白饭</button><button data-action="sleep">睡一会儿</button><button id="motion">暂停动画</button></div><p class="caption">直接点按钮试试 · 此页是离线形象预览，未调用 AI</p></div></section>
 <div class="features"><div class="feature"><b>看得见的角色</b><p>两种比例，真实逐帧动画与变身过渡。独立桌宠支持拖拽、置顶、右键菜单和聊天气泡。</p></div><div class="feature"><b>接得上的大脑</b><p>官网创建 Key，检测模型与余额，收到真实回复后再启用。网页和桌宠共用配置。</p></div><div class="feature"><b>查得到的过程</b><p>公开网页读取与截图、有限站内探索。源码、素材来源、检查脚本和验证边界随包提供。</p></div></div>
 <section class="section" id="start"><h2>快速开始 · 三步</h2><div class="steps"><div class="step"><div class="number">01 / 启动</div><strong>先有 Python，再双击桌宠</strong><p>完整程序需要 Python 3.10+（64 位）。Windows 安装时勾选 Add Python to PATH。解压后双击「启动桌宠」；首次自动安装组件。</p></div><div class="step"><div class="number">02 / 接入</div><strong>用自己的 DeepSeek API Key</strong><p>双击聊天，点「接入 / 管理 DeepSeek」。登录官方开放平台创建 Key，回填并检测。API 按官方规则计费，项目不接收官网密码。</p></div><div class="step"><div class="number">03 / 工作</div><strong>让她带回一张网页截图</strong><p>先运行「安装浏览器」，再打开养成台的「出去逛逛」。读取公开 HTTPS 网址并查看截图；配置模型后可做有限步数站内探索。</p></div></div><div class="callout">桌宠：左键拖拽，双击聊天，右键切换形态和动作。无 Key 时可体验明确标注的预设互动；官网账号登录状态不会自动授权本项目调用 API。</div></section>
 <section class="section"><h2>给程序员朋友的 3 分钟演示</h2><div class="demo"><div><p><b>先看体验：</b>切换 Q 版 / 成熟版 → 挥手、喂饭 → 拖动独立桌宠 → 双击聊天。</p><p><b>再看能力：</b>接入自己的 Key，临时出一道题；随后读取一个公开网页，核对结果和截图。</p></div><div><p><b>最后看工程：</b><code>provider.py</code> 管接入，<code>pet_core.py</code> 管动作，<code>tests/</code> 可重跑验证。</p><p><b>体验不顺：</b>运行「诊断环境」。报告不包含 Key、令牌或聊天正文。</p></div></div></section>
 <section class="section"><h2>已知边界，说清楚</h2><p class="boundary">已做本机 HTTP、浏览器、公开 HTTPS 和 Qt 离屏检查。DeepSeek 接入流程用明确的本地测试服务验证，尚无真实付费 Key 的联调记录；Windows/macOS 桌面效果、QQ / 企业微信实号和 Android 真机仍需对方环境验证。Q 版为逐帧动画，成熟版为六姿态与程序过渡，非 Live2D。微信仅支持企业微信群机器人发送；手机通道需授权 Android + ADB。</p><p class="boundary">自己的 Key、聊天和截图留在运行后的 <code>data/</code>，交付包不含这些数据。Key 为本机文件保存，未加密；模型会收到当前会话近期内容。对外转发请发送原始交付包。</p></section>
 <footer>非官方、非商业社区二创，与 DeepSeek / OpenAI 无隶属或背书关系。Q 版动画：<a href="https://github.com/schrieeeffer/shenshen-codex-pet">Shenshen Pet contributors</a>，基于上善无形及 dsh-pet 社区谱系，CC BY-NC-SA 4.0；成熟版：GPT Image 二创，参考 <a href="https://treapgogo.github.io/deepseek-whale-girl/">TreapGoGo 社区三视图</a>及上善无形 / ZipZipPipe 形象链路。完整许可在交付包 ATTRIBUTION.md 与 references/licenses/。<br>官方接入依据：<a href="https://api-docs.deepseek.com/zh-cn/">DeepSeek API 文档</a> · 源码代码许可与角色素材许可分开。核对日期：2026-11-05。</footer>
 </main><script>__PLAYER__</script><script>
 const spec=__SPEC__;const pet=new FishSprite(document.getElementById('preview'),{manifest:spec,assetBase:__BASE__});window.previewPet=pet;
 const status=document.getElementById('status');pet.ready.then(()=>status.textContent='Q 版 · 待机').catch(()=>status.textContent='请完整解压后打开本页');
 for(const id of ['chibi','mature'])document.getElementById(id).onclick=()=>pet.setForm(id);
 document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>pet.play(b.dataset.action));document.getElementById('motion').onclick=()=>pet.setMotion(!pet.motion);
 document.getElementById('preview').addEventListener('petstate',e=>{status.textContent=spec.forms[e.detail.form].name+' · '+spec.actions[e.detail.action];for(const id of ['chibi','mature'])document.getElementById(id).classList.toggle('active',e.detail.form===id);document.getElementById('motion').textContent=e.detail.motion?'暂停动画':'开启动画';});
 </script></body></html>'''
 return markup.replace('__PLAYER__',player).replace('__SPEC__',json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')).replace('__BASE__',json.dumps(asset_base))


def copy_project(destination):
 destination.mkdir(parents=True,exist_ok=True)
 for p in ROOT.rglob('*'):
  relative=p.relative_to(ROOT)
  if not p.is_file() or EXCLUDED.intersection(relative.parts) or p.name.startswith('.env'):continue
  target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)


def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if STAGE.exists():shutil.rmtree(STAGE)
 bundle=STAGE/NAME;bundle.mkdir(parents=True)
 copy_project(bundle/'项目')
 (bundle/'先看这里.html').write_text(intro(), 'utf-8')
 (OUT/'大肥鱼-介绍与离线预览-v4.html').write_text(intro(True),'utf-8')
 docs=bundle/'文档';docs.mkdir()
 for filename,source in [('快速上手.txt','快速开始.txt'),('使用说明.md','README.md'),('DeepSeek接入说明.md','docs/DeepSeek接入说明.md'),('验证记录.md','VALIDATION.md'),('开发维护说明.md','docs/开发维护说明.md')]:
  shutil.copy2(ROOT/source,docs/filename)
 pdf=OUT/'大肥鱼-介绍与演示指南-v4.pdf'
 if pdf.exists():shutil.copy2(pdf,docs/pdf.name)
 video=OUT/'fatfish-v4-demo.webm'
 if video.exists():
  (bundle/'演示').mkdir();shutil.copy2(video,bundle/'演示/动作与接入入口.webm')
 starts={'启动桌宠':'launcher.py --desktop','启动养成台':'launcher.py','安装浏览器':'launcher.py --install-browser','诊断环境':'doctor.py'}
 for name,command in starts.items():
  bat='@echo off\nchcp 65001 >nul\ncd /d "%~dp0项目"\nwhere py >nul 2>nul\nif %errorlevel% equ 0 (\n  py -3 '+command+'\n) else (\n  python '+command+'\n)\nif errorlevel 1 (\n  echo 请确认安装 Python 3.10 或更新版本，并完整解压本包。\n  pause\n)\n'
  (bundle/(name+'.bat')).write_bytes(bat.replace('\n','\r\n').encode('utf-8'))
  shell='#!/bin/sh\ncd "$(dirname "$0")/项目" || exit 1\npython3 '+command+'\n'
  p=bundle/(name+'.command');p.write_text(shell);p.chmod(0o755)
 (bundle/'README.txt').write_text('先打开「先看这里.html」体验形态与动作，不用安装。\n完整程序需要 Python 3.10+（64位），然后双击「启动桌宠」或「启动养成台」。\nDeepSeek 接入：在聊天区点击「接入 DeepSeek」，到官方平台创建自己的 API Key。\n更多操作见「文档」，完整源码在「项目」。\n本包不含密钥或用户数据；不要把自己运行后的 data 文件夹转发给别人。\n','utf-8')
 archive=OUT/(NAME+'.zip')
 with ZipFile(archive,'w',ZIP_DEFLATED) as z:
  for p in sorted(bundle.rglob('*')):
   if not p.is_file():continue
   name=str(p.relative_to(STAGE)).replace('\\','/')
   info=ZipInfo(name,date_time=(2026,11,5,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=(p.stat().st_mode&0xFFFF)<<16
   z.writestr(info,p.read_bytes())
  assert not any('/data/' in n or 'credentials.json' in n or '.env' in n or '__pycache__' in n for n in z.namelist())
  assert z.testzip() is None
 print('Bundle:',archive.name,round(archive.stat().st_size/1024/1024,2),'MiB')
 print('Offline introduction and staging folder ready.')

if __name__=='__main__':main()
