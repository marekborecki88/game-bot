import os
import re
from dataclasses import dataclass
import yaml
from dotenv import load_dotenv

@dataclass
class Config:
    server_url: str
    speed: int
    user_login: str
    user_password: str
    headless: bool
    log_level: str = "INFO"


def load_config(file_path: str) -> Config:
    load_dotenv()

    with open(file_path, 'r') as file:
        content = file.read()

    def replace_env_var(match):
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))

    content = re.sub(r'\$\{(\w+)}', replace_env_var, content)

    data = yaml.safe_load(content)
    return Config(
        server_url=data['server_url'],
        speed=data['speed'],
        user_login=data['user_login'],
        user_password=data['user_password'],
        headless=data['headless'],
        log_level=data.get('log_level', 'INFO')
    )


