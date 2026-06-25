import os
from croo import Config, AgentClient


def make_client(sdk_key: str | None = None) -> AgentClient:
    config = Config(
        base_url=os.environ["CROO_API_URL"],
        ws_url=os.environ["CROO_WS_URL"],
    )
    return AgentClient(config, sdk_key or os.environ["CROO_SDK_KEY"])
