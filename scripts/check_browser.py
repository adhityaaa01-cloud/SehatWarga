"""Responsive/interaction checks against a disposable SQLite development server.
Install optional tooling: pip install playwright; python -m playwright install chromium.
Set BROWSER_EXECUTABLE only to use an already-installed Chromium executable.
"""
import os
import json
import threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
from preview import preview_app

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'qa';OUT.mkdir(exist_ok=True)
app=preview_app()
server=make_server('127.0.0.1',5055,app,threaded=True)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
checks=[];errors=[]
def check(name,condition,details=None):
    checks.append({'check':name,'pass':bool(condition),'details':details})

try:
 with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BROWSER_EXECUTABLE') or None,args=['--no-sandbox'])
    for role in ['public','citizen','admin']:
      context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
      page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
      if role!='public':
        page.goto('http://127.0.0.1:5055/login');page.locator('#email').fill('admin.demo@sehatwarga.test' if role=='admin' else 'warga.demo@sehatwarga.test');page.locator('#password').fill('AdminDemo123!' if role=='admin' else 'WargaDemo123!');page.locator('button[type=submit]').last.click();page.wait_for_url('**/dashboard')
      paths={'public':['/','/login','/register','/facilities','/assistant'],'citizen':['/citizen/dashboard','/citizen/services','/citizen/services/request','/citizen/card','/citizen/complaints/create'],'admin':['/admin/dashboard','/admin/services','/admin/facilities']}[role]
      for width in [320,375,480,768,1024,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        for path in paths:
          response=page.goto('http://127.0.0.1:5055'+path,wait_until='domcontentloaded');page.wait_for_timeout(80)
          check(f'{role} {path} {width} render',response.status==200)
          overflow=page.evaluate('''() => [...document.querySelectorAll('body *')].filter(e => {const r=e.getBoundingClientRect();const c=getComputedStyle(e);return r.width&&r.right>innerWidth+1&&c.visibility!=='hidden'&&!e.closest('.table-responsive,.leaflet-container,.site-navigation,.sr-only');}).map(e=>e.tagName+'.'+e.className).slice(0,12)''')
          check(f'{role} {path} {width} no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),overflow)
          check(f'{role} {path} {width} main heading',page.locator('h1').count()==1)
          if width in [375,1440] and path in ['/','/assistant','/citizen/dashboard','/admin/dashboard']:
            page.screenshot(path=str(OUT/(role+'-'+path.strip('/').replace('/','-')+'-'+str(width)+'.png')),full_page=True)
        if width<1024:
          page.locator('#nav-toggle').click();check(f'{role} drawer {width} opens',page.locator('#nav-toggle').get_attribute('aria-expanded')=='true');check(f'{role} drawer {width} scroll lock',page.evaluate('getComputedStyle(document.body).overflow')=='hidden')
          page.locator('#nav-close').click();check(f'{role} drawer {width} close button clickable',page.locator('#nav-toggle').get_attribute('aria-expanded')=='false')
          page.locator('#nav-toggle').click()
          expect(page.locator('#nav-close')).to_be_focused()
          page.keyboard.press('Shift+Tab');check(f'{role} drawer {width} focus trap',page.locator('#site-navigation').evaluate('e=>e.contains(document.activeElement)'))
          page.keyboard.press('Escape');check(f'{role} drawer {width} escape',page.locator('#nav-toggle').get_attribute('aria-expanded')=='false')
          check(f'{role} drawer {width} focus restored',page.locator('#nav-toggle').evaluate('e=>e===document.activeElement'))
          page.locator('#nav-toggle').click();page.locator('#nav-overlay').click(position={'x':2,'y':500});check(f'{role} drawer {width} overlay',page.locator('#nav-toggle').get_attribute('aria-expanded')=='false')
      if role=='public':
        page.goto('http://127.0.0.1:5055/assistant');page.locator('#chat-input').fill('Berapa tarif iuran?');page.locator('#chat-submit').click();page.get_by_text('Rp50.000',exact=False).last.wait_for();check('assistant fallback rendered',True)
        page.locator('#chat-input').fill('<script>alert(1)</script>');page.locator('#chat-submit').click();page.locator('#chat-submit:not([disabled])').wait_for();check('assistant user content stays text',page.locator('#chat-messages script').count()==0)
      context.close()
    browser.close()
finally:
 server.shutdown()
check('no browser JavaScript exceptions',not errors,errors)
(OUT/'browser-results.json').write_text(json.dumps(checks,indent=2))
failures=[c for c in checks if not c['pass']]
print(json.dumps({'checks':len(checks),'pass':len(checks)-len(failures),'fail':len(failures),'failures':failures},indent=2))
raise SystemExit(bool(failures))
