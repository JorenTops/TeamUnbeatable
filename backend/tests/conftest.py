import os
import secrets

os.environ.setdefault("TTG_DEMO_LOGIN", "true")
# Random per test run: no hard-coded key in the repository.
os.environ.setdefault("TTG_SECRET_KEY", secrets.token_urlsafe(48))
