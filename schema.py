from pydantic import BaseModel, EmailStr


class Sender(BaseModel):
    username: EmailStr
    mail_from: EmailStr
    password: str
    port: int
    server: str
    ssl_tls: bool
    starttls: bool


class Receiver(BaseModel):
    template: str
    email: EmailStr
    subject: str


class EmailMessage(BaseModel):
    sender: Sender
    receiver: Receiver
