from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import speech_recognition as sr
import io

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Surah Al-Fatiha ka data aur exact seconds
fatiha_words = [
    {"word": "الحمد", "start_time": 0},
    {"word": "لله", "start_time": 2},
    {"word": "رب", "start_time": 3},
    {"word": "العالمين", "start_time": 4}
]

def clean_word(w):
    return "".join([c for c in w if c not in ["\u064b", "\u064c", "\u064d", "\u064e", "\u0650", "\u064f", "\u0651", "\u0652", " "]])

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    recognizer = sr.Recognizer()
    
    try:
        while True:
            # Browser se live audio bytes (chunks) darya ki tarah catch karna
            audio_bytes = await websocket.receive_bytes()
            
            if not audio_bytes:
                continue
                
            try:
                # Live chunk ko AI model par bhejna
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = recognizer.record(source)
                    user_text = recognizer.recognize_google(audio_data, language="ar-AE")
                
                user_words = user_text.split()
                galti_mili = False
                jump_to_seconds = 0
                
                # Live checking logic
                for i, target in enumerate(fatiha_words):
                    if i >= len(user_words) or clean_word(user_words[i]) != clean_word(target["word"]):
                        galti_mili = True
                        jump_to_seconds = target["start_time"]
                        break
                
                if galti_mili:
                    # Agar galti mili to browser ko signal bhejna ke Qari sahab ko is second se chalao
                    await websocket.send_json({
                        "status": "error",
                        "user_text": user_text,
                        "jump_to": jump_to_seconds
                    })
                else:
                    # Agar sab sahi hai to browser ko signal bhejna ke Qari sahab ko chup rakho
                    await websocket.send_json({
                        "status": "success",
                        "user_text": user_text
                    })
                    
            except sr.UnknownValueError:
                # Agar user khamosh hai ya awaz saaf nahi aayi
                await websocket.send_json({"status": "listening", "user_text": "Suna ja raha hai..."})
                
    except WebSocketDisconnect:
        print("Client disconnected")
