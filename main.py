import os
import json
import base64
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env (local) or Render's envVars
load_dotenv()

app = FastAPI()

# CORS setup (for local or frontend call)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_DIR = "uploads"
DATA_FILE = "user_data/data.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("user_data", exist_ok=True)

@app.get("/")
def root():
    return {"message": "Hello, Calories API!"}

@app.post("/upload")
async def upload_image(
    user_id: str = Form(...),
    meal: str = Form(...),
    image_file: UploadFile = File(...)
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(image_file.filename)[-1]
    filename = f"{user_id}_{timestamp}_{os.urandom(4).hex()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await image_file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Convert image to base64
    b64 = base64.b64encode(content).decode("utf-8")

    # Send to OpenAI Vision
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What food is in this image? Estimate total calories."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }
        ],
        max_tokens=500
    )

    gpt_text = response.choices[0].message.content

    # Extract calories (basic parse)
    total = 0
    items = []
    for line in gpt_text.splitlines():
        if "calories" in line.lower():
            parts = line.split(":")
            if len(parts) >= 2:
                name = parts[0].strip()
                try:
                    cal = int(''.join(filter(str.isdigit, parts[1])))
                    items.append({"name": name, "calories": cal})
                    total += cal
                except:
                    continue

    data = {
        "date": str(datetime.today().date()),
        "meal": meal,
        "total_calories": total,
        "ingredients_estimated": items,
        "image_file": filename,
        "timestamp": datetime.now().isoformat()
    }

    # Save history
    try:
        with open(DATA_FILE, "r") as f:
            history = json.load(f)
    except:
        history = {}

    history.setdefault(user_id, []).append(data)

    with open(DATA_FILE, "w") as f:
        json.dump(history, f, indent=2)

    return JSONResponse(content={"status": "ok", "data": data})

@app.get("/history")
async def get_history(user_id: str):
    try:
        with open(DATA_FILE, "r") as f:
            history = json.load(f)
        return {"history": history.get(user_id, [])}
    except:
        return {"history": []}
