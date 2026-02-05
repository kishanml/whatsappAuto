import re
import pandas as pd

from enum import Enum
from pathlib import Path


class REGEX_PATTERNS(str,Enum):

    HIGHLIGHTS_PATTERN = "^(\d{2}\/\d{2}\/\d{2,4}),\s(\d{1,2}:\d{1,2}(?:[\s.-]?(?:[aApP][mM]|[aApP]))?)\s-\s"
    MESSAGE_PATTERN = "^(?P<date>\d{2}\/\d{2}\/\d{2,4}),\s(?P<time>\d{1,2}:\d{1,2}(?:\s|[ .-]?(?:[aApP][mM]))?)\s-\s(?P<sender_no>((?:\+?\d{1,3})?[\s.-]?\(?\d{2,5}\)?[\s.-]?\d{3,5}[\s.-]?\d{3,5})|(?P<sender>[A-Za-z].*)):\s(?P<message>\w.*)$"

def create_dataframe_from_chats(chat_input_path : str) -> pd.DataFrame:
    
    file_path = Path(chat_input_path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"{file_path} is an invalid file path!")

    highlight_comp = re.compile(REGEX_PATTERNS.HIGHLIGHTS_PATTERN)
    message_comp = re.compile(REGEX_PATTERNS.MESSAGE_PATTERN)
    
    chat_content = open(chat_input_path,'r').read().replace("\n\n"," ")
    chat_content_lines = chat_content.split('\n')

    chat_list = []

    for message in chat_content_lines:

        is_highlight = highlight_comp.search(message)
        
        if is_highlight:
            is_message = message_comp.search(message)
            
            if is_message:
                msg_groups = is_message.groupdict()
                msg_groups['sender'] = msg_groups['sender_no'] if msg_groups['sender'] is None else msg_groups['sender']
                msg_groups.pop('sender_no')
                chat_list.append(msg_groups)

        else:
            if chat_list:
                chat_list[-1]["message"] += f" {message}"

    df = pd.DataFrame(chat_list)
    return df.groupby(['date', 'time', 'sender'], as_index=False).agg({'message': lambda x: ' '.join(x)})
    
   


    