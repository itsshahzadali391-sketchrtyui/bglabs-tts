from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import edge_tts
import asyncio
import httpx
import os
import time
from pathlib import Path

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="BG LABS TTS Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Edge TTS Voices
EDGE_VOICES = {
    "guy": {"name": "Guy (Male)", "id": "en-US-GuyNeural"},
    "aria": {"name": "Aria (Female)", "id": "en-US-AriaNeural"},
    "jenny": {"name": "Jenny (Female)", "id": "en-US-JennyNeural"},
    "davis": {"name": "Davis (Male)", "id": "en-US-DavisNeural"},
    "sara": {"name": "Sara (Female)", "id": "en-US-SaraNeural"},
    "tony": {"name": "Tony (Male)", "id": "en-US-TonyNeural"},
    "andrew": {"name": "Andrew (Male)", "id": "en-US-AndrewNeural"},
    "brian": {"name": "Brian (Male)", "id": "en-US-BrianNeural"},
    "adam": {"name": "Adam (Male)", "id": "en-US-AdamNeural"},
    "amber": {"name": "Amber (Female)", "id": "en-US-AmberNeural"},
    "ashley": {"name": "Ashley (Female)", "id": "en-US-AshleyNeural"},
    "chris": {"name": "Chris (Male)", "id": "en-US-ChrisNeural"},
    "cora": {"name": "Cora (Female)", "id": "en-US-CoraNeural"},
    "elizabeth": {"name": "Elizabeth (Female)", "id": "en-US-ElizabethNeural"},
    "moon": {"name": "Moon (Female)", "id": "en-US-MoonNeural"},
    "nancy": {"name": "Nancy (Female)", "id": "en-US-NancyNeural"},
    "phil": {"name": "Phil (Male)", "id": "en-US-PhilNeural"},
    "sam": {"name": "Sam (Male)", "id": "en-US-SamNeural"},
    "michelle": {"name": "Michelle (Female)", "id": "en-US-MichelleNeural"},
    "eric": {"name": "Eric (Male)", "id": "en-US-EricNeural"},
}

# F5-TTS Hugging Face Space (free inference)
F5_TTS_SPACE = "mrfakename/F5-TTS"

class TTSRequest(BaseModel):
    text: str
    voice: str = "guy"
    engine: str = "auto"  # auto, edge, f5
    rate: int = 0
    pitch: int = 0

class VoiceCloneRequest(BaseModel):
    text: str
    reference_audio: str = ""  # URL or base64
    voice: str = "guy"

