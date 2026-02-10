from pydantic import BaseModel, Field
from typing import List
import json

class MsgOutput(BaseModel):
    message_id : int = Field('message id')
    is_concern : bool = Field('True if the message is a concern, else False')

class FullOutput(BaseModel):    
    result : List[MsgOutput] 


prompt = lambda batch : f"""
### TASK : 
You are a project manager.You task is to identify if the client is not satisfied by our services.
1. Analyze these messages. Identify if they are a "User Concern" in the message.User is not satisfied with the service. Ignore greetings or neutral acknowledgments.

### MESSAGE BATCH
{batch}

You must respond ONLY with a JSON object that strictly follows this schema:
{json.dumps(FullOutput.model_json_schema(), indent=2)}

"""

