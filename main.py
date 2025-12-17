from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from schema import SendEmailRequest

templates = Jinja2Templates(directory="templates")

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/send/email")
async def send(payload: SendEmailRequest):
    config = ConnectionConfig(**payload.config.model_dump())
    message = MessageSchema(**payload.message.model_dump())

    fm = FastMail(config)
    await fm.send_message(message)

    return {
        "message": "Email has been sent",
        "recipients": payload.message.recipients
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)