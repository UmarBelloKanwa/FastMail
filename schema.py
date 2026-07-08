"""
Pydantic request/response models for the FastAPI-Mail HTTP wrapper.

These mirror every field that ``fastapi_mail.ConnectionConfig`` and
``fastapi_mail.MessageSchema`` accept, so nothing from the underlying
library is left unreachable through the API.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# --------------------------------------------------------------------------- #
# Enums (kept as plain str enums so they serialize cleanly in OpenAPI/JSON)
# --------------------------------------------------------------------------- #

class MessageTypeEnum(str, Enum):
    plain = "plain"
    html = "html"


class MultipartSubtypeEnum(str, Enum):
    mixed = "mixed"
    digest = "digest"
    alternative = "alternative"
    related = "related"


# --------------------------------------------------------------------------- #
# Connection config (== fastapi_mail.ConnectionConfig)
# --------------------------------------------------------------------------- #

class ConnectionConfigIn(BaseModel):
    """
    SMTP connection settings. Every field fastapi-mail's ConnectionConfig
    supports is exposed here. If omitted entirely from a request, the
    server falls back to the MAIL_* environment variables (see main.py),
    which is the recommended way to run this service so credentials never
    have to travel in the request body.
    """

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int = 587
    MAIL_SERVER: str
    MAIL_FROM_NAME: Optional[str] = None
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    TIMEOUT: int = 60
    MAIL_DEBUG: int = 0
    SUPPRESS_SEND: int = 0  # set to 1 to dry-run (fastapi-mail will not actually send)


# --------------------------------------------------------------------------- #
# Attachments
# --------------------------------------------------------------------------- #

class AttachmentIn(BaseModel):
    """
    A single attachment sent inline as base64. Use this on the plain
    JSON /send/email endpoint. If you'd rather upload real files, use
    /send/email/with-attachments (multipart/form-data) instead.
    """

    filename: str
    content_base64: str = Field(..., description="Base64-encoded file bytes")
    content_type: Optional[str] = Field(
        None, description='MIME type, e.g. "application/pdf" or "image/png"'
    )
    headers: Optional[Dict[str, str]] = Field(
        None, description="Extra MIME headers to attach to this part, e.g. Content-ID"
    )


# --------------------------------------------------------------------------- #
# Message (== fastapi_mail.MessageSchema)
# --------------------------------------------------------------------------- #

class MessageIn(BaseModel):
    recipients: List[EmailStr]
    subject: str = ""
    body: Optional[str] = None
    alternative_body: Optional[str] = Field(
        None,
        description="Only used when multipart_subtype='alternative'. "
        "Provide the opposite subtype's content here (e.g. plain-text "
        "fallback for an html body).",
    )
    subtype: MessageTypeEnum = MessageTypeEnum.plain
    multipart_subtype: MultipartSubtypeEnum = MultipartSubtypeEnum.mixed
    cc: List[EmailStr] = []
    bcc: List[EmailStr] = []
    reply_to: List[EmailStr] = []
    from_email: Optional[EmailStr] = Field(
        None, description="Overrides MAIL_FROM for this message only"
    )
    from_name: Optional[str] = Field(
        None, description="Overrides MAIL_FROM_NAME for this message only"
    )
    charset: str = "utf-8"
    headers: Optional[Dict[str, str]] = Field(
        None, description="Extra custom SMTP headers, e.g. {'X-Custom': 'value'}"
    )
    attachments: List[AttachmentIn] = []


# --------------------------------------------------------------------------- #
# Templated message (Jinja2, served from the TEMPLATE_FOLDER on this server)
# --------------------------------------------------------------------------- #

class TemplateMessageIn(BaseModel):
    recipients: List[EmailStr]
    subject: str = ""
    subtype: MessageTypeEnum = MessageTypeEnum.html
    multipart_subtype: MultipartSubtypeEnum = MultipartSubtypeEnum.mixed
    cc: List[EmailStr] = []
    bcc: List[EmailStr] = []
    reply_to: List[EmailStr] = []
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = None
    charset: str = "utf-8"
    headers: Optional[Dict[str, str]] = None
    template_body: Dict = Field(
        default_factory=dict, description="Variables passed into the Jinja2 template"
    )


# --------------------------------------------------------------------------- #
# Top level request bodies
# --------------------------------------------------------------------------- #

class SendEmailRequest(BaseModel):
    config: Optional[ConnectionConfigIn] = None
    message: MessageIn


class SendTemplateEmailRequest(BaseModel):
    config: Optional[ConnectionConfigIn] = None
    message: TemplateMessageIn
    template_name: str = Field(
        ..., description="Filename of a Jinja2 template inside TEMPLATE_FOLDER, e.g. 'welcome.html'"
    )


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #

class SendEmailResponse(BaseModel):
    message: str
    recipients: List[EmailStr]
    cc: List[EmailStr] = []
    bcc: List[EmailStr] = []


class ErrorResponse(BaseModel):
    error: str
    detail: str