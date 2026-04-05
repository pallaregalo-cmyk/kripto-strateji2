from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from database import init_db
from routers import auth, users, strategies, watchlist, bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Kripto Strateji", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/api/auth",       tags=["auth"])
app.include_router(users.router,      prefix="/api/users",      tags=["users"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(watchlist.router,  prefix="/api/watchlist",  tags=["watchlist"])
app.include_router(bot.router,        prefix="/api/bot",        tags=["bot"])

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    index = os.path.join(frontend_path, "templates", "index.html")
    return FileResponse(index)
