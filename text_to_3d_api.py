#!/usr/bin/env python3
"""
TRELLIS Text-to-3D API Server

A FastAPI-based REST API for generating 3D assets from text descriptions using TRELLIS.
This API provides endpoints to generate 3D models in various formats (GLB, PLY, video).

Usage:
    python text_to_3d_api.py

API Endpoints:
    POST /generate: Generate 3D model from text description
    GET /health: Health check endpoint
    GET /: API documentation (Swagger UI)
"""

import os
import sys
import uuid
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import traceback
from datetime import datetime

# Environment setup for TRELLIS
os.environ['SPCONV_ALGO'] = 'native'  # Recommended for single runs

import torch
import numpy as np
import imageio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import uvicorn

# TRELLIS imports
try:
    from trellis.pipelines import TrellisTextTo3DPipeline
    from trellis.utils import render_utils, postprocessing_utils
    from trellis.representations import Gaussian, MeshExtractResult
except ImportError as e:
    print(f"Error importing TRELLIS modules: {e}")
    print("Make sure TRELLIS is properly installed and accessible")
    sys.exit(1)

# Global variables
pipeline = None
MAX_SEED = np.iinfo(np.int32).max
TEMP_DIR = Path(tempfile.gettempdir()) / "trellis_api"
TEMP_DIR.mkdir(exist_ok=True)

# Cleanup tracking
generated_files = {}


class TextTo3DRequest(BaseModel):
    """Request model for text-to-3D generation"""
    prompt: str = Field(..., description="Text description of the 3D object to generate", min_length=1)
    seed: Optional[int] = Field(None, description="Random seed for reproducible generation", ge=0, le=MAX_SEED)
    formats: List[str] = Field(["mesh", "gaussian"], description="Output formats to generate")
    
    # Sparse Structure Generation Parameters
    ss_steps: int = Field(12, description="Sampling steps for sparse structure generation", ge=1, le=50)
    ss_cfg_strength: float = Field(7.5, description="CFG strength for sparse structure generation", ge=0.0, le=20.0)
    
    # Structured Latent Generation Parameters  
    slat_steps: int = Field(12, description="Sampling steps for structured latent generation", ge=1, le=50)
    slat_cfg_strength: float = Field(7.5, description="CFG strength for structured latent generation", ge=0.0, le=20.0)
    
    # Output Options
    generate_video: bool = Field(True, description="Whether to generate preview video")
    video_frames: int = Field(120, description="Number of frames for video generation", ge=30, le=240)
    video_fps: int = Field(15, description="Frames per second for video", ge=10, le=60)
    
    # GLB Export Options (if GLB format requested)
    simplify_ratio: float = Field(0.95, description="Mesh simplification ratio", ge=0.5, le=1.0)
    texture_size: int = Field(1024, description="Texture resolution for GLB export", ge=512, le=2048)


class TextTo3DResponse(BaseModel):
    """Response model for text-to-3D generation"""
    job_id: str = Field(..., description="Unique identifier for this generation job")
    status: str = Field(..., description="Status of the generation (success, error)")
    message: str = Field(..., description="Human-readable status message")
    prompt: str = Field(..., description="The input prompt that was processed")
    seed: int = Field(..., description="The seed used for generation")
    generation_time_seconds: float = Field(..., description="Time taken for generation")
    
    # File paths (relative to API base URL)
    files: Dict[str, str] = Field(default_factory=dict, description="Generated file paths by format")
    
    # Metadata
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Information about the generated model")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    gpu_available: bool
    model_loaded: bool
    timestamp: str


async def load_pipeline():
    """Load the TRELLIS pipeline on startup"""
    global pipeline
    try:
        print("Loading TRELLIS text-to-3D pipeline...")
        pipeline = TrellisTextTo3DPipeline.from_pretrained("microsoft/TRELLIS-text-xlarge")
        
        if torch.cuda.is_available():
            pipeline.cuda()
            print(f"Pipeline loaded on GPU: {torch.cuda.get_device_name()}")
        else:
            print("Warning: CUDA not available, using CPU (will be very slow)")
            
        print("Pipeline loaded successfully!")
        
    except Exception as e:
        print(f"Error loading pipeline: {e}")
        traceback.print_exc()
        raise


