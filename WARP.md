# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Muxxy Swap is a video VJ/mixing application that enables real-time video manipulation and audio analysis. It's a microservices architecture with a SvelteKit frontend and a Python-based audio analysis backend service.

### Architecture

**Monorepo Structure:**
- `apps/web/` - SvelteKit frontend using Svelte 5 runes, Tailwind CSS 4, and Mux components
- `services/audio-analysis/` - FastAPI service using Essentia for audio feature extraction (BPM, beats, onsets)

**Key Integration Points:**
- Frontend communicates with audio-analysis service via `/api/analyze` proxy endpoint (apps/web/src/routes/api/analyze/+server.ts)
- Mux API handles video upload/storage via `/api/upload/mux` endpoint (apps/web/src/routes/api/upload/mux/+server.ts)
- Audio analysis service downloads video from Mux playback URLs and extracts audio features
- Service-to-service communication defined in docker-compose.yml (frontend -> http://audio-analysis:8000)

**Core Data Flow:**
1. User uploads video via Mux uploader component or file input
2. Frontend polls Mux API for playback ID once upload completes
3. Frontend constructs MP4 URL: `https://stream.mux.com/{playbackId}/medium.mp4`
4. Frontend calls `/api/analyze` with MP4 URL
5. Audio-analysis service downloads, extracts audio features using Essentia
6. Analysis results (BPM, beats, onsets) returned to frontend for UI display

**UI Architecture:**
- 4x8 clip grid (4 layers × 8 columns) in apps/web/src/routes/+page.svelte
- Layer-based video mixing with opacity and blend modes
- Svelte 5 runes for reactivity ($state)
- Mux web components (@mux/mux-player, @mux/mux-uploader)

## Development Commands

### Frontend (apps/web/)

**Prerequisites:**
- Uses Bun 1.x as package manager
- Requires .env file with Mux credentials (see .env.example)

**Essential Commands:**
```bash
cd apps/web
bun install              # Install dependencies
bun run dev              # Start dev server on port 5173
bun run build            # Production build
bun run preview          # Preview production build
bun run check            # Type-check with svelte-check
bun run check:watch      # Type-check in watch mode
```

**Environment Variables Required:**
- MUX_TOKEN_ID - Mux API token ID
- MUX_TOKEN_SECRET - Mux API token secret
- ANALYSIS_SERVICE_URL - URL to audio analysis service (default: http://audio-analysis:8000)

### Audio Analysis Service (services/audio-analysis/)

**Prerequisites:**
- Python 3.11+
- Uses `uv` for dependency management
- Requires Essentia with system dependencies (ffmpeg, libfftw3, etc.)

**Essential Commands:**
```bash
cd services/audio-analysis
uv sync                  # Install dependencies (creates .venv)
uv run uvicorn main:app --reload --port 8000  # Start dev server
```

**API Endpoints:**
- GET `/` - Health check
- POST `/analyze` - Analyze audio from URL (expects JSON body with "url" field)

### Docker Compose

**Run entire stack:**
```bash
docker compose up        # Start all services
docker compose up --build  # Rebuild and start
docker compose down      # Stop all services
```

**Services:**
- `frontend` - Exposed on http://localhost:3000
- `audio-analysis` - Exposed on http://localhost:8000

## Code Patterns

### Frontend API Route Handlers
- Use SvelteKit's `+server.ts` convention for API endpoints
- Access private environment variables via `$env/static/private`
- Return responses using `json()` helper from '@sveltejs/kit'

### Svelte 5 State Management
- Use `$state()` rune for reactive variables
- Use `$derived()` for computed values (if needed)
- Component logic lives in `<script lang="ts">` blocks

### Mux Integration
- Create upload URLs via `mux.video.uploads.create()`
- Poll upload status via `mux.video.uploads.retrieve(uploadId)`
- Retrieve asset playback IDs via `mux.video.assets.retrieve(assetId)`
- Always enable mp4_support: 'standard' for downloads

### Audio Analysis Service
- Uses Essentia standard algorithms (RhythmExtractor2013, Onsets, Envelope)
- Downloads audio to temporary files, processes at 44.1kHz sample rate
- Returns JSON with BPM, beats array (timestamps), onsets array (timestamps), duration

## Project-Specific Notes

### Mux Configuration
- Current setup uses 'public' playback policy - restrict for production
- CORS origin set to '*' in upload creation - should be locked down
- MP4 support required for audio analysis service to download videos

### Audio Analysis
- Service expects publicly accessible URLs (Mux stream URLs work)
- Processes full audio file (no streaming analysis yet)
- Returns beat/onset timestamps in seconds for timeline synchronization

### Deployment Considerations
- Frontend uses adapter-auto (supports Node, Cloudflare, Vercel, etc.)
- Audio-analysis service needs ffmpeg and audio processing libraries
- Both services containerized with Dockerfiles using multi-stage builds
