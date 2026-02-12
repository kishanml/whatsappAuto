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
    SEARCH_BAR = '//*[@id="side"]/div[1]/div/div/div/div/div[1]'
    GROUP_BUTTON = '//*[@id="group-filter"]/div/div/div/span/span/span'
    SEARCH_RESULT_ROWS= 'div[role="row"]'
    CHATBOX = '//*[@id="main"]'
    CHAT_PANE_SELECTOR = 'div[data-scrolltracepolicy="wa.web.conversation.messages"]'
    CHAT_DIV='.//div[@role="row"]'
    MESSAGE_IN='.//div[starts-with(@class,"message-in")]'
    SENDER_SPAN='.//*[@role]//span'
    MESSAGE_TEXT= './/*[@data-pre-plain-text]'


class whatsappAuto:
    
    def __init__(self)-> None:
        

        self.driver = webdriver.Chrome()

        self.scroll_pause : int =2.5
        self.time_comp = re.compile(r"(\d{2}:\d{2})")
        self.date_comp = re.compile(r"(\d{1,2}\/\d{1,2}\/\d{2,4})")
        self.ref_user = lambda x: x.split(' ',2)[-1]
    
    def get_chats(self, group_title ,till_date, count_limit : int = 50):

        if not self.whatsapp_is_loaded():
            print("You've quit.")
            self.driver.quit()
            return
        
        if not self.group_found(group_title):
            print("You've quit.")
            self.driver.quit()
            return 

        
        print("Group found! Starting scrape...")
        finished = False
        data = []
        seen = set()
        count = 0
        while True:
        
            try:
                pane = self.driver.find_element(By.CSS_SELECTOR, XPATHS.CHAT_PANE_SELECTOR)        
                last_height = self.driver.execute_script("return arguments[0].scrollHeight", pane)

                message_ins = self.driver.find_elements(By.XPATH, XPATHS.CHATBOX)
                for msg in message_ins:
                    try:
                        message_info = msg.find_elements(By.XPATH, XPATHS.MESSAGE_TEXT)
                        for x in message_info:
                            msg_date, msg_time = None, None
                            metadata = x.get_attribute("data-pre-plain-text")
                            if metadata is not None:
                                is_date_exists = self.date_comp.search(metadata)
                                if is_date_exists:
                                    msg_date = is_date_exists.group()
                                    
                                is_time_exists = self.time_comp.search(metadata)
                                if is_time_exists:
                                    msg_time = is_time_exists.group()
                                if msg_date and msg_time:
                                    msg_datetime = pd.to_datetime(msg_date+' '+msg_time,format="%m/%d/%Y %H:%M")
                                    # print(msg_datetime,msg_datetime.month)
                                    if msg_datetime.normalize() >= till_date.normalize():
                                        msg_text = str(x.text.split('\n')[-1])
                                        unique_id = hashlib.md5((str(msg_datetime) + msg_text).encode()).hexdigest()
                                        if unique_id not in seen:
                                            data.append({'date':msg_date,'time':msg_time,'sender':self.ref_user(metadata),'message':msg_text})
                                            seen.add(unique_id)
                                    elif msg_datetime < till_date.normalize():
                                        finished = True


                    except Exception as e:
                        print(e)

                    self.driver.execute_script("arguments[0].scrollTop = 0;", pane)            
                    time.sleep(self.scroll_pause)

                new_height = self.driver.execute_script("return arguments[0].scrollHeight", pane)
                # print('->',finished,count_limit)
                # if new_height == last_height or finished or count_limit==50:

                if finished or count==count_limit:
                    print("No more messages to load or reached the sync limit.")
                    break
                    
                # last_height = new_height
                # print(f"Loaded older messages. New height: {new_height}")
                count+=1

            except Exception as exc:
                print(f'Error occured while scraping : {traceback.format_exc()}')
                break

        self.driver.quit()
        return pd.DataFrame(data).sort_values(by=['date','time']).reset_index(drop=True) if data else None
        
    
    def whatsapp_is_loaded(self):

        print("Loading WhatsApp...", end="\r")
        self.driver.get('https://web.whatsapp.com/')

        logged_in, wait_time = False, 30
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

    

    def group_found(self, group_title) -> bool:

        print('Searching Group ...')

        try:
            group_button = self.driver.find_element(By.XPATH,XPATHS.GROUP_BUTTON)
            group_button.click()

            search_bar_element = self.driver.find_element(By.XPATH, XPATHS.SEARCH_BAR)
            search_bar_element.send_keys(group_title)
            time.sleep(5)

            first_row = self.driver.find_elements(By.CSS_SELECTOR, XPATHS.SEARCH_RESULT_ROWS)[1]
            first_row.click()

            self.chatbox_element = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, XPATHS.CHATBOX)))
            self.chatbox_element.click()

            self.chatbox_pane = self.driver.find_element(By.CSS_SELECTOR, XPATHS.CHAT_PANE_SELECTOR)

            print(group_title, ' found !')
            return True
        
        except:
            print(f"Error occured while searching group : {traceback.format_exc()}")
            return False


