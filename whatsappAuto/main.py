import re
import os
import yaml
import hashlib
import time
import traceback
import pandas as pd
from datetime import datetime
from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException


class XPATHS(str,Enum):

    START_PANE = '//*[@id="app"]/div/div/div[3]/div/div[5]/section'
    SEARCH_BAR = '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p'
    GROUP_BUTTON = '//*[@id="group-filter"]/div/div/div/span/span/span'
    SEARCH_RESULT_ROWS= 'div[role="row"]'
    CHATBOX = '//*[@id="main"]/div[2]'
    CHAT_PANE_SELECTOR = 'div[data-scrolltracepolicy="wa.web.conversation.messages"]'
    CHAT_DIV='.//div[@role="row"]'
    MESSAGE_IN='.//div[starts-with(@class,"message-in")]'
    SENDER_SPAN='.//*[@role]//span'
    MESSAGE_TEXT= './/*[@data-pre-plain-text]'


class whatsappAuto:
    
    def __init__(self,
                 group_title : str,
                 till_date : datetime = datetime.now().today().date())-> None:
        

        options = webdriver.chrome.options.Options()
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.driver.set_script_timeout(90)

        self.group_title = group_title
        self.till_date = till_date

        self.scroll_pause : int =2.5
        self.chats : pd.DataFrame = pd.DataFrame()

        self.date_comp = re.compile(r"(\d{2}:\d{2})")
        self.time_comp = re.compile(r"(\d{1,2}\/\d{1,2}\/\d{2,4})")
        self.ref_user = lambda x: x.split(' ',2)[-1]
 
    def run(self):

        if not self.whatsapp_is_loaded():
            print("You've quit.")
            self.driver.quit()
            return
        
        if not self.group_found():
            print("You've quit.")
            self.driver.quit()
            return 

        
        finished = False
        chat_list = []
        seen_hashes = set()
        print("Group found! Starting scrape...")
        while True:
        
            # TODO : to be refined
            chat_divs = self.chatbox_element.find_elements(By.XPATH, XPATHS.CHAT_DIV)
            for section in chat_divs:
                
                message_in = section.find_elements(By.XPATH,XPATHS.MESSAGE_IN)
                for msg in message_in:
                    try:
                        sender_element = msg.find_elements(By.XPATH, XPATHS.SENDER_SPAN)
                        if sender_element:
                            sender_info = sender_element[0].text.strip()

                        message_info = msg.find_element(By.XPATH, XPATHS.MESSAGE_TEXT)
                        metadata = message_info.get_attribute("data-pre-plain-text")
                        if not metadata: continue
                        
                        msg_date = self.date_comp.search(metadata).group()
                        msg_time = self.time_comp.search(metadata).group()
                        msg_datetime = pd.to_datetime(msg_date + ' ' + msg_time)
                        if msg_datetime.date() < self.till_date:
                            finished = True
                            break    
                        print(metadata,sender_info,message_info.text.strip())

                        msg_text = message_info.text.strip()
                        unique_id = hashlib.md5((metadata + msg_text).encode()).hexdigest()

                        if unique_id not in seen_hashes:
                            chat_list.append({
                                "sender": self.ref_user(metadata),
                                "sender_2":sender_info,
                                "datetime": msg_datetime,
                                "message": msg_text
                            })
                            seen_hashes.add(unique_id)

                       
                    except Exception as e:
                        print(traceback.format_exc(),e)
                        continue

                if finished: break

            if not finished:
                self.driver.execute_script("arguments[0].scrollTop = 0;", self.chatbox_element)
                time.sleep(self.scroll_pause)
        
            return pd.DataFrame(chat_list)
        
    
    def whatsapp_is_loaded(self):

        print("Loading WhatsApp...", end="\r")
        self.driver.get('https://web.whatsapp.com/')

        logged_in, wait_time = False, 20
        while not logged_in:

            logged_in = self.user_is_logged_in(wait_time)

            if not logged_in:
                print(f"Error: WhatsApp did not load within {wait_time} seconds. Make sure you are logged in and let's try again.")

                is_valid_response = False
                while not is_valid_response:
                    err_response = input("Proceed (y/n)? ")

                    if err_response.strip().lower() in {'y', 'yes'}:
                        is_valid_response = True
                        continue
                    elif err_response.strip().lower() in {'n', 'no'}:
                        is_valid_response = True
                        return False
                    else:
                        is_valid_response = False
                        continue

        print("Success! WhatsApp finished loading and is ready.")
        return True
    

    def user_is_logged_in(self,wait_time):

        try:
            chat_pane = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, XPATHS.START_PANE)))
            return True
        except TimeoutException:
            return False

    

    def group_found(self) -> bool:

        print('Searching Group ...')

        try:
            group_button = self.driver.find_element(By.XPATH,XPATHS.GROUP_BUTTON)
            group_button.click()

            search_bar_element = self.driver.find_element(By.XPATH, XPATHS.SEARCH_BAR)
            search_bar_element.send_keys(self.group_title)
            time.sleep(5)

            first_row = self.driver.find_elements(By.CSS_SELECTOR, XPATHS.SEARCH_RESULT_ROWS)[1]
            first_row.click()

            self.chatbox_element = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, XPATHS.CHATBOX)))
            self.chatbox_element.click()

            self.chatbox_pane = self.driver.find_element(By.CSS_SELECTOR, XPATHS.CHAT_PANE_SELECTOR)

            print(self.group_title, ' found !')
            return True
        
        except:
            print(f"Error occured while searching group : {traceback.format_exc()}")
            return False




if __name__ == "__main__":

    sel = whatsappAuto(group_title="Demo")
    print(sel.run())