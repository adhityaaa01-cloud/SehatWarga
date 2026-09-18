"""Optional axe audit. Set AXE_SOURCE to axe.min.js and optionally BROWSER_EXECUTABLE.
Requires playwright and npm package axe-core, outside Flask runtime.
"""
import os,sys,threading,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from preview import preview_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
app=preview_app();server=make_server('127.0.0.1',5056,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE') or None,headless=True,args=['--no-sandbox'])
 for role in ['public','citizen','admin']:
  context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=context.new_page()
  if role!='public':
   page.goto('http://127.0.0.1:5056/login');page.locator('#email').fill('admin.demo@sehatwarga.test' if role=='admin' else 'warga.demo@sehatwarga.test');page.locator('#password').fill('AdminDemo123!' if role=='admin' else 'WargaDemo123!');page.locator('button[type=submit]').last.click();page.wait_for_url('**/dashboard')
  paths={'public':['/','/login','/register','/facilities','/assistant'],'citizen':['/citizen/dashboard','/citizen/services/request','/citizen/card','/citizen/complaints/create'],'admin':['/admin/dashboard','/admin/facilities']}[role]
  for width in [375,1440]:
   page.set_viewport_size({'width':width,'height':1000})
   for path in paths:
    page.goto('http://127.0.0.1:5056'+path);page.add_script_tag(path=os.environ['AXE_SOURCE'])
    result=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))")
    results.append({'role':role,'path':path,'width':width,'violations':result})
  context.close()
 browser.close()
server.shutdown()
(ROOT/'qa/accessibility-results.json').write_text(json.dumps(results,indent=2))
print(json.dumps([r for r in results if r['violations']],indent=2))

raise SystemExit(any(r["violations"] for r in results))
