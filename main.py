import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from starlette.datastructures import Headers
from starlette.templating import Jinja2Templates
from .endpoints import Endpoints

from schema import (
    ConnectionConfigIn,
    MessageIn,
    SendEmailRequest,
    SendEmailResponse,
    SendTemplateEmailRequest,
    TemplateMessageIn,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FOLDER = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATE_FOLDER))

app = FastAPI(
    title="FastAPI-Mail Service",
    description="A standalone SMTP-sending microservice exposing the full "
    "capability of fastapi-mail over HTTP, for deployment on a server that "
    "supports outbound SMTP.",
    version="2.0.0",
)

# Allow this service to be called from a different origin (your main server).
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Connection config resolution
# --------------------------------------------------------------------------- #

def _env_config() -> ConnectionConfig:
    """Build a ConnectionConfig from environment variables (recommended:
    keeps SMTP credentials out of every request body)."""
    required = ["MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM", "MAIL_SERVER"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=(
                "No 'config' was supplied in the request and the server is "
                f"missing required environment variables: {', '.join(missing)}. "
                "Either set these in your .env, or pass a 'config' object "
                "in the request body."
            ),
        )
    return ConnectionConfig(
        MAIL_USERNAME=os.environ["MAIL_USERNAME"],
        MAIL_PASSWORD=os.environ["MAIL_PASSWORD"],
        MAIL_FROM=os.environ["MAIL_FROM"],
        MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
        MAIL_SERVER=os.environ["MAIL_SERVER"],
        MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
        MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True") == "True",
        MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False") == "True",
        USE_CREDENTIALS=os.getenv("USE_CREDENTIALS", "True") == "True",
        VALIDATE_CERTS=os.getenv("VALIDATE_CERTS", "True") == "True",
        TIMEOUT=int(os.getenv("MAIL_TIMEOUT", 60)),
        MAIL_DEBUG=int(os.getenv("MAIL_DEBUG", 0)),
        SUPPRESS_SEND=int(os.getenv("SUPPRESS_SEND", 0)),
        TEMPLATE_FOLDER=TEMPLATE_FOLDER,
    )


def resolve_config(config_in: Optional[ConnectionConfigIn]) -> ConnectionConfig:
    if config_in is None:
        return _env_config()
    return ConnectionConfig(
        **config_in.model_dump(),
        TEMPLATE_FOLDER=TEMPLATE_FOLDER,
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def build_attachments(message_in: MessageIn) -> List[dict]:
    """Turn base64 AttachmentIn entries into the (UploadFile, meta) shape
    fastapi-mail expects."""
    attachments = []
    for att in message_in.attachments:
        try:
            raw = base64.b64decode(att.content_base64)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Attachment '{att.filename}' is not valid base64: {exc}",
            )

        headers = None
        if att.content_type:
            headers = Headers({"content-type": att.content_type})

        upload = UploadFile(filename=att.filename, file=BytesIO(raw), headers=headers)

        meta = {}
        if att.content_type and "/" in att.content_type:
            mime_type, mime_subtype = att.content_type.split("/", 1)
            meta["mime_type"] = mime_type
            meta["mime_subtype"] = mime_subtype
        if att.headers:
            meta["headers"] = att.headers

        attachments.append({"file": upload, **meta} if meta else upload)

    return attachments


