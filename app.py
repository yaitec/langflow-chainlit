import chainlit as cl
import httpx
import os
from typing import Optional

LF_BASE_API_URL = os.environ.get("LF_BASE_API_URL")
LF_API_KEY = os.environ.get("LF_API_KEY")

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
    api_url = f"{LF_BASE_API_URL}/{flow_id}"

    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
    }
    headers = None
    if tweaks:
        payload["tweaks"] = tweaks
    if LF_API_KEY:
        headers = {"x-api-key": LF_API_KEY}
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

# We could use header auth to check on a specific header to get the flow_id and store it in the user metadata.
# This way one Chainlit app could serve multiple flows based on the header.

# @cl.header_auth_callback
# def header_auth_callback(headers: dict) -> Optional[cl.User]:
#   if headers.get("test-header") == "test-value":
#     return cl.User(identifier="admin", metadata={"role": "admin", "provider": "header"})
#   else:
#     return None

@cl.on_chat_start
async def on_chat_start():
    # If we use header auth this could be read from the user metadata
    FLOW_ID = "dcf7de2b-9d40-4cc4-ae65-f40ee907dc88"
    cl.user_session.set("flow_id", FLOW_ID)
    cl.user_session.set("tweaks", {})

@cl.on_message
async def on_message(msg: cl.Message):
    response = await run_flow(message=msg.content, flow_id=cl.user_session.get("flow_id"), tweaks=cl.user_session.get("tweaks"))
    response_text = response.get("outputs")[0].get("outputs")[0].get("results").get("result")
    await cl.Message(content=response_text).send()