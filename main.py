from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from datetime import datetime
import os, uuid, json

app = FastAPI()

UPLOAD_DIR = "uploads"
DATA_DIR = "user_data"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Dummy call GPT (ไว้รอคุณส่ง API Key ค่อยต่อ GPT จริง)
def mock_calorie_estimate():
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "meal": "lunch",
        "total_calories": 635,
        "ingredients_estimated": [
            { "name": "steamed chicken", "calories": 300 },
            { "name": "rice", "calories": 280 },
            { "name": "sauce", "calories": 55 }
        ]
    }

@app.post("/upload")
async def upload_image(user_id: str = Form(...), file: UploadFile = File(...)):
    # บันทึกรูป
    now = datetime.now()
    filename = f"{user_id}_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # เรียก ChatGPT API (ตอนนี้ใช้ mock)
    calorie_result = mock_calorie_estimate()
    calorie_result["image_file"] = filename
    calorie_result["timestamp"] = now.isoformat()

    # เก็บไว้ใน user-specific JSON
    user_file = os.path.join(DATA_DIR, f"{user_id}.json")
    history = []
    if os.path.exists(user_file):
        with open(user_file, "r") as f:
            history = json.load(f)
    history.append(calorie_result)
    with open(user_file, "w") as f:
        json.dump(history, f, indent=2)

    return {"status": "ok", "data": calorie_result}


@app.get("/history")
def get_history(user_id: str):
    user_file = os.path.join(DATA_DIR, f"{user_id}.json")
    if not os.path.exists(user_file):
        return JSONResponse(content={"history": []}, status_code=200)
    
    with open(user_file, "r") as f:
        history = json.load(f)
    
    return {"history": history}
