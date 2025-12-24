import os
import tempfile
import requests
import essentia.standard as es
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class AnalysisRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"message": "Audio Analysis Service Ready (Essentia)"}

@app.post("/analyze")
def analyze_audio(request: AnalysisRequest):
    temp_file_path = None
    try:
        # 1. Download the file
        print(f"Downloading audio from {request.url}...")
        response = requests.get(request.url, stream=True)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        print(f"Audio saved to {temp_file_path}")

        # 2. Load Audio
        # Downsample to 44.1kHz for consistency
        loader = es.MonoLoader(filename=temp_file_path, sampleRate=44100)
        audio = loader()

        # 3. Analyze Rhythm (BPM & Beats)
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)

        # 4. Analyze Onsets (Transient Detection)
        # Using a standard onset detection chain
        od_complex = es.OnsetDetection(method='complex')
        w = es.Windowing(type='hann')
        fft = es.FFT()
        c2p = es.CartesianToPolar()
        
        # Helper to run onset detection (basic frame-wise processing)
        # Typically we use OnsetRate or similar, but let's stick to OnsetDetectionGlobal usually found in aggregators
        # Or simpler: use the OnsetDetection function on frames
        # For simplicity in this v1, let's use a simpler high-level algo if available, 
        # but RhythmExtractor gives us beats. Onsets are different.
        # Let's use OnsetRate which handles the chain internally or build a simple loop.
        
        # Simplified Onset Generation using 'complex' method
        onsets_hfc = es.Onsets(method='complex')
        onsets = onsets_hfc(audio)

        # 5. Analyze Energy/Intensity (RMS)
        # Calculate global energy or frame-based? Let's give frame-based energy for visualization
        emp = es.Envelope()
        envelope = emp(audio)
        
        # Downsample envelope for visualization (e.g., 100 points per second)
        # 44100 samples/sec. Hop size?
        # Let's just return the global metrics for now and the beats/onsets timestamps.

        result = {
            "bpm": float(bpm),
            "bpm_confidence": float(beats_confidence),
            "beats": beats.tolist(),
            "onsets": onsets.tolist(),
            "duration": len(audio) / 44100.0,
            # "energy_preview": envelope[::441].tolist() # Too large for JSON? maybe
        }

        # Cleanup
        os.unlink(temp_file_path)

        return result

    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
