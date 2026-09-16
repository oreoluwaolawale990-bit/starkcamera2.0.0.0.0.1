import base64
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; Render env vars work without it

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stark-os")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini setup - key comes from a Render environment variable, never commit it.
# gemini-flash-latest is Google's alias for their current recommended Flash-tier
# model, so this keeps working as they retire/replace specific model versions.
# Set GEMINI_MODEL to a dated model name (e.g. "gemini-2.5-flash") instead if
# you want fixed, predictable behavior rather than auto-tracking updates.
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB decoded - keeps the free tier from choking on abuse
MAX_MESSAGE_CHARS = 2000


@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    return {"status": "ok", "gemini_configured": client is not None, "model": MODEL_NAME}


@app.post("/api/analyze")
async def analyze(request: Request):
    try:
        data = await request.json()
        image_b64 = data.get("image", "")
        prompt = data.get(
            "prompt",
            "You are JARVIS. Describe what you see in tactical, concise sentences.",
        )

        if not client:
            return JSONResponse({
                "error": "GEMINI_API_KEY not set on Render",
                "mock": "MOCK: I see a person in front of a camera, desk setup detected. "
                        "(Add GEMINI_API_KEY in Render's Environment tab for real AI.)",
            })

        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_b64)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            return JSONResponse({"error": "Image too large"}, status_code=413)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ],
        )

        return {"text": response.text}
    except Exception as e:
        logger.exception("analyze failed")
        return JSONResponse({"error": str(e), "text": f"Error: {e}"}, status_code=500)


@app.post("/api/jarvis")
async def jarvis(request: Request):
    try:
        data = await request.json()
        message = (data.get("message") or "")[:MAX_MESSAGE_CHARS]
        context = data.get("context", "")

        if not message:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        if not client:
            return {
                "text": f"MOCK JARVIS: You said '{message}'. Context: {context[:100]}. "
                        f"(Set GEMINI_API_KEY on Render for real AI.)"
            }

        full_prompt = (
            "You are JARVIS, Tony Stark's AI. Tactical, witty, concise.\n"
            f"Context from camera: {context}\nUser: {message}\nJARVIS:"
        )
        response = client.models.generate_content(model=MODEL_NAME, contents=full_prompt)
        return {"text": response.text}
    except Exception as e:
        logger.exception("jarvis failed")
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