async def cleanup_old_files():
    """Background task to cleanup old generated files"""
    try:
        current_time = datetime.now().timestamp()
        files_to_remove = []
        
        for job_id, file_info in generated_files.items():
            # Remove files older than 1 hour
            if current_time - file_info.get('timestamp', 0) > 3600:
                files_to_remove.append(job_id)
                
        for job_id in files_to_remove:
            file_info = generated_files.pop(job_id, {})
            for file_path in file_info.get('files', {}).values():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
                    
    except Exception as e:
        print(f"Error in cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await load_pipeline()
    yield
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="TRELLIS Text-to-3D API",
    description="Generate 3D assets from text descriptions using TRELLIS",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "TRELLIS Text-to-3D API",
        "version": "1.0.0",
        "description": "Generate 3D assets from text descriptions",
        "endpoints": {
            "/generate": "POST - Generate 3D model from text",
            "/health": "GET - Health check",
            "/files/{job_id}/{filename}": "GET - Download generated files",
            "/docs": "GET - Interactive API documentation"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if pipeline is not None else "unhealthy",
        message="API is running" if pipeline is not None else "Pipeline not loaded",
        gpu_available=torch.cuda.is_available(),
        model_loaded=pipeline is not None,
        timestamp=datetime.now().isoformat()
    )


@app.post("/generate", response_model=TextTo3DResponse)
async def generate_3d_from_text(
    request: TextTo3DRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a 3D asset from text description
    
    This endpoint processes a text prompt and generates 3D assets in the requested formats.
    The generation process may take several minutes depending on the complexity and settings.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not loaded")
    
    job_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    try:
        # Set random seed
        seed = request.seed if request.seed is not None else np.random.randint(0, MAX_SEED)
        
        # Create job directory
        job_dir = TEMP_DIR / job_id
        job_dir.mkdir(exist_ok=True)
        
        print(f"Starting generation for job {job_id}: '{request.prompt}' (seed: {seed})")
        
        # Run the pipeline - don't specify formats to get all by default (gaussian, mesh, radiance_field)
        # We'll filter the saved files based on user request later
        outputs = pipeline.run(
            request.prompt,
            seed=seed,
            sparse_structure_sampler_params={
                "steps": request.ss_steps,
                "cfg_strength": request.ss_cfg_strength,
            },
            slat_sampler_params={
                "steps": request.slat_steps,
                "cfg_strength": request.slat_cfg_strength,
            },
        )
        
        generated_files_info = {}
        model_info = {
            "formats_generated": list(outputs.keys()),
            "num_gaussians": len(outputs.get('gaussian', [])),
            "num_meshes": len(outputs.get('mesh', [])),
            "num_radiance_fields": len(outputs.get('radiance_field', []))
        }
        
        # Save outputs in requested formats
        for format_name, format_outputs in outputs.items():
            if format_outputs and len(format_outputs) > 0:  # Check if there are outputs for this format
                if format_name == 'gaussian' and 'gaussian' in request.formats:
                    # Save Gaussian as PLY only if user requested it
                    try:
                        ply_path = job_dir / f"{job_id}_gaussian.ply"
                        format_outputs[0].save_ply(str(ply_path))
                        generated_files_info['gaussian_ply'] = str(ply_path)
                        print(f"  Saved Gaussian PLY: {ply_path}")
                    except Exception as e:
                        print(f"  Error saving Gaussian PLY: {e}")
                        
                elif format_name == 'mesh' and 'mesh' in request.formats:
                    # Generate GLB file - now we should always have both gaussian and mesh
                    try:
                        if 'gaussian' in outputs and outputs['gaussian'] and len(outputs['gaussian']) > 0:
                            glb = postprocessing_utils.to_glb(
                                outputs['gaussian'][0],
                                outputs['mesh'][0],
                                simplify=request.simplify_ratio,
                                texture_size=request.texture_size,
                                verbose=False
                            )
                            glb_path = job_dir / f"{job_id}_mesh.glb"
                            glb.export(str(glb_path))
                            generated_files_info['mesh_glb'] = str(glb_path)
                            print(f"  Saved Mesh GLB: {glb_path}")
                        else:
                            print(f"  Error: No gaussian available for GLB export")
                    except Exception as e:
                        print(f"  Error saving Mesh GLB: {e}")
                        
                elif format_name == 'radiance_field':
                    # For radiance field, we might need different handling
                    # print(f"  Radiance field format found but not implemented for file export")
                    pass
                    
        print(f"Generated files: {list(generated_files_info.keys())}")
        
        # Generate preview video if requested
        if request.generate_video and outputs:
            try:
                video_components = []
                
                # Try to render different representations
                if 'gaussian' in outputs and outputs['gaussian']:
                    video_gaussian = render_utils.render_video(
                        outputs['gaussian'][0], 
                        num_frames=request.video_frames
                    )['color']
                    video_components.append(video_gaussian)
                    
                if 'mesh' in outputs and outputs['mesh']:
                    video_mesh = render_utils.render_video(
                        outputs['mesh'][0], 
                        num_frames=request.video_frames
                    )['normal']
                    video_components.append(video_mesh)
                
                # Combine videos side by side if multiple components
                if len(video_components) > 1:
                    video = [np.concatenate([comp[i] for comp in video_components], axis=1) 
                            for i in range(len(video_components[0]))]
                else:
                    video = video_components[0] if video_components else None
                    
                if video:
                    video_path = job_dir / f"{job_id}_preview.mp4"
                    imageio.mimsave(str(video_path), video, fps=request.video_fps)
                    generated_files_info['preview_video'] = str(video_path)
                    
            except Exception as e:
                print(f"Warning: Could not generate preview video: {e}")
        
        # Clear GPU memory
        torch.cuda.empty_cache()
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # Store file information for later retrieval
        generated_files[job_id] = {
            'files': generated_files_info,
            'timestamp': datetime.now().timestamp(),
            'job_dir': str(job_dir)
        }
        
        # Schedule cleanup task
        background_tasks.add_task(cleanup_old_files)
        
        print(f"Generation completed for job {job_id} in {generation_time:.2f}s")
        
        # Convert absolute paths to relative API paths
        api_files = {}
        for file_type, file_path in generated_files_info.items():
            filename = Path(file_path).name
            api_files[file_type] = f"/files/{job_id}/{filename}"
        
        return TextTo3DResponse(
            job_id=job_id,
            status="success",
            message="3D asset generated successfully",
            prompt=request.prompt,
            seed=seed,
            generation_time_seconds=generation_time,
            files=api_files,
            model_info=model_info
        )
        
    except Exception as e:
        # Clean up on error
        if job_id in generated_files:
            del generated_files[job_id]
        
        error_msg = f"Error generating 3D asset: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        
        # Clear GPU memory on error too
        torch.cuda.empty_cache()
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/files/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """Download a generated file"""
    if job_id not in generated_files:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = generated_files[job_id]
    file_path = None
    
    # Find the file path
    for file_type, path in job_info['files'].items():
        if Path(path).name == filename:
            file_path = path
            break
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type based on file extension
    ext = Path(filename).suffix.lower()
    media_type_map = {
        '.glb': 'model/gltf-binary',
        '.ply': 'application/octet-stream',
        '.mp4': 'video/mp4',
    }
    media_type = media_type_map.get(ext, 'application/octet-stream')
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TRELLIS Text-to-3D API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    
    args = parser.parse_args()
    
    print(f"Starting TRELLIS Text-to-3D API on {args.host}:{args.port}")
    
    uvicorn.run(
        "text_to_3d_api:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=False
    )
