import time

from playwright.sync_api import sync_playwright

from app.config import load_config, Config
from app.login import login
from app.scan import scan

with sync_playwright() as p:
    config: Config = load_config("../config.yaml")
    browser, page = login(p, config)

    account = scan(page, config)


    print(account)

    time.sleep(5)
    browser.close()