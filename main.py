import os
import json
import base64
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
    ], stdout=PIPE)
    (raw_signature, err) = process.communicate()
    exit_code = process.wait()

    if exit_code:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Signing error."
            }
        )

    # encode
    signature = base64.\
        b64encode(raw_signature).\
        decode("utf-8")

    # sign data
    return {
        "data": data,
        "signature": signature,
    }


if __name__ == '__main__':
    uvicorn.run(app, port=int(os.environ.get("PORT", "5000")), host='0.0.0.0')
