import jwt
import configparser
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
import datetime
from pyargon2 import hash


class Security:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")

        self.secret = self.config["TOKEN_SECRET"]["secret"]
        self.expiration = self.config["TOKEN_EXPIRATION"]["expiration"]
        
    def hashPassword(self, password: str, secret: str):
        return hash(password, secret)
    
    def basic(self, credentials: HTTPBasicCredentials, UserModel: object, fields: object = {"username": "username", "password": "password"}):
        username = credentials.username
        password = credentials.password
        
        user = UserModel().objects.filter({fields["username"]: username, fields["password"]: self.hashPassword(password, self.secret)})
        if len(user["data"]) == 0:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return True
    
    def basicSession(self, credentials: HTTPBasicCredentials, UserModel: object, fields: object = {"username": "username", "password": "password"}):
        username = credentials.username
        password = credentials.password
        
        user = UserModel().objects.filter({fields["username"]: username, fields["password"]: self.hashPassword(password, self.secret)})
        if len(user["data"]) == 0:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user["data"][0]

    def issueToken(self, user: object):
        payload = {
            "sub": user._id,
            "iat": datetime.datetime.now().timestamp()
        }

        return jwt.encode(payload, self.secret, algorithm="HS256")

    def getCurrentUser(self, token: str, UserModel: object):
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            sub = payload["sub"]
            user = UserModel().objects.get(sub)
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            return user
        except Exception as e:
            print(e)
            raise HTTPException(status_code=401, detail="Invalid token (" + str(e) + ")")

    def checkToken(self, token: str, UserModel: object):
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            iat = payload["iat"]
            sub = payload["sub"]

            user = UserModel().objects.get(sub)
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")

            if iat > (datetime.datetime.now().timestamp() + int(self.expiration)):
                raise HTTPException(status_code=401, detail="Token has expired")

            return True
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid token (" + str(e) + ")")