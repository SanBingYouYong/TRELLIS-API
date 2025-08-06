# TRELLIS Text-to-3D API

A REST API server for generating 3D assets from text descriptions using Microsoft's TRELLIS model. This API provides a simple HTTP interface to the powerful text-to-3D generation capabilities of TRELLIS.

## Features

- **Text-to-3D Generation**: Convert text descriptions into high-quality 3D assets
- **Multiple Output Formats**: Generate GLB files, PLY files, and preview videos
- **Flexible Parameters**: Control generation quality, seed, and export settings
- **REST API**: Simple HTTP interface for easy integration
- **Docker Support**: Ready-to-use containerization
- **File Management**: Automatic cleanup of temporary files
- **Health Monitoring**: Built-in health check endpoints

## Quick Start

### Using Docker (Recommended)

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **The API will be available at:**
   - `http://localhost:8000` - API endpoints
   - `http://localhost:8000/docs` - Interactive documentation (Swagger UI)

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install -r api_requirements.txt
   ```

2. **Run the server:**
   ```bash
   python text_to_3d_api.py
   ```

## API Endpoints

### POST `/generate`
Generate a 3D asset from a text description.

**Request Body:**
```json
{
  "prompt": "A futuristic robot with glowing eyes",
  "seed": 42,
  "formats": ["mesh", "gaussian"],
  "ss_steps": 12,
  "ss_cfg_strength": 7.5,
  "slat_steps": 12,
  "slat_cfg_strength": 7.5,
  "generate_video": true,
  "video_frames": 120,
  "video_fps": 15,
  "simplify_ratio": 0.95,
  "texture_size": 1024
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "success",
  "message": "3D asset generated successfully",
  "prompt": "A futuristic robot with glowing eyes",
  "seed": 42,
  "generation_time_seconds": 45.2,
  "files": {
    "mesh_glb": "/files/uuid-string/model.glb",
    "gaussian_ply": "/files/uuid-string/model.ply",
    "preview_video": "/files/uuid-string/preview.mp4"
  },
  "model_info": {
    "formats_generated": ["gaussian", "mesh"],
    "num_gaussians": 1,
    "num_meshes": 1
  }
}
```

### GET `/files/{job_id}/{filename}`
Download a generated file.

### GET `/health`
Check API health and status.

**Response:**
```json
{
  "status": "healthy",
  "message": "API is running",
  "gpu_available": true,
  "model_loaded": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

## Usage Examples

### Using the Python Client

```python
from api_client_example import TrellisAPIClient

# Create client
client = TrellisAPIClient("http://localhost:8000")

# Check health
health = client.health_check()
print(f"API Status: {health['status']}")

# Generate 3D asset
result = client.generate_3d(
    prompt="A medieval castle on a hill",
    seed=123,
    formats=["mesh", "gaussian"]
)

# Download files
for file_type, file_url in result['files'].items():
    filename = file_url.split('/')[-1]
    client.download_file(result['job_id'], filename, "./output")
```

### Using cURL

```bash
# Generate 3D asset
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A red sports car",
    "seed": 42,
    "formats": ["mesh"],
    "generate_video": true
  }'

# Download generated file
curl -O "http://localhost:8000/files/{job_id}/model.glb"
```

### Using Python requests

```python
import requests

# Generate 3D asset
response = requests.post(
    "http://localhost:8000/generate",
    json={
        "prompt": "A colorful butterfly",
        "formats": ["mesh", "gaussian"],
        "generate_video": True
    }
)

result = response.json()
print(f"Job ID: {result['job_id']}")

# Download GLB file
if 'mesh_glb' in result['files']:
    file_response = requests.get(f"http://localhost:8000{result['files']['mesh_glb']}")
    with open("butterfly.glb", "wb") as f:
        f.write(file_response.content)
```

## Parameters

### Generation Parameters

- **`prompt`** (required): Text description of the 3D object
- **`seed`** (optional): Random seed for reproducible generation
- **`formats`** (default: `["mesh", "gaussian"]`): Output formats to generate

### Sparse Structure Generation
- **`ss_steps`** (default: 12): Number of sampling steps (1-50)
- **`ss_cfg_strength`** (default: 7.5): CFG guidance strength (0.0-20.0)

### Structured Latent Generation
- **`slat_steps`** (default: 12): Number of sampling steps (1-50)
- **`slat_cfg_strength`** (default: 7.5): CFG guidance strength (0.0-20.0)

### Output Options
- **`generate_video`** (default: true): Generate preview video
- **`video_frames`** (default: 120): Number of video frames (30-240)
- **`video_fps`** (default: 15): Video frame rate (10-60)

### GLB Export Options
- **`simplify_ratio`** (default: 0.95): Mesh simplification ratio (0.5-1.0)
- **`texture_size`** (default: 1024): Texture resolution (512-2048)

## Output Formats

### GLB Files (`.glb`)
- Standard 3D format compatible with most 3D software
- Includes textures and materials
- Suitable for web viewing, Unity, Blender, etc.

### PLY Files (`.ply`)
- Point cloud format containing 3D Gaussians
- Large files (~50MB) with detailed representation
- Suitable for research and advanced 3D processing

### Video Files (`.mp4`)
- Preview animation showing the 3D model rotating
- Useful for quick visualization and sharing
- Combines different views when multiple formats are generated

## Performance and Requirements

### System Requirements
- **GPU**: NVIDIA GPU with CUDA support (recommended: RTX 3080 or better)
- **RAM**: 16GB+ system RAM
- **VRAM**: 8GB+ GPU memory
- **Storage**: 50GB+ for model cache and temporary files

### Generation Times
- **Simple objects**: 30-60 seconds
- **Complex objects**: 2-5 minutes
- **High-quality settings**: 5-10 minutes

### Optimization Tips
- Use `native` SPCONV algorithm for single generations
- Lower sampling steps for faster generation
- Reduce texture size for smaller files
- Skip video generation if not needed

## Configuration

### Environment Variables
- **`CUDA_VISIBLE_DEVICES`**: GPU device selection
- **`SPCONV_ALGO`**: Set to `native` for single runs
- **`ATTN_BACKEND`**: Use `xformers` or `flash-attn`

### Docker Configuration
The API can be configured through environment variables in docker-compose.yml:

```yaml
environment:
  - CUDA_VISIBLE_DEVICES=0
  - SPCONV_ALGO=native
```

## Troubleshooting

### Common Issues

1. **"Pipeline not loaded" error**
   - Check GPU availability and CUDA setup
   - Verify model downloads completed
   - Check system memory and disk space

2. **Generation timeout**
   - Increase timeout in client requests
   - Reduce quality parameters
   - Check GPU memory usage

3. **Out of memory errors**
   - Reduce batch size or quality settings
   - Clear cache: `torch.cuda.empty_cache()`
   - Restart the API service

4. **Model download issues**
   - Check internet connection
   - Verify Hugging Face access
   - Clear cache and retry

### Logs and Monitoring

- API logs include generation progress and timing
- Health endpoint provides system status
- File cleanup happens automatically after 1 hour

## Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -r api_requirements.txt

# Run with auto-reload
uvicorn text_to_3d_api:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.

## License

This API wrapper follows the same license as the original TRELLIS project. See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Check the original TRELLIS repository for model-specific issues
4. Open an issue with detailed error information
