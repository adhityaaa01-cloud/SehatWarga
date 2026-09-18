import os
os.environ["SEHATWARGA_TESTING"] = "1"
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def create_test_app():
    from app import create_app
    from app.extensions import db
    from config import TestingConfig
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
    return app