def to_message_schema(message_in: MessageIn) -> MessageSchema:
    return MessageSchema(
        recipients=message_in.recipients,
        subject=message_in.subject,
        body=message_in.body,
        alternative_body=message_in.alternative_body,
        subtype=MessageType(message_in.subtype.value),
        multipart_subtype=message_in.multipart_subtype.value,
        cc=message_in.cc,
        bcc=message_in.bcc,
        reply_to=message_in.reply_to,
        from_email=message_in.from_email,
        from_name=message_in.from_name,
        charset=message_in.charset,
        headers=message_in.headers,
        attachments=build_attachments(message_in),
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get(Endpoints.HEALTH)
async def health():
    return {"status": "ok"}


@app.post(Endpoints.SEND_EMAIL, response_model=SendEmailResponse)
async def send_email(payload: SendEmailRequest):
    """
    Send an email with a plain/html body and optional base64-encoded
    attachments. If 'config' is omitted, the server's MAIL_* environment
    variables are used.
    """
    config = resolve_config(payload.config)
    message = to_message_schema(payload.message)

    fm = FastMail(config)
    try:
        await fm.send_message(message)
    except ConnectionErrors as exc:
        raise HTTPException(status_code=502, detail=f"SMTP connection failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")

    return SendEmailResponse(
        message="Email has been sent",
        recipients=payload.message.recipients,
        cc=payload.message.cc,
        bcc=payload.message.bcc,
    )


@app.post(Endpoints.SEND_EMAIL_WITH_ATTACHMENTS, response_model=SendEmailResponse)
async def send_email_with_attachments(
    message: str = Form(
        ..., description="JSON-encoded body matching the MessageIn schema (minus attachments)"
    ),
    config: Optional[str] = Form(
        None, description="Optional JSON-encoded ConnectionConfigIn. Omit to use server env vars."
    ),
    files: List[UploadFile] = File(
        default=[], description="Real file attachments, sent as multipart/form-data"
    ),
):
    """
    Same as /send/email, but takes real file uploads for attachments
    instead of base64, which is cheaper for large files.
    """
    try:
        message_data = json.loads(message)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"'message' is not valid JSON: {exc}")
    message_data.pop("attachments", None)
    message_in = MessageIn(**message_data)

    config_in = None
    if config:
        try:
            config_in = ConnectionConfigIn(**json.loads(config))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"'config' is not valid JSON: {exc}")

    resolved_config = resolve_config(config_in)

    message_schema = MessageSchema(
        recipients=message_in.recipients,
        subject=message_in.subject,
        body=message_in.body,
        alternative_body=message_in.alternative_body,
        subtype=MessageType(message_in.subtype.value),
        multipart_subtype=message_in.multipart_subtype.value,
        cc=message_in.cc,
        bcc=message_in.bcc,
        reply_to=message_in.reply_to,
        from_email=message_in.from_email,
        from_name=message_in.from_name,
        charset=message_in.charset,
        headers=message_in.headers,
        attachments=list(files),
    )

    fm = FastMail(resolved_config)
    try:
        await fm.send_message(message_schema)
    except ConnectionErrors as exc:
        raise HTTPException(status_code=502, detail=f"SMTP connection failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")

    return SendEmailResponse(
        message="Email has been sent",
        recipients=message_in.recipients,
        cc=message_in.cc,
        bcc=message_in.bcc,
    )


@app.post(Endpoints.SEND_TEMPLATE_EMAIL, response_model=SendEmailResponse)
async def send_templated_email(payload: SendTemplateEmailRequest):
    """
    Render a Jinja2 template from the server's TEMPLATE_FOLDER
    ('templates/' next to main.py) and send it as the email body.
    template_name must match a file in that folder, e.g. 'welcome.html'.
    """
    config = resolve_config(payload.config)
    message_in: TemplateMessageIn = payload.message

    template_path = TEMPLATE_FOLDER / payload.template_name
    if not template_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Template '{payload.template_name}' not found in {TEMPLATE_FOLDER}",
        )

    message = MessageSchema(
        recipients=message_in.recipients,
        subject=message_in.subject,
        subtype=MessageType(message_in.subtype.value),
        multipart_subtype=message_in.multipart_subtype.value,
        cc=message_in.cc,
        bcc=message_in.bcc,
        reply_to=message_in.reply_to,
        from_email=message_in.from_email,
        from_name=message_in.from_name,
        charset=message_in.charset,
        headers=message_in.headers,
        template_body=message_in.template_body,
    )

    fm = FastMail(config)
    try:
        await fm.send_message(message, template_name=payload.template_name)
    except ConnectionErrors as exc:
        raise HTTPException(status_code=502, detail=f"SMTP connection failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")

    return SendEmailResponse(
        message="Templated email has been sent",
        recipients=message_in.recipients,
        cc=message_in.cc,
        bcc=message_in.bcc,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 5001)), reload=True)