from dataclasses import dataclass

import yaml

@dataclass
class Config:
    server_url: str
    speed: int
    user_login: str
    user_password: str
    headless: bool


def load_config(file_path: str) ->Config:
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        return Config(
            server_url=data['server_url'],
            speed=data['speed'],
            user_login=data['user_login'],
            user_password=data['user_password'],
            headless=data['headless']
        )


