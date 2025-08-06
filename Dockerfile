FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg build-essential git rdfind \
    && rm -rf /var/lib/apt/lists/*

# Configure conda
RUN conda init && \
    conda config --set always_yes true && \
    conda config --add channels defaults

SHELL ["/bin/bash", "-c"]

# Install Python dependencies in one layer for efficiency
RUN pip install --no-cache-dir \
    pillow imageio imageio-ffmpeg tqdm easydict opencv-python-headless ninja rembg onnxruntime trimesh xatlas pyvista pymeshfix igraph transformers \
    git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8 \
    xformers flash-attn spconv-cu120 open3d \
    gradio==4.44.1 gradio_litmodel3d==0.0.1

# Install Kaolin
RUN git clone --recursive https://github.com/NVIDIAGameWorks/kaolin /tmp/extensions/kaolin && \
    export IGNORE_TORCH_VER=1 && \
    pip install --no-cache-dir "Cython >= 0.29.37" && \
    pip install --no-cache-dir /tmp/extensions/kaolin && \
    rm -rf /tmp/extensions/kaolin

# Install nvdiffrast
RUN git clone https://github.com/NVlabs/nvdiffrast.git /tmp/extensions/nvdiffrast && \
    pip install --no-cache-dir /tmp/extensions/nvdiffrast && \
    rm -rf /tmp/extensions/nvdiffrast

# Install diffoctreerast
RUN git clone --recurse-submodules https://github.com/JeffreyXiang/diffoctreerast.git /tmp/extensions/diffoctreerast && \
    export TORCH_CUDA_ARCH_LIST="10.0 10.1 12.0" && \
    pip install --no-cache-dir /tmp/extensions/diffoctreerast && \
    rm -rf /tmp/extensions/diffoctreerast

# Install mip-splatting diff-gaussian-rasterization
RUN git clone https://github.com/autonomousvision/mip-splatting.git /tmp/extensions/mip-splatting && \
    export TORCH_CUDA_ARCH_LIST="10.0 10.1 12.0" && \
    pip install --no-cache-dir /tmp/extensions/mip-splatting/submodules/diff-gaussian-rasterization/ && \
    rm -rf /tmp/extensions/mip-splatting
    
# Clone TRELLIS repo (if needed for build context)
COPY . /app
WORKDIR /app
