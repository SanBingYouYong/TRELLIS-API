to volume-mount cache, avoiding repeated downloads
    /root/.cache/torch/hub
    /.cache/huggingface

run with: 
```bash
docker run -it --gpus all \
  -v $(pwd)/cache:/root/.cache \
  trellis

```

# Update: 

start the trellis text-to-3d api:
```bash
docker compose up --build
```
- use Ctrl C to stop, or docker compose down in a new window
- alternative: `docker build -t trellis .` and `docker run -it --gpus all   -v $(pwd)/cache:/root/.cache   -p 8000:8000 trellis` and `python text_to_3d_api.py --host 0.0.0.0 --port 8000`
    - then use Ctrl PQ and `docker attach <container_id>` to detach/reattach

Test the api with: `python test_api.py`
