import os
import json
import base64
import re
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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
os.makedirs("user_data", exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"message": "Hello, Calories API!"}

@app.post("/upload")
async def upload_image(
    user_id: str = Form(...),
    meal: str = Form(...),
    image_file: UploadFile = File(...)
):
    # Save image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(image_file.filename)[-1]
    filename = f"{user_id}_{timestamp}_{os.urandom(4).hex()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    content = await image_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Convert image to base64
    image_b64 = base64.b64encode(content).decode("utf-8")

    # Query OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What food is in this image? List each ingredient and estimate its calories. Do not include a total estimate line."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }
        ],
        max_tokens=500,
    )

    text_output = response.choices[0].message.content

    total_calories = 0
    ingredients = []

    for line in text_output.split("\n"):
        if not line.strip():
            continue

        # Skip vague summary lines
        if "estimated calories" in line.lower() and not any(char.isdigit() for char in line):
            continue

        match = re.match(r"^(.*?)[\:\-–]\s*(\d+)\s*(?:-|–)?\s*(\d+)?\s*calories?", line, re.IGNORECASE)
        if match:
            name = match.group(1).strip(" -•*:.")
            low = int(match.group(2))
            high = int(match.group(3)) if match.group(3) else low
            avg_calories = (low + high) // 2

            # Filter out generic or unclear labels
            if "estimated calories" not in name.lower():
                ingredients.append({"name": name, "calories": avg_calories})
                total_calories += avg_calories

    data = {
        "date": str(datetime.today().date()),
        "meal": meal,
        "total_calories": total_calories,
        "ingredients_estimated": ingredients,
        "image_file": filename,
        "timestamp": datetime.now().isoformat()
    }

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
