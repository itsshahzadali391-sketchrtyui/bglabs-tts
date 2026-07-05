from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import edge_tts
import asyncio
import os
import time
from pathlib import Path

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="BG LABS TTS API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

VOICES = {
    "Guy (Male)": "en-US-GuyNeural",
    "Aria (Female)": "en-US-AriaNeural",
    "Jenny (Female)": "en-US-JennyNeural",
    "Davis (Male)": "en-US-DavisNeural",
    "Sara (Female)": "en-US-SaraNeural",
    "Tony (Male)": "en-US-TonyNeural",
    "Andrew (Male)": "en-US-AndrewNeural",
    "Brian (Male)": "en-US-BrianNeural",
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
    "Michelle (Female)": "en-US-MichelleNeural",
    "Eric (Male)": "en-US-EricNeural",
}

FRONTEND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BG LABS TTS Studio</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; }
        .bg-glow { position: fixed; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle at 30% 40%, rgba(139,92,246,0.15) 0%, transparent 50%), radial-gradient(circle at 70% 60%, rgba(236,72,153,0.1) 0%, transparent 50%); pointer-events: none; }
        .container { max-width: 800px; margin: 0 auto; padding: 30px 20px; position: relative; z-index: 1; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { color: #94a3b8; margin-top: 8px; }
        .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 30px; margin-bottom: 24px; }
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; margin-bottom: 6px; font-size: 0.85rem; color: #94a3b8; }
        textarea, select, input { width: 100%; padding: 12px 16px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: #fff; font-size: 0.95rem; resize: vertical; }
        textarea:focus, select:focus { outline: none; border-color: #8b5cf6; }
        textarea { min-height: 120px; }
        select option { background: #1a1a2e; }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .btn { padding: 14px 32px; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; width: 100%; transition: all 0.3s; }
        .btn-primary { background: linear-gradient(135deg, #8b5cf6, #a855f7); color: #fff; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139,92,246,0.3); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .result { text-align: center; margin-top: 20px; }
        audio { width: 100%; margin-top: 10px; }
        .status { text-align: center; color: #94a3b8; margin: 10px 0; }
        .badge { display: inline-block; padding: 4px 12px; background: rgba(34,197,94,0.2); color: #22c55e; border-radius: 20px; font-size: 0.8rem; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="bg-glow"></div>
    <div class="container">
        <div class="header">
            <h1>BG LABS TTS Studio</h1>
            <p>Free Unlimited Text-to-Speech | 20+ Microsoft Neural Voices</p>
            <span class="badge">UNLIMITED & FREE</span>
        </div>
        
        <div class="card">
            <div class="form-group">
                <label>Text to speak (unlimited length - up to 30 min audio)</label>
                <textarea id="text" placeholder="Enter your text here... You can paste long articles, scripts, or any text. No character limits!"></textarea>
            </div>
            
            <div class="row">
                <div class="form-group">
                    <label>Voice</label>
                    <select id="voice">
                        <option value="en-US-GuyNeural">Guy (Male)</option>
                        <option value="en-US-AriaNeural">Aria (Female)</option>
                        <option value="en-US-JennyNeural">Jenny (Female)</option>
                        <option value="en-US-DavisNeural">Davis (Male)</option>
                        <option value="en-US-SaraNeural">Sara (Female)</option>
                        <option value="en-US-TonyNeural">Tony (Male)</option>
                        <option value="en-US-AndrewNeural">Andrew (Male)</option>
                        <option value="en-US-BrianNeural">Brian (Male)</option>
                        <option value="en-US-AdamNeural">Adam (Male)</option>
                        <option value="en-US-AmberNeural">Amber (Female)</option>
                        <option value="en-US-AshleyNeural">Ashley (Female)</option>
                        <option value="en-US-ChrisNeural">Chris (Male)</option>
                        <option value="en-US-CoraNeural">Cora (Female)</option>
                        <option value="en-US-ElizabethNeural">Elizabeth (Female)</option>
                        <option value="en-US-MoonNeural">Moon (Female)</option>
                        <option value="en-US-NancyNeural">Nancy (Female)</option>
                        <option value="en-US-PhilNeural">Phil (Male)</option>
                        <option value="en-US-SamNeural">Sam (Male)</option>
                        <option value="en-US-MichelleNeural">Michelle (Female)</option>
                        <option value="en-US-EricNeural">Eric (Male)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Speed</label>
                    <input type="range" id="rate" min="-50" max="50" value="0" style="padding:8px">
                </div>
            </div>
            
            <button class="btn btn-primary" id="genBtn" onclick="generate()">Generate Voice</button>
        </div>
        
        <div class="card" id="resultCard" style="display:none">
            <div class="result">
                <audio id="audio" controls></audio>
                <br><br>
                <a id="downloadLink" class="btn btn-primary" style="text-decoration:none;display:inline-block;width:auto;padding:10px 24px" download>Download MP3</a>
            </div>
        </div>
        
        <div class="card" style="text-align:center">
            <p style="color:#94a3b8;font-size:0.9rem">API Endpoint: <code>/api/tts</code></p>
            <p style="color:#94a3b8;font-size:0.8rem;margin-top:8px">POST { "text": "your text", "voice": "en-US-GuyNeural" }</p>
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
                        rate: parseInt(document.getElementById('rate').value),
                        pitch: 0
                    })
                });
                
                const data = await resp.json();
                if (data.status === 'done') {
                    document.getElementById('resultCard').style.display = 'block';
                    document.getElementById('audio').src = '/api/tts?text=' + encodeURIComponent(text) + '&voice=' + document.getElementById('voice').value;
                    document.getElementById('downloadLink').href = document.getElementById('audio').src;
                } else {
                    alert('Error: ' + (data.detail || 'Unknown'));
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

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"
    rate: int = 0
    pitch: int = 0

@app.get("/")
async def root():
    return HTMLResponse(FRONTEND_HTML)

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "BG LABS TTS", "version": "2.0", "voices_count": len(VOICES)}

@app.get("/api/voices")
async def get_voices():
    return {"voices": [{"name": k, "id": v} for k, v in VOICES.items()]}

@app.post("/api/tts")
async def generate_tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text required")
    
    rate_str = f"+{req.rate}%" if req.rate >= 0 else f"{req.rate}%"
    pitch_str = f"+{req.pitch}Hz" if req.pitch >= 0 else f"{req.pitch}Hz"
    ts = int(time.time() * 1000)
    out = OUTPUT_DIR / f"tts_{ts}.mp3"
    
    try:
        comm = edge_tts.Communicate(req.text, req.voice, rate=rate_str, pitch=pitch_str)
        await comm.save(str(out))
        return FileResponse(str(out), media_type="audio/mpeg", filename="speech.mp3")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/tts/url")
async def generate_tts_url(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text required")
    
    rate_str = f"+{req.rate}%" if req.rate >= 0 else f"{req.rate}%"
    pitch_str = f"+{req.pitch}Hz" if req.pitch >= 0 else f"{req.pitch}Hz"
    ts = int(time.time() * 1000)
    out = OUTPUT_DIR / f"tts_{ts}.mp3"
    
    try:
        comm = edge_tts.Communicate(req.text, req.voice, rate=rate_str, pitch=pitch_str)
        await comm.save(str(out))
        size = os.path.getsize(str(out))
        return {"status": "done", "size_kb": round(size/1024, 1), "voice": req.voice}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/tts/get")
async def get_tts(text: str, voice: str = "en-US-GuyNeural"):
    ts = int(time.time() * 1000)
    out = OUTPUT_DIR / f"tts_{ts}.mp3"
    try:
        comm = edge_tts.Communicate(text, voice)
        await comm.save(str(out))
        return FileResponse(str(out), media_type="audio/mpeg", filename="speech.mp3")
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
