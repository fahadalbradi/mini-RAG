import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from routes import base

app = FastAPI()
app.include_router(base.base_router)