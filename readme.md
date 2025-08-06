to volume-mount cache, avoiding repeated downloads
    /root/.cache/torch/hub
    /.cache/huggingface

run with: 
```bash
docker run -it --gpus all \
  -v $(pwd)/cache:/root/.cache \
  trellis

```