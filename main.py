import uvicorn

from subprocess import Popen, PIPE
from functools import lru_cache
from typing import Any, Dict
from fastapi import FastAPI, Depends, HTTPException

from config import Settings

app = FastAPI()


@lru_cache()
def get_settings():
    return Settings()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/sign/")
def sign(body: Dict[Any, Any], settings: Settings = Depends(get_settings)):
    # validate secret
    if body.get("secret") != settings.secret:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid secret."
            }
        )

    # get payload
    data = body.get("data")
    if not data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing `data` payload."
            }
        )

    # run ksi
    process = Popen(["ls", "-la", "."], stdout=PIPE)
    (output, err) = process.communicate()
    exit_code = process.wait()

    # sign data
    return data


if __name__ == '__main__':
    uvicorn.run(app, port=5000, host='127.0.0.1')
