"""Regenerate the README business reference from the active service constants."""
import os
import sys
from pathlib import Path
os.environ['PYTHON_DOTENV_DISABLED']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.services.assistant_knowledge import KNOWLEDGE_TOPICS

START='<!-- BEGIN VERIFIED BUSINESS KNOWLEDGE -->'
END='<!-- END VERIFIED BUSINESS KNOWLEDGE -->'

def generated_block():
    return START+'\n\n## Referensi business logic aktif\n\n'+ '\n\n'.join('### '+name.replace('_',' ').title()+'\n\n'+text for name,text in KNOWLEDGE_TOPICS.items())+'\n\n'+END

if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'README.md'
    text=path.read_text()
    block=generated_block()
    if '--check' in sys.argv:
        if block not in text:
            raise SystemExit('README knowledge reference is outdated; run python scripts/sync_knowledge.py')
        print('README knowledge reference matches active constants')
    else:
        if START in text:
            start=text.index(START);end=text.index(END,start)+len(END);text=text[:start]+block+text[end:]
        else:text+='\n\n'+block+'\n'
        path.write_text(text)