# ===== F5-TTS Engine =====
async def generate_f5_tts(text: str) -> str:
    """Generate TTS using F5-TTS via Hugging Face Space"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Try Hugging Face Inference API
            api_url = f"https://{F5_TTS_SPACE}.hf.space/api/predict"
            
            payload = {
                "data": [text, "", "en-US", 0.8, 1.0],
                "fn_index": 0
            }
            
            resp = await client.post(api_url, json=payload, timeout=60.0)
            
            if resp.status_code == 200:
                result = resp.json()
                if result.get("data") and len(result["data"]) > 0:
                    audio_url = result["data"][0].get("url") or result["data"][0].get("path")
                    if audio_url:
                        # Download the audio
                        audio_resp = await client.get(audio_url, timeout=30.0)
                        if audio_resp.status_code == 200:
                            ts = int(time.time() * 1000)
                            out_path = OUTPUT_DIR / f"f5_{ts}.wav"
                            out_path.write_bytes(audio_resp.content)
                            return str(out_path)
            
            return None
    except Exception as e:
        print(f"F5-TTS error: {e}")
        return None

# ===== Edge TTS Engine =====
async def generate_edge_tts(text: str, voice_id: str, rate: int = 0, pitch: int = 0) -> str:
    """Generate TTS using Edge TTS"""
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    
    ts = int(time.time() * 1000)
    out_path = OUTPUT_DIR / f"edge_{ts}.mp3"
    
    try:
        comm = edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str)
        await comm.save(str(out_path))
        return str(out_path)
    except Exception as e:
        print(f"Edge TTS error: {e}")
        return None

# ===== Smart Router =====
async def generate_tts_smart(text: str, voice: str, engine: str, rate: int, pitch: int) -> dict:
    """Smart router: tries F5 first, falls back to Edge"""
    
    # Get Edge voice ID
    edge_voice = EDGE_VOICES.get(voice, EDGE_VOICES["guy"])
    voice_id = edge_voice["id"]
    voice_name = edge_voice["name"]
    
    # If user specifically wants edge
    if engine == "edge":
        file_path = await generate_edge_tts(text, voice_id, rate, pitch)
        if file_path:
            return {"file": file_path, "engine": "edge", "voice": voice_name}
    
    # If user specifically wants F5
    if engine == "f5":
        file_path = await generate_f5_tts(text)
        if file_path:
            return {"file": file_path, "engine": "f5", "voice": "F5-TTS"}
        else:
            raise HTTPException(503, "F5-TTS unavailable, try engine='edge'")
    
    # Auto mode: try F5 first, fallback to Edge
    if engine == "auto":
        # Try F5 first (better quality)
        file_path = await generate_f5_tts(text)
        if file_path:
            return {"file": file_path, "engine": "f5", "voice": "F5-TTS"}
        
        # Fallback to Edge (always works)
        file_path = await generate_edge_tts(text, voice_id, rate, pitch)
        if file_path:
            return {"file": file_path, "engine": "edge", "voice": voice_name}
    
    raise HTTPException(500, "All TTS engines failed")

# ===== API Endpoints =====
@app.get("/")
async def root():
    return HTMLResponse(HTML_PAGE)

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "BG LABS TTS Server",
        "version": "3.0",
        "engines": ["Edge TTS", "F5-TTS"],
        "voices_count": len(EDGE_VOICES)
    }

@app.get("/api/voices")
async def get_voices():
    return {
        "voices": [
            {"id": k, "name": v["name"], "engine": "edge"}
            for k, v in EDGE_VOICES.items()
        ] + [
            {"id": "f5-default", "name": "F5-TTS (High Quality)", "engine": "f5"}
        ]
    }

@app.post("/api/tts")
async def generate_tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text required")
    
    result = await generate_tts_smart(req.text, req.voice, req.engine, req.rate, req.pitch)
    return FileResponse(result["file"], media_type="audio/mpeg", filename="speech.mp3")

@app.post("/api/tts/url")
async def generate_tts_url(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text required")
    
    result = await generate_tts_smart(req.text, req.voice, req.engine, req.rate, req.pitch)
    size = os.path.getsize(result["file"])
    
    return {
        "status": "done",
        "engine": result["engine"],
        "voice": result["voice"],
        "size_kb": round(size / 1024, 1),
        "text_length": len(req.text)
    }

@app.post("/api/voice-clone")
async def voice_clone(req: VoiceCloneRequest):
    """Voice clone using F5-TTS with reference audio"""
    if not req.text:
        raise HTTPException(400, "Text required")
    
    # For now, fallback to edge TTS
    edge_voice = EDGE_VOICES.get(req.voice, EDGE_VOICES["guy"])
    file_path = await generate_edge_tts(req.text, edge_voice["id"])
    
    if file_path:
        return {
            "status": "done",
            "engine": "edge",
            "voice": edge_voice["name"],
            "note": "Voice clone requires F5-TTS. Using Edge TTS as fallback."
        }
    
    raise HTTPException(500, "TTS failed")

@app.get("/api/tts/get")
async def get_tts(text: str, voice: str = "guy", engine: str = "auto"):
    if not text:
        raise HTTPException(400, "Text required")
    
    edge_voice = EDGE_VOICES.get(voice, EDGE_VOICES["guy"])
    result = await generate_tts_smart(text, voice, engine, 0, 0)
    return FileResponse(result["file"], media_type="audio/mpeg", filename="speech.mp3")

# ===== HTML Frontend =====
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BG LABS TTS Server v3</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; }
        .bg { position: fixed; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle at 30% 40%, rgba(139,92,246,0.15) 0%, transparent 50%), radial-gradient(circle at 70% 60%, rgba(236,72,153,0.1) 0%, transparent 50%); pointer-events: none; }
        .c { max-width: 800px; margin: 0 auto; padding: 30px 20px; position: relative; z-index: 1; }
        .h { text-align: center; margin-bottom: 30px; }
        .h h1 { font-size: 2.5rem; background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .h p { color: #94a3b8; margin-top: 8px; }
        .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 30px; margin-bottom: 24px; }
        .fg { margin-bottom: 18px; }
        .fg label { display: block; margin-bottom: 6px; font-size: 0.85rem; color: #94a3b8; }
        textarea, select { width: 100%; padding: 12px 16px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: #fff; font-size: 0.95rem; resize: vertical; }
        textarea:focus, select:focus { outline: none; border-color: #8b5cf6; }
        textarea { min-height: 120px; }
        select option { background: #1a1a2e; }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .btn { padding: 14px 32px; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; width: 100%; transition: all 0.3s; }
        .btn-p { background: linear-gradient(135deg, #8b5cf6, #a855f7); color: #fff; }
        .btn-p:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139,92,246,0.3); }
        .btn-p:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; margin: 5px; }
        .b-green { background: rgba(34,197,94,0.2); color: #22c55e; }
        .b-blue { background: rgba(59,130,246,0.2); color: #3b82f6; }
        .b-purple { background: rgba(139,92,246,0.2); color: #8b5cf6; }
        audio { width: 100%; margin-top: 10px; }
        .status { text-align: center; color: #94a3b8; margin: 10px 0; }
        .engines { display: flex; gap: 10px; justify-content: center; margin-top: 10px; flex-wrap: wrap; }
    </style>
</head>
<body>
    <div class="bg"></div>
    <div class="c">
        <div class="h">
            <h1>BG LABS TTS Server v3</h1>
            <p>Edge TTS + F5-TTS Combined | Free & Unlimited</p>
            <div class="engines">
                <span class="badge b-green">Edge TTS (Fast)</span>
                <span class="badge b-blue">F5-TTS (Quality)</span>
                <span class="badge b-purple">Auto Router</span>
            </div>
        </div>
        
        <div class="card">
            <div class="fg">
                <label>Text to speak</label>
                <textarea id="text" placeholder="Enter text here... (unlimited length)"></textarea>
            </div>
            <div class="row">
                <div class="fg">
                    <label>Voice</label>
                    <select id="voice">
                        <option value="guy">Guy (Male)</option>
                        <option value="aria">Aria (Female)</option>
                        <option value="jenny">Jenny (Female)</option>
                        <option value="davis">Davis (Male)</option>
                        <option value="sara">Sara (Female)</option>
                        <option value="tony">Tony (Male)</option>
                        <option value="andrew">Andrew (Male)</option>
                        <option value="brian">Brian (Male)</option>
                        <option value="adam">Adam (Male)</option>
                        <option value="amber">Amber (Female)</option>
                        <option value="moon">Moon (Female)</option>
                        <option value="nancy">Nancy (Female)</option>
                    </select>
                </div>
                <div class="fg">
                    <label>Engine</label>
                    <select id="engine">
                        <option value="auto">Auto (Best Quality)</option>
                        <option value="edge">Edge TTS (Fast)</option>
                        <option value="f5">F5-TTS (Best Quality)</option>
                    </select>
                </div>
            </div>
            <button class="btn btn-p" id="genBtn" onclick="generate()">Generate Voice</button>
        </div>
        
        <div class="card" id="result" style="display:none">
            <audio id="audio" controls></audio>
            <div class="status" id="status"></div>
        </div>
        
        <div class="card">
            <h3 style="margin-bottom:15px">API Docs</h3>
            <p style="color:#94a3b8;font-size:0.9rem"><code>POST /api/tts/url</code></p>
            <pre style="background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;margin-top:10px;color:#8b5cf6;font-size:0.85rem">{"text":"Hello","voice":"guy","engine":"auto"}</pre>
            <p style="color:#94a3b8;font-size:0.8rem;margin-top:10px">Engine: auto | edge | f5</p>
        </div>
    </div>
    
    <script>
        async function generate() {
            const text = document.getElementById('text').value;
            if (!text.trim()) { alert('Enter text!'); return; }
            
            const btn = document.getElementById('genBtn');
            btn.disabled = true;
            btn.textContent = 'Generating...';
            
            try {
                const resp = await fetch('/api/tts/url', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: text,
                        voice: document.getElementById('voice').value,
                        engine: document.getElementById('engine').value
                    })
                });
                
                const data = await resp.json();
                if (data.status === 'done') {
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('audio').src = '/api/tts?text=' + encodeURIComponent(text) + '&voice=' + document.getElementById('voice').value + '&engine=' + document.getElementById('engine').value;
                    document.getElementById('status').innerHTML = 'Engine: <b>' + data.engine.toUpperCase() + '</b> | Voice: ' + data.voice + ' | Size: ' + data.size_kb + ' KB';
                } else {
                    alert('Error');
                }
            } catch(e) {
                alert('Error: ' + e.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Generate Voice';
            }
        }
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
