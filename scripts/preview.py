"""Local disposable preview. Never reads .env or connects to MySQL."""
import os
import sys
from pathlib import Path
os.environ['PYTHON_DOTENV_DISABLED']='1'
os.environ['SEHATWARGA_TESTING']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import create_test_app


def preview_app():
    app=create_test_app()
    result=app.test_cli_runner().invoke(args=['seed-demo','--admin-password=AdminDemo123!','--citizen-password=WargaDemo123!'])
    if result.exit_code:
        raise RuntimeError('Unable to seed disposable preview')
    return app


if __name__=='__main__':
    preview_app().run(host='127.0.0.1',port=5055,debug=False)
