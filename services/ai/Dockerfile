FROM conda/miniconda3

WORKDIR /app

RUN conda update -n base -c defaults conda -y
RUN pip install --no-cache-dir fastapi uvicorn pydantic requests

# copy only the AI folder
COPY backend/lm_core ./backend/lm_core

EXPOSE 9001
CMD ["bash","-lc","uvicorn backend.lm_core.api:app --host 0.0.0.0 --port 9001"]
