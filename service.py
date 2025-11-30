from fastapi_mail import FastMail, MessageType, MessageSchema, ConnectionConfig
from starlette.responses import JSONResponse
from pydantic import SecretStr
from schema import EmailMessage


async def send_mail(email_message: EmailMessage):
    config = ConnectionConfig(
        MAIL_USERNAME=email_message.sender.username,
        MAIL_FROM=email_message.sender.mail_from,
        MAIL_PASSWORD=SecretStr(email_message.sender.password),
        MAIL_PORT=email_message.sender.port,
        MAIL_SERVER=email_message.sender.server,
        MAIL_SSL_TLS=email_message.sender.ssl_tls,
        MAIL_STARTTLS=email_message.sender.starttls,
    )

    message = MessageSchema(
        subject=email_message.receiver.subject,
        recipients=[email_message.receiver.email],
        subtype=MessageType.html,
        body=email_message.receiver.template
    )

    fm = FastMail(config)
    await fm.send_message(message)

    return JSONResponse(
        status_code=200,
        content={"message": f"Email has been sent to {email_message.receiver.email}"}
    )
