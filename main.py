import json
import shutil
import traceback
import numpy as np
import re
import pandas as pd
from pathlib import Path
from client import LLMClient, prompt
from numpy.typing import NDArray
from whatsappAuto import whatsappAuto
from exported_chats_into_dataframe import create_dataframe_from_chats


def _process_group_to_excel(group_path: Path, database_dir: Path) -> bool:
    try:

        source_file = next(group_path.glob('*'), None)
        
        if not source_file:
            return False

        excel_path = database_dir/f"{group_path.name}.xlsx"
        
        if not excel_path.exists():
            df = create_dataframe_from_chats(chat_input_path=source_file)
            df.to_excel(excel_path, index=False)
        return True,excel_path.absolute()
    except Exception:
        print(f"Error processing group {group_path.name}: {traceback.format_exc()}")
        return False, None

def sync_chat_database(chat_exports_dir: str = "chatExports", 
                         database_dir: str = "database", 
                         refresh_all: bool = False):
 
    chat_dir = Path(chat_exports_dir)
    db_dir = Path(database_dir)

    try:
        if refresh_all and db_dir.exists():
            shutil.rmtree(db_dir)
        db_dir.mkdir(parents=True, exist_ok=True)

        targets = [g for g in chat_dir.glob('*') if not g.name.startswith('.')]
        
        results = [_process_group_to_excel(grp, db_dir) for grp in targets]
        return all(results)
    
    except Exception as e:
        print(f"Critical error: {e}")
        return False

def sync_single_chat(group_name: str, 
                     chat_exports_dir: str = "chatExports", 
                     database_dir: str = "database"):
    db_dir = Path(database_dir)
    group_path = Path(chat_exports_dir) / group_name

    if not group_path.exists():
        print(f"Source group {group_name} not found.")
        return False

    db_dir.mkdir(parents=True, exist_ok=True)
    return _process_group_to_excel(group_path, db_dir)


def get_dict_from_json(res):
    flag = re.search("```json", res)
    if flag:
        start = flag.span()[1]
        stop = re.search("```(?!json)", res).span()[0]
        res = res[start: stop]
        last_comma = re.search(",(?=[\n]*})", res)
        if last_comma is not None:
            res = res[:last_comma.span()[0]] + res[last_comma.span()[1]:]
        # print()
        # return json.loads(res.strip())
        return re.sub(r"[^\x20-\x7E]", "", res.strip())
    else:
        return res


async def generate_classification(messages : NDArray, batch_size : int = 10):

    batches = [messages[i:i + batch_size] for i in range(0, len(messages), batch_size)]
    outputs = []
    client = LLMClient()
    for pack in batches:
        response = None
        messages = [{"role": "user","content": prompt(list(enumerate(pack,1)))}]
        async for event in client.chat_completion(messages,False):
            response = event
        # print(response.text_delta.content)
        outputs.extend([ele['is_concern'] for ele in json.loads(get_dict_from_json(response.text_delta.content))['result']])
    return outputs
