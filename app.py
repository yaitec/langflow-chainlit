import chainlit as cl
import httpx
import os
import json
from typing import Optional

LF_BASE_API_URL = os.environ.get("LF_BASE_API_URL")
LF_API_KEY = os.environ.get("LF_API_KEY")
LF_FLOW_ID = os.environ.get("LF_FLOW_ID")

if not LF_BASE_API_URL:
    raise ValueError("LF_BASE_API_URL is not set. Please set it in your environment variables.")

if not LF_FLOW_ID:
    raise ValueError("LF_FLOW_ID is not set. Please set it in your environment variables.")

async def run_flow(message: str,
    flow_id: str,
    output_type: str = "chat",
    input_type: str = "chat",
    tweaks: Optional[dict] = None) -> dict:
    """
    Run a flow with a given message and optional tweaks.

    :param message: The message to send to the flow
    :param flow_id: The ID of the flow to run
    :param tweaks: Optional tweaks to customize the flow
    :return: The JSON response from the flow
    """
    if not flow_id:
        raise ValueError("Flow ID is not provided.")

    api_url = f"{LF_BASE_API_URL}/api/v1/run/{flow_id}?stream=true"

    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
    }
    headers = None
    if tweaks:
        payload["tweaks"] = tweaks
    
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        try:
            json_response = response.json()
            return json_response
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Response content: {response.text}")
            raise

@cl.on_chat_start
async def on_chat_start():
    # If we use header auth this could be read from the user metadata
    cl.user_session.set("flow_id", LF_FLOW_ID)
    cl.user_session.set("tweaks", {})

@cl.on_message
async def on_message(msg: cl.Message):

    content = msg.content
    msg = await cl.Message(content="").send()

    response = await run_flow(
        message=content,
        flow_id=cl.user_session.get("flow_id"),
        tweaks=cl.user_session.get("tweaks")
    )

    stream_url = response.get("outputs")[0].get("outputs")[0].get("artifacts").get("stream_url")

    async with httpx.AsyncClient() as client:
        stream = await client.get(f"{LF_BASE_API_URL}{stream_url}")
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                data = line[len("data: "):]
                parsed = json.loads(data)
                if token := parsed.get("chunk"):
                    await msg.stream_token(token)

    await msg.update()
