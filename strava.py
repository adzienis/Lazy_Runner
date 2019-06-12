import http.server
import requests
import json
import os
import pickle

from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains

import configparser

CODE= ""

RECORDS = {"ACCESS_TOKEN": "", "REFRESH_TOKEN": "", "EXPIRES_AT": "", "uploaded_ids": {} }

driver = None

CONFIG = None
CUR_PATH = os.path.dirname(os.path.realpath(__file__))

class myHandler(http.server.BaseHTTPRequestHandler):
    #Handler for the GET requests
    def do_GET(self):
        global CODE
        CODE = self.requestline.split(' ')[1].split('&')[1].split('=')[1]
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        # Send the html message
        self.wfile.write("All good, just exit the tab!".encode())
        return

def log_into_site():
    global driver
    options = Options()
    options.headless = True
    driver = webdriver.Firefox()
    driver.get("http://www.logarun.com/logon.aspx")

    driver.find_element_by_id("LoginName").send_keys(CONFIG["DEFAULT"]["USERNAME"])
    driver.find_element_by_id("Password").send_keys(CONFIG["DEFAULT"]["PASSWORD"])

    driver.find_element_by_id("LoginNow").click()
    return

def authenticate():
    server = http.server.HTTPServer(('', CONFIG["DEFAULT"].getint("PORT")), myHandler)
    URL=("https://www.strava.com/oauth/authorize?client_id={0}&"
            "redirect_uri={1}&"
            "approval_prompt=auto&"
            "response_type={2}&"
            "scope={3}").format(CONFIG["STRAVA"]["CLIENT_ID"], CONFIG["STRAVA"]["REDIRECT_URI"], CONFIG["STRAVA"]["RESPONSE_TYPE"], CONFIG["STRAVA"]["SCOPE"])

    print("Paste this URL: " + URL)

    server.handle_request()

    resp = requests.post("https://www.strava.com/oauth/token", params={"client_id":CONFIG["STRAVA"]["CLIENT_ID"], "client_secret":CONFIG["STRAVA"]["CLIENT_SECRET"], "code":CODE, "grant_type": "authorization_code" })

    json_out = resp.json()

    return json_out["access_token"], json_out["refresh_token"], json_out["expires_at"]

def refresh_token():
    URL = "https://www.strava.com/oauth/token"

    resp = requests.post(URL, params={ "client_id": CONFIG["STRAVA"]["CLIENT_ID"],
        "client_secret": CONFIG["STRAVA"]["CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": RECORDS["REFRESH_TOKEN"]})

    json_out = resp.json()

    RECORDS["access_token"] = json_out["access_token"]


def upload_run(date, distance):
    driver.get('http://www.logarun.com/Edit.aspx?username={0}&date={1}/{2}/{3}'.format(CONFIG["DEFAULT"]["USERNAME"], date["month"], date["day"], date["year"]))

    dist_elem = driver.find_element_by_xpath('//*[@datatype="Distance"]')
    ActionChains(driver).click(dist_elem).key_down(Keys.CONTROL).key_down("A").key_up("A").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
    dist_elem.send_keys(distance)

    title_elem = driver.find_element_by_id("ctl00_Content_c_dayTitle_c_title")
    ActionChains(driver).click(title_elem).key_down(Keys.CONTROL).key_down("A").key_up("A").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
    title_elem.send_keys("{0}/{1}/{2}".format(date["month"], date["day"], date["year"]))

    driver.find_element_by_xpath('//*[@value="Save"]').click()

    return

def check_for_data():
    new_dict = defaultdict(list)
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities", headers={'Authorization': 'access_token ' + RECORDS["ACCESS_TOKEN"]}).json()

    for activity in resp:
        full_date = activity["start_date_local"].split("T")[0]
        start_date_local = full_date.split("-")
        date = {"year": start_date_local[0], "month": start_date_local[1], "day": start_date_local[2]}
        upload_id = activity["upload_id"]
        distance_mi = float(activity["distance"])/1609.344

        new_dict[full_date].append({"date": date, "upload_id":upload_id, "distance_mi": distance_mi })

    return new_dict


def main():
    global driver
    global RECORDS

    try:
        if not os.path.exists(CUR_PATH + "/records.pkl"):
            print("First time setting up: ")
            RECORDS["ACCESS_TOKEN"], RECORDS["REFRESH_TOKEN"], RECORDS["EXPIRES_AT"] = authenticate()

            with open(CUR_PATH + "/records.pkl", "wb") as f:
                pickle.dump(RECORDS, f)

        with open(CUR_PATH + "/records.pkl", "rb") as f:
            RECORDS = pickle.load(f)

        refresh_token()

        new_dict = check_for_data()

        log_into_site()

        for k in list(new_dict):

            temp = k.split("-")

            date = {"year": temp[0], "month": temp[1], "day": temp[2]}
            uploaded_entry = {"date": k, "ids": [], "distance": 0.0}


            if k in RECORDS["uploaded_ids"]:
                continue

            for inner_entry in list(new_dict[k]):
                uploaded_entry["distance"] += inner_entry["distance_mi"]

            RECORDS["uploaded_ids"][k] = None

            try:
                upload_run(date, str(uploaded_entry["distance"]))
                print("Uploaded: " + str(uploaded_entry["date"]))
            except:
                print("Failed to upload: " + uploaded_entry["date"])

        with open(CUR_PATH + "/records.pkl", "wb") as f:
            pickle.dump(RECORDS, f)
    except KeyboardInterrupt:
        print('shutting down the web server')

    if driver:
        driver.quit()

    return


if __name__ == "__main__":
    CONFIG = configparser.ConfigParser()
    CONFIG.read("config.cfg")

    main()

