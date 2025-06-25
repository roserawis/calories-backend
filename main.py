@app.post("/upload")
async def upload_image(
    user_id: str = Form(...),
    meal: str = Form(...),
    image_file: UploadFile = File(...)
):
    # สร้างชื่อไฟล์
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(image_file.filename)[-1]
    filename = f"{user_id}_{timestamp}_{os.urandom(4).hex()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # บันทึกรูป
    content = await image_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # แปลงรูปเป็น base64
    image_b64 = base64.b64encode(content).decode("utf-8")

    # ส่งไปยัง GPT
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What food is in this image? Estimate total calories."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }
        ],
        max_tokens=500,
    )

    text_output = response.choices[0].message.content

    # แปลงข้อความจาก GPT เป็นข้อมูล JSON
    total_calories = 0
    ingredients = []

    for line in text_output.split("\n"):
        if "calories" in line.lower():
            parts = line.split(":")
            if len(parts) >= 2:
                name = parts[0].strip()
                try:
                    calories = int(''.join(filter(str.isdigit, parts[1])))
                    ingredients.append({"name": name, "calories": calories})
                    total_calories += calories
                except:
                    continue

    data = {
        "date": str(datetime.today().date()),
        "meal": meal,
        "total_calories": total_calories,
        "ingredients_estimated": ingredients,
        "image_file": filename,
        "timestamp": datetime.now().isoformat()
    }

    # เขียนข้อมูลลงไฟล์
    try:
        with open(DATA_FILE, "r") as f:
            history = json.load(f)
    except:
        history = {}

    history.setdefault(user_id, []).append(data)

    with open(DATA_FILE, "w") as f:
        json.dump(history, f, indent=2)

    return JSONResponse(content={"status": "ok", "data": data})
