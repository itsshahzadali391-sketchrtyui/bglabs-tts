import gradio as gr
import edge_tts
import asyncio
import os
import time
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

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

ELEVENLABS_VOICES = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Bella": "EXAVITQu4vr4xnSDxMaL",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Arnold": "VR6AewLTigWG4xSOukaG",
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Sam": "yoZ06aMxZJJ28mfd3POQ",
}

api = FastAPI(title="BG LABS TTS API v3")
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"
    rate: int = 0
    pitch: int = 0

class ElevenLabsRequest(BaseModel):
    text: str
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    model_id: str = "eleven_monolingual_v1"
    speed: float = 1.0

@api.get("/")
async def root():
    return {"status": "ok", "service": "BG LABS TTS v3", "providers": ["edge-tts", "elevenlabs"]}

@api.get("/api/health")
async def health():
    return {"status": "ok", "service": "BG LABS TTS v3", "elevenlabs_configured": bool(ELEVENLABS_API_KEY)}

@api.get("/api/voices")
async def get_voices():
    return {
        "edge_voices": [{"name": k, "id": v} for k, v in MICROSOFT_VOICES.items()],
        "elevenlabs_voices": [{"name": k, "id": v} for k, v in ELEVENLABS_VOICES.items()]
    }

@api.post("/api/tts")
async def generate_tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text is required")
    rate_str = f"+{req.rate}%" if req.rate >= 0 else f"{req.rate}%"
    pitch_str = f"+{req.pitch}Hz" if req.pitch >= 0 else f"{req.pitch}Hz"
    timestamp = int(time.time() * 1000)
    output_file = os.path.join(OUTPUT_DIR, f"edge_{timestamp}.mp3")
    try:
        communicate = edge_tts.Communicate(req.text, req.voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_file)
        return FileResponse(output_file, media_type="audio/mpeg", filename="speech.mp3")
    except Exception as e:
        raise HTTPException(500, str(e))

@api.post("/api/elevenlabs")
async def generate_elevenlabs(req: ElevenLabsRequest):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(500, "ElevenLabs API key not configured")
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text is required")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{req.voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": req.text,
        "model_id": req.model_id,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": req.speed}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        raise HTTPException(response.status_code, "ElevenLabs API error")
    timestamp = int(time.time() * 1000)
    output_file = os.path.join(OUTPUT_DIR, f"eleven_{timestamp}.mp3")
    with open(output_file, "wb") as f:
        f.write(response.content)
    return FileResponse(output_file, media_type="audio/mpeg", filename="speech.mp3")

def edge_generate(text, voice_name, rate, pitch):
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

def elevenlabs_generate(text, voice_name):
    if not ELEVENLABS_API_KEY:
        return None, "ElevenLabs API key not set! Set ELEVENLABS_API_KEY env var."
    if not text or not text.strip():
        return None, "Please enter text!"
    voice_id = ELEVENLABS_VOICES.get(voice_name, "21m00Tcm4TlvDq8ikWAM")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            return None, f"ElevenLabs error: {response.status_code}"
        timestamp = int(time.time() * 1000)
        output_file = os.path.join(OUTPUT_DIR, f"eleven_{timestamp}.mp3")
        with open(output_file, "wb") as f:
            f.write(response.content)
        return output_file, f"Done! ElevenLabs voice: {voice_name}"
    except Exception as e:
        return None, f"Error: {str(e)}"

with gr.Blocks(title="BG LABS TTS v3") as demo:
    gr.Markdown("# BG LABS TTS v3\n### Edge TTS (Free) + ElevenLabs (Premium)")
    
    with gr.Tabs():
        with gr.TabItem("Edge TTS (FREE Unlimited)"):
            with gr.Row():
                with gr.Column(scale=2):
                    edge_text = gr.Textbox(label="Text", lines=6, placeholder="Enter text here...")
                    edge_voice = gr.Dropdown(choices=list(MICROSOFT_VOICES.keys()), value="Guy (Male)", label="Voice")
                    edge_rate = gr.Slider(-50, 50, value=0, label="Speed")
                    edge_pitch = gr.Slider(-50, 50, value=0, label="Pitch")
                    edge_btn = gr.Button("Generate Edge TTS", variant="primary")
                with gr.Column(scale=1):
                    edge_audio = gr.Audio(label="Audio", type="filepath")
                    edge_status = gr.Textbox(label="Status")
            edge_btn.click(fn=edge_generate, inputs=[edge_text, edge_voice, edge_rate, edge_pitch], outputs=[edge_audio, edge_status])
        
        with gr.TabItem("ElevenLabs (Premium + Voice Cloning)"):
            with gr.Row():
                with gr.Column(scale=2):
                    eleven_text = gr.Textbox(label="Text", lines=6, placeholder="Enter text here...")
                    eleven_voice = gr.Dropdown(choices=list(ELEVENLABS_VOICES.keys()), value="Rachel", label="Voice")
                    eleven_btn = gr.Button("Generate ElevenLabs", variant="primary")
                with gr.Column(scale=1):
                    eleven_audio = gr.Audio(label="Audio", type="filepath")
                    eleven_status = gr.Textbox(label="Status")
            eleven_btn.click(fn=elevenlabs_generate, inputs=[eleven_text, eleven_voice], outputs=[eleven_audio, eleven_status])
    
    gr.Markdown("---\nAPI: `/api/tts` (Edge) | `/api/elevenlabs` (ElevenLabs) | `/api/voices` (List)")

app = demo

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
