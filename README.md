

# 📧 FastAPI Email Service (Serverless on Vercel)

A lightweight **serverless email-sending microservice** built using **FastAPI**, **FastAPI-Mail**, and deployed on **Vercel**.
It allows you to send fully customizable HTML email templates through any SMTP provider (Fastmail, Gmail, Outlook, Zoho, custom SMTP, etc).

This service is optimized to run on **Vercel’s Serverless Functions**, making it highly scalable and cost-efficient.

---

## 🚀 Features

* Send emails using SMTP (supports all providers)
* FastAPI backend converted to serverless using **Mangum**
* Serverless deployment on **Vercel**
* Supports HTML email templates
* Fully typed Pydantic models (Sender + Receiver structure)
* Quick and easy integration with any frontend or backend
* Secure credentials using Vercel Environment Variables

---

## 📁 Project Structure

```
project/
│
├── service.py            # Email sending logic
├── schema.py                 # Request models for sender/receiver
│
├── main.py 
└── requirements.txt              
```

---

## 🔧 Technologies Used

* **FastAPI**
* **FastAPI-Mail**
* **Pydantic**
* **Mangum** (ASGI → AWS Lambda adapter required by Vercel)
* **Starlette**
* **Python 3.10+**

---

## ✉️ API Endpoint

### **POST /send/email**

Sends an email using SMTP.

#### Request Body

```json
{
  "sender": {
    "username": "you@example.com",
    "mail_from": "you@example.com",
    "password": "your-smtp-password",
    "port": 587,
    "server": "smtp.fastmail.com",
    "ssl_tls": false,
    "starttls": true
  },
  "receiver": {
    "template": "<h1>Hello Umar!</h1><p>Your message has been received.</p>",
    "email": "recipient@example.com",
    "subject": "Hello from FastAPI on Vercel!"
  }
}
```

#### Response

```json
{
  "message": "Email sent to recipient@example.com"
}
```

---

## ⚙️ Environment Variables (Recommended)

Instead of sending credentials in the request body, store them in **Vercel Environment Variables**.

Example:

```
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=super_secret_password
SMTP_PORT=587
SMTP_SERVER=smtp.fastmail.com
SMTP_FROM=you@example.com
```

You can then change the backend logic to load them automatically.

Add them in your Vercel dashboard:

> **Vercel Dashboard → Project → Settings → Environment Variables**

---

## 🛠 Deployment on Vercel

### 1. Install Vercel CLI (optional)

```
npm i -g vercel
```

### 2. Deploy

```
vercel
```

That's it — Vercel will automatically detect your `vercel.json` and deploy the API as a serverless Python function.

---

## 📦 requirements.txt

```
fastapi
fastapi-mail
pydantic
mangum
starlette
email-validator
```

---

## ⚠️ Vercel Limitations

Because this service runs on **serverless functions**, note:

| Feature                      | Supported |
| ---------------------------- | --------- |
| SMTP sending                 | ✅ Yes     |
| HTML emails                  | ✅ Yes     |
| Long-running background jobs | ❌ No      |
| WebSockets                   | ❌ No      |
| Persistent filesystem        | ❌ No      |

But email sending works perfectly.

---

## 🧪 Testing Locally

### Option 1 — Uvicorn

```
uvicorn api.send_email:app --reload
```

Then test:

```
POST http://127.0.0.1:8000/send/email
```

### Option 2 — Vercel Dev

```
vercel dev
```

---

## 🤝 Contributing

Feel free to open issues or PRs to improve the email API, add templating, or extend functionality.

---

## 📝 License

MIT — free to use, modify, and deploy.

---
