"""Capture frontend geometry and animations at a reproducible phase.
Usage: .venv/bin/python scripts/check_performance_visual.py FRONTEND OUTPUT
Run once with a baseline frontend directory and once with frontend/.
Only the test fixture freezes animation clocks, transitions, and observers.
The application files are never changed by this check.
"""
import sys, threading, json, logging
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from preview import preview_app
from jinja2 import FileSystemLoader
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app=preview_app(); frontend=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
app.static_folder=str(frontend/'static');app.jinja_loader=FileSystemLoader(str(frontend/'templates'))
server=make_server('127.0.0.1',5057,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
errors=[];results=[]
try:
 with sync_playwright() as p:
  b=p.chromium.launch(args=["--disable-gpu"])
  for width in [375,1440]:
   page=b.new_page(viewport={'width':width,'height':1000})
   page.on('pageerror',lambda e:errors.append(str(e)))
   # Freeze only in the QA fixture: seeded initial canvas and fixed CSS phase.
   page.add_init_script('''let seed=12345; Math.random=()=>((seed=(seed*16807)%2147483647)-1)/2147483646;
   document.addEventListener('pointermove',e=>e.stopImmediatePropagation(),true);
   const IO=window.IntersectionObserver;window.IntersectionObserver=class extends IO{constructor(cb,options){super((entries,o)=>{if(!window.__qaFreeze)cb(entries,o)},options)}};
   const raf=window.requestAnimationFrame; window.requestAnimationFrame=fn=>fn.name==='drawNetwork'?999999:raf.call(window,fn);''')
   page.goto('http://127.0.0.1:5057/');page.evaluate('document.fonts.ready')
   page.evaluate('''async()=>{for(const i of document.images){i.loading='eager';await i.decode().catch(()=>{});}document.querySelectorAll('.reveal-item,.journey-reveal').forEach(e=>e.classList.add('is-visible'));}''')
   page.wait_for_timeout(700)
   page.evaluate('window.__qaFreeze=true')
   page.add_style_tag(content='*,*::before,*::after { transition: none !important; }')
   animation_data=page.evaluate('''()=>document.getAnimations().filter(a=>a.animationName).map(a=>{const t=a.effect.getTiming();a.pause();a.currentTime=t.iterations===Infinity?1234:100000;return {name:a.animationName||'transition',duration:t.duration,delay:t.delay,iterations:String(t.iterations),easing:t.easing};}).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))''')
   page.screenshot(path=str(out/f'{width}-motion.png'),full_page=True)
   page.screenshot(path=str(out/f'{width}-repeat.png'),full_page=True)
   results.append({'width':width,'animations':animation_data,'shards':page.locator('.energy-shards i').count(),'geometry':page.evaluate('''()=>[...document.querySelectorAll('body *')].filter(e=>!e.closest('svg')).map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,cls:typeof e.className==='string'?e.className:'',x:r.x,y:r.y,width:r.width,height:r.height,transform:s.transform,opacity:s.opacity,filter:s.filter};})''')})
   page.close()
  b.close()
finally:server.shutdown()
(out/'results.json').write_text(json.dumps({'results':results,'errors':errors},indent=2));print(json.dumps({'pages':len(results),'errors':errors}))
