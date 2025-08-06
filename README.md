# TRELLIS Text-to-3D API

REST API for [Microsoft TRELLIS](https://github.com/microsoft/TRELLIS) text-to-3D generation.

## Quick Start

```bash
docker compose up --build
```

API available at `http://localhost:8000` with interactive docs at `/docs`.

Test with: `python test_api.py`

## API Usage

```bash
# Generate 3D model
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A red sports car", "formats": ["mesh", "gaussian"]}'

# Download files from response URLs
curl -O "http://localhost:8000/files/{job_id}/model.glb"
```

## Features

- **REST API** for text-to-3D generation
- **Multiple formats**: GLB, PLY, MP4 preview videos
- **Docker deployment** with GPU support
- **File management** with automatic cleanup
- **Health monitoring** and error handling

See `API_README.md` for detailed documentation.
