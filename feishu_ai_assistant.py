#!/usr/bin/env python3
import os, json, time, requests
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()
APP_ID = os.getenv("FEISHU_APP_ID", "cli_a93f964c9b78dced")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "FPtiKi98JCm6oVwjdvcSvhsToSClOwx7")
token_cache = {"token": None, "expires_at": 0}

def get_token():
    global token_cache
    if token_cache["token"] and time.time() < token_cache["expires_at"]:
        return token_cache["token"]
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    r = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    data = r.json()
    if data.get("code") != 0: raise Exception(data.get("msg"))
    token_cache = {"token": data["tenant_access_token"], "expires_at": time.time() + data.get("expire", 7200) - 300}
    return token_cache["token"]

def send_msg(receive_id, text, message_id=None):
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply" if message_id else "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"receive_id": receive_id, "msg_type": "text", "content": json.dumps({"text": text})}
    if not message_id: payload["receive_id"] = receive_id
    requests.post(url, params=params, headers=headers, json=payload)

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    if body.get("challenge"): return {"challenge": body["challenge"]}
    event = body.get("event", {})
    if event.get("header", {}).get("event_type") == "im.message.receive_v1":
        msg = event.get("message", {})
        user_id = msg.get("sender", {}).get("user_id", {}).get("open_id", "")
        message_id = msg.get("message_id", "")
        content = msg.get("content", {})
        if msg.get("msg_type") == "text" and user_id:
            text = content.get("text", "").strip()
            reply = f"收到任务：「{text}」\n\n任务已收到，我会尽快处理！"
            send_msg(user_id, reply, message_id)
    return {"success": True}

@app.get("/")
def root(): return {"message": "Feishu AI Assistant"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
