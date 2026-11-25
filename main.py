from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import urllib.parse
import urllib.request
import json
import os
import re

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


class TokenRequest(BaseModel):
    token_input: str


def extract_eat(raw: str) -> tuple[str, dict]:
    raw = raw.strip()
    url_params = {}
    if "?" in raw:
        try:
            parsed = urllib.parse.urlparse(raw)
            params = urllib.parse.parse_qs(parsed.query)
            url_params = {k: v[0] for k, v in params.items()}
        except Exception:
            pass
    match = re.search(r'[?&]eat=([^&#\s]+)', raw)
    eat = urllib.parse.unquote(match.group(1)) if match else raw
    return eat, url_params


def try_eat_freefire(eat_input: str) -> dict | None:
    """eat.freefire.site backend"""
    try:
        payload = json.dumps({"token_input": eat_input}).encode()
        req = urllib.request.Request(
            "https://eat.freefire.site/api/convert",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Origin": "https://eat.freefire.site",
                "Referer": "https://eat.freefire.site/",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            if data.get("status") == "success" and data.get("access_token"):
                return data
    except Exception:
        pass
    return None


def try_bio_ffofficial(eat_input: str) -> dict | None:
    """bio.ffofficial.shop backend"""
    try:
        payload = json.dumps({"eat_input": eat_input}).encode()
        req = urllib.request.Request(
            "https://bio.ffofficial.shop/api/token",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Origin": "https://bio.ffofficial.shop",
                "Referer": "https://bio.ffofficial.shop/token",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            if data.get("access_token"):
                return {"status": "success", **data}
    except Exception:
        pass
    return None


def try_killersharma(eat_input: str) -> dict | None:
    """KillerSharma backend"""
    try:
        url = "https://access.killersharmabot.online/access?access_token=" + urllib.parse.quote(eat_input)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            if data.get("access_token") or data.get("token"):
                return {"status": "success", **data}
    except Exception:
        pass
    return None


@app.get("/", response_class=HTMLResponse)
async def root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse("<h1>FF Token API</h1>")


@app.post("/api/convert")
async def convert_token(req: TokenRequest):
    if not req.token_input or len(req.token_input) < 10:
        raise HTTPException(status_code=400, detail="Invalid token_input")

    eat, url_params = extract_eat(req.token_input)

    if len(eat) < 10:
        raise HTTPException(status_code=400, detail="Could not extract EAT token")

    # Fallback chain: 3 backends try karo
    result = (
        try_eat_freefire(eat)
        or try_eat_freefire(req.token_input)
        or try_bio_ffofficial(eat)
        or try_killersharma(eat)
    )

    if result and result.get("access_token"):
        return {
            "status": "success",
            "access_token": result.get("access_token", ""),
            "account_id": result.get("account_id", url_params.get("account_id", "")),
            "nickname": result.get("nickname", url_params.get("nickname", "")),
            "region": result.get("region", url_params.get("region", "")),
        }
    else:
        raise HTTPException(status_code=502, detail="All backends failed. Token may be expired.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
