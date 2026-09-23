"""Frontend performance regressions on a disposable SQLite app; requires Playwright.
Run: .venv/bin/python scripts/check_performance.py
Visibility is simulated for deterministic hidden-tab checks.
"""
import sys,threading,json,logging
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from preview import preview_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app=preview_app();server=make_server('127.0.0.1',5058,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[];errors=[];console=[]
def check(name,value):checks.append({'check':name,'pass':bool(value)})
try:
 with sync_playwright() as p:
  b=p.chromium.launch();page=b.new_page(viewport={'width':1440,'height':1000})
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
  page.add_init_script('''window.qa={draw:0,flush:0,listeners:0,reads:0};const raf=window.requestAnimationFrame;window.requestAnimationFrame=fn=>raf.call(window,t=>{if(fn.name==='drawNetwork')qa.draw++;if(fn.name==='flushInput')qa.flush++;fn(t)});const add=EventTarget.prototype.addEventListener;EventTarget.prototype.addEventListener=function(...args){qa.listeners++;return add.apply(this,args)};const rect=Element.prototype.getBoundingClientRect;Element.prototype.getBoundingClientRect=function(){qa.reads++;return rect.call(this)};''')
  page.goto('http://127.0.0.1:5058/');page.wait_for_timeout(1100)
  check('one hero canvas',page.locator('.motion-canvas').count()==1)
  baseline=page.evaluate('({listeners:qa.listeners,shards:document.querySelectorAll(".energy-shards i").length})')
  page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
  check('duplicate main init does not attach listeners or decorations',page.evaluate('({listeners:qa.listeners,shards:document.querySelectorAll(".energy-shards i").length})')==baseline)
  burst=page.evaluate('''async()=>{qa.reads=0;qa.flush=0;const e=document.querySelector('[data-tilt]');for(let n=0;n<100;n++)e.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,clientX:900,clientY:400}));await new Promise(requestAnimationFrame);return {reads:qa.reads,flush:qa.flush};}''')
  check('100 pointer events use one frame and one read per affected element',burst=={'reads':2,'flush':1})
  leave=page.evaluate('''async()=>{const e=document.querySelector('[data-tilt]');e.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,clientX:950,clientY:430}));e.dispatchEvent(new PointerEvent('pointerleave'));await new Promise(requestAnimationFrame);return e.style.getPropertyValue('--tilt-x')==='0deg' && e.style.getPropertyValue('--tilt-y')==='0deg';}''')
  check('pointerleave cancels pending tilt write',leave)
  before=page.evaluate('qa.draw');page.wait_for_function('(n)=>qa.draw>n',arg=before);check('visible hero canvas runs',True)
  page.evaluate('window.scrollTo(0,document.body.scrollHeight)');page.wait_for_timeout(350);before=page.evaluate('qa.draw');page.wait_for_timeout(200)
  check('offscreen canvas stops',page.evaluate('qa.draw')==before)
  check('offscreen repeating hero animations pause',page.evaluate('''()=>document.querySelector('.hero-section').getAnimations({subtree:true}).filter(a=>a.effect.getTiming().iterations===Infinity).every(a=>a.playState==='paused')'''))
  page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(350);before=page.evaluate('qa.draw');page.wait_for_function('(n)=>qa.draw>n',arg=before);check('visible canvas resumes',True)
  page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
  page.wait_for_timeout(100);before=page.evaluate('qa.draw');page.wait_for_timeout(200);check('hidden document stops canvas',page.evaluate('qa.draw')==before)
  check('hidden document pauses repeating CSS',page.evaluate('''()=>document.getAnimations().filter(a=>a.effect.getTiming().iterations===Infinity).every(a=>a.playState==='paused')'''))
  page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))");page.wait_for_function('(n)=>qa.draw>n',arg=before);check('active document resumes canvas',True)
  page.goto('http://127.0.0.1:5058/facilities');page.wait_for_timeout(500)
  check('Leaflet loaded',page.evaluate("typeof L!=='undefined'"))
  before=page.evaluate('qa.listeners')
  # Repeat actual inline initializer, including its map ID and original facility data.
  page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
  check('duplicate facility init adds no listeners',page.evaluate('qa.listeners')==before)
  check('one Leaflet container',page.locator('.leaflet-container').count()==1)
  detail=page.locator('a[href^="/facilities/"]').first.get_attribute('href')
  page.locator('.leaflet-marker-icon').first.click()
  check('facility marker opens popup',page.locator('.leaflet-popup').count()==1)
  page.context.grant_permissions(['geolocation'])
  page.context.set_geolocation({'latitude':-7.2575,'longitude':112.7521})
  page.locator('#btn-use-location').click()
  page.locator('#btn-use-location:not([disabled])').wait_for()
  check('facility geolocation updates feedback', 'Lokasi digunakan' in page.locator('#location-feedback').inner_text())
  page.goto('http://127.0.0.1:5058'+detail);page.wait_for_timeout(500)
  check('facility detail map and popup render',page.locator('.leaflet-container').count()==1 and page.locator('.leaflet-popup').count()==1)
  before=page.evaluate('qa.listeners');page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
  check('duplicate detail map init adds no listeners',page.evaluate('qa.listeners')==before)
  page.goto('http://127.0.0.1:5058/assistant');page.wait_for_timeout(250)
  before=page.evaluate('qa.listeners');page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))");check('duplicate chat init adds no listeners',page.evaluate('qa.listeners')==before)
  requests=[];page.on('request',lambda r:requests.append(r.url) if r.method=='POST' else None)
  page.locator('#chat-input').fill('Berapa tarif iuran?');page.locator('#chat-submit').click();page.locator('#chat-submit:not([disabled])').wait_for()
  check('one chat submission sends one request',len(requests)==1)
  check('chat fallback response rendered',page.get_by_text('Rp50.000',exact=False).count()>0)
  b.close()
finally:server.shutdown()
check('no JavaScript exceptions',not errors)
result={'checks':checks,'errors':errors,'console_errors':console,'pointer_burst':burst}
out=ROOT/'qa'/'performance';out.mkdir(parents=True,exist_ok=True);(out/'runtime.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
raise SystemExit(any(not c['pass'] for c in checks))
