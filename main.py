import os
import json
import base64
from collections import OrderedDict

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


class DataSignatureManager(object):

    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def _preprocess_data(data):
        # remove `dateModified` property
        if "dateModified" in data:
            data.pop("dateModified")

        # add property for updated attributes
        # first set `updatedAttributes` to empty dict
        # so that it's also included in call to `data.keys()`
        # also include ksiSignature prop which is added after signature is generated
        data["updatedAttributes"] = {}
        data["updatedAttributes"] = ",".join(sorted(list(data.keys()) + ["ksiSignature"]))

    def _sorted_dict_props(self, data):

        if type(data) != dict:
            return data

        ordered_data = OrderedDict()
        for prop, value in sorted(data.items(), key=lambda item: item[0]):
            ordered_data[prop] = self._sorted_dict_props(data=value)

        return ordered_data

    def _get_signature(self, data):
        # write data to file
        with open('data.json', 'w') as f:
            f.write(data)

        # run ksi process
        process = Popen([
            "ksi", "sign",
            "-i", "data.json", "-o", "-",
            "-S", self.settings.aggr_url,
            "--aggr-user", self.settings.aggr_user,
            "--aggr-key", self.settings.aggr_password,
        ], stdout=PIPE)

        # get response & wait to finish
        (raw_signature, err) = process.communicate()
        exit_code = process.wait()

        # raise exception for non-zero exit codes
        if exit_code:
            raise DataSignatureManager.SignatureError()

        # decode & return signature
        return base64. \
            b64encode(raw_signature). \
            decode("utf-8")

    def _serialized_data(self, data):
        # serialize remove whitespace,
        # order fields alphabetically,
        return json.dumps(
            self._sorted_dict_props(data),
            separators=(',', ':')
        )

    def get_signed_data(self, data):
        # preprocess
        self._preprocess_data(data=data)

        # get signature
        signature = self._get_signature(data=self._serialized_data(data=data))

        # add signature
        data["ksiSignature"] = signature

        # serialize again and return
        return json.loads(self._serialized_data(data=data))

    class SignatureError(ValueError):
        pass


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

    # sign data
    try:
        signed_data = DataSignatureManager(settings=settings).\
            get_signed_data(data=data)
    except DataSignatureManager.SignatureError:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Signing error."
            }
        )

    # return signed data
    return {
        "signed_data": signed_data,
    }


if __name__ == '__main__':
    uvicorn.run(app, port=int(os.environ.get("PORT", "5000")), host='0.0.0.0')
