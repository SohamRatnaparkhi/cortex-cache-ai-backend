import os

import jwt
from dotenv import load_dotenv
from pydantic import BaseModel

if os.path.exists(".env"):
    load_dotenv()


secret = os.getenv("JWT_SECRET")


class Credentials(BaseModel):
    userId: str
    emailId: str
    apiKey: str


def get_credentials(token: str):
    jwt_token = token.split(" ")[1]

    # decode jwt token
    payload: Credentials = jwt.decode(
        jwt_token, secret, algorithms=["HS256"])
    # print(type(payload))
    # print(payload.keys())

    userId = payload["userId"]
    emailId = payload["email"]
    apiKey = payload["apiKey"]

    return userId, emailId, apiKey
