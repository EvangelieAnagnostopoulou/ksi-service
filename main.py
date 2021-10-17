import os
import json
import uvicorn

from subprocess import Popen, PIPE
from functools import lru_cache
from typing import Any, Dict
from fastapi import FastAPI, Depends, HTTPException

from dotenv import load_dotenv
from pydantic import BaseSettings


load_dotenv()


class Settings(BaseSettings):
    secret: str

    aggr_url: str = "http://tryout.guardtime.net:8080/gt-signingservice"
    aggr_user: str = "test-user@example.com"
    aggr_password: str

    class Config:
        env_prefix = ""


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

    # write json to file
    with open('data.json', 'w') as f:
        json.dump(data, f)

    # run ksi
    process = Popen([
        "ksi", "sign",
        "-i", "data.json", "-o", "-",
        "-S", settings.aggr_url,
        "--aggr-user", settings.aggr_user,
        "--aggr-key", settings.aggr_password,
    ])
    process = Popen(["ls", "-la", "."], stdout=PIPE)
    (output, err) = process.communicate()
    exit_code = process.wait()

    # sign data
    return data


if __name__ == '__main__':
    uvicorn.run(app, port=int(os.environ.get("PORT", "5000")), host='0.0.0.0')
