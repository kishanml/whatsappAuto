import os
from typing import Any, Optional,List
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .response import TextDelta,TokenUsage,StreamEvent,EventType
from typing import AsyncGenerator
load_dotenv()

class LLMClient:

    def __init__(self, model_name : str = "gemini-2.5-flash"):    
        self._client : Optional[AsyncOpenAI] = None
        self.model_name = model_name

    def get_client(self) -> AsyncOpenAI:

        if self._client is None:
            self._client  = AsyncOpenAI(
                api_key=os.environ["GEMINI_API_KEY"],
               base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )

        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(self, messages : List[dict[str,Any]], stream : bool = True):

        client = self.get_client()
        kwargs  ={"model":self.model_name,
                  "messages":messages,
                  "stream" : stream}
        if stream:
            async for event in self._stream_response(client, kwargs):
                yield event


        else:
            event = await self._non_stream_response(client, kwargs)
            yield event

    async def _stream_response(self,client : AsyncOpenAI, kwargs : dict[str,Any]):

        response = await client.chat.completions.create(**kwargs)

        usage : Optional[TokenUsage] = None
        finish_reason : Optional[str] = None

        async for chunk in response:
            if hasattr(chunk,"usage") and chunk.usage:
                usage = TokenUsage(
                prompt_tokens=chunk.usage.prompt_tokens,
                completion_tokens= chunk.usage.completion_tokens,
                total_tokens= chunk.usage.total_tokens,
            )
            
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason
            if delta.content:
                yield StreamEvent(type=EventType.TEXT_DELTA,
                                  text_delta=TextDelta(delta.content))
                
        yield StreamEvent(type=EventType.MESSAGE_COMPLETE,
                          finish_reason=finish_reason,
                          usage=usage)
                

        

    async def _non_stream_response(self,client : AsyncOpenAI, kwargs : dict[str,Any]):

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        text_delta, usage =  None, None

        if message.content:
            text_delta = TextDelta(content=message.content)
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens= response.usage.completion_tokens,
                total_tokens= response.usage.total_tokens,
            )
        return StreamEvent(
            type=EventType.TEXT_DELTA,
            text_delta=text_delta,
            finish_reason= choice.finish_reason,
            usage= usage)