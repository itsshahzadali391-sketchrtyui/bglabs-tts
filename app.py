import gradio as gr
import edge_tts
import asyncio
import os
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from pathlib import Path

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MICROSOFT_VOICES = {
    "Guy (Male)": "en-US-GuyNeural",
    "Aria (Female)": "en-US-AriaNeural",
    "Jenny (Female)": "en-US-JennyNeural",
    "Davis (Male)": "en-US-DavisNeural",
    "Sara (Female)": "en-US-SaraNeural",
    "Tony (Male)": "en-US-TonyNeural",
    "Andrew (Male)": "en-US-AndrewNeural",
    "Brian (Male)": "en-US-BrianNeural",
    "Christopher (Male)": "en-US-ChristopherNeural",
    "Eric (Male)": "en-US-EricNeural",
    "Michelle (Female)": "en-US-MichelleNeural",
    "Ana (Female)": "en-US-AnaNeural",
    "Brandon (Male)": "en-US-BrandonNeural",
    "Gabriel (Male)": "en-US-GabrielNeural",
    "Jessie (Male)": "en-US-JessieNeural",
    "Adam (Male)": "en-US-AdamNeural",
    "Amber (Female)": "en-US-AmberNeural",
    "Ashley (Female)": "en-US-AshleyNeural",
    "Chris (Male)": "en-US-ChrisNeural",
    "Cora (Female)": "en-US-CoraNeural",
    "Elizabeth (Female)": "en-US-ElizabethNeural",
    "Moon (Female)": "en-US-MoonNeural",
    "Nancy (Female)": "en-US-NancyNeural",
    "Phil (Male)": "en-US-PhilNeural",
    "Sam (Male)": "en-US-SamNeural",
}

# ===== FastAPI Backend =====
api = FastAPI(title="BG LABS TTS API")
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"
    rate: int = 0
    pitch: int = 0

@api.get("/api/health")
async def health():
    return {"status": "ok", "service": "BG LABS TTS", "version": "2.0", "voices": len(MICROSOFT_VOICES)}

@api.get("/api/voices")
async def get_voices():
    return {"voices": [{"name": k, "id": v} for k, v in MICROSOFT_VOICES.items()]}

@api.post("/api/tts")
async def generate_tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text is required")
    
    rate_str = f"+{req.rate}%" if req.rate >= 0 else f"{req.rate}%"
    pitch_str = f"+{req.pitch}Hz" if req.pitch >= 0 else f"{req.pitch}Hz"
    
    timestamp = int(time.time() * 1000)
    output_file = os.path.join(OUTPUT_DIR, f"tts_{timestamp}.mp3")
    
    try:
        communicate = edge_tts.Communicate(req.text, req.voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_file)
        return FileResponse(output_file, media_type="audio/mpeg", filename="speech.mp3")
    except Exception as e:
        raise HTTPException(500, str(e))

@api.post("/api/tts/url")
async def generate_tts_url(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text is required")
    
    rate_str = f"+{req.rate}%" if req.rate >= 0 else f"{req.rate}%"
    pitch_str = f"+{req.pitch}Hz" if req.pitch >= 0 else f"{req.pitch}Hz"
    
    timestamp = int(time.time() * 1000)
    output_file = os.path.join(OUTPUT_DIR, f"tts_{timestamp}.mp3")
    
    try:
        communicate = edge_tts.Communicate(req.text, req.voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_file)
        
        file_size = os.path.getsize(output_file)
        return {
            "status": "done",
            "file": output_file,
            "size_kb": round(file_size / 1024, 1),
            "voice": req.voice
        }
    except Exception as e:
        raise HTTPException(500, str(e))

# ===== Gradio Interface =====
def gradio_generate(text, voice_name, rate, pitch):
    if not text or not text.strip():
        return None, "Please enter text!"
    
    voice_id = MICROSOFT_VOICES.get(voice_name, "en-US-GuyNeural")
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    
    timestamp = int(time.time() * 1000)
    output_file = os.path.join(OUTPUT_DIR, f"gradio_{timestamp}.mp3")
    
    try:
        asyncio.run(edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str).save(output_file))
        return output_file, f"Done! Voice: {voice_name}"
    except Exception as e:
        return None, f"Error: {str(e)}"

with gr.Blocks(title="BG LABS TTS Studio") as gradio_app:
    gr.Markdown("# BG LABS TTS Studio\n### Free Unlimited Text-to-Speech")
    
    with gr.Row():
        with gr.Column(scale=2):
            text_input = gr.Textbox(label="Text", lines=8, placeholder="Enter text here...")
            voice_dropdown = gr.Dropdown(choices=list(MICROSOFT_VOICES.keys()), value="Guy (Male)", label="Voice")
            rate_slider = gr.Slider(-50, 50, value=0, label="Speed")
            pitch_slider = gr.Slider(-50, 50, value=0, label="Pitch")
            gen_btn = gr.Button("Generate", variant="primary")
        
        with gr.Column(scale=1):
            audio_out = gr.Audio(label="Audio", type="filepath")
            status_out = gr.Textbox(label="Status")
    
    gen_btn.click(fn=gradio_generate, inputs=[text_input, voice_dropdown, rate_slider, pitch_slider], outputs=[audio_out, status_out])

# ===== Run Both =====
app = gradio_app

if __name__ == "__main__":
    gradio_app.launch(server_name="0.0.0.0", server_port=7860)
