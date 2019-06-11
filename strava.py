import http.server
import socketserver
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

import os
import pickle
from selenium.webdriver.common.action_chains import ActionChains

PORT_NUMBER=5000

CLIENT_ID="***REMOVED***"
CLIENT_SECRET="***REMOVED***"
CODE= ""
GRANT_TYPE="authorization_code"

REDIRECT_URI="http://localhost:5000"
RESPONSE_TYPE="code"
SCOPE="activity:read_all"

URL="https://www.strava.com/oauth/authorize?client_id={0}&redirect_uri={1}&approval_prompt=auto&response_type={2}&scope={3}".format(CLIENT_ID, REDIRECT_URI, RESPONSE_TYPE, SCOPE)

RECORDS = {"ACCESS_TOKEN": "", "REFRESH_TOKEN": "", "EXPIRES_AT": "", "uploaded_ids": {} }

driver = None

USERNAME = "***REMOVED***"
PASSWORD = "***REMOVED***"

class myHandler(http.server.BaseHTTPRequestHandler):
    #Handler for the GET requests
    def do_GET(self):
        global CODE
        CODE = self.requestline.split(' ')[1].split('&')[1].split('=')[1]
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        # Send the html message
        self.wfile.write("Hello World !".encode())
        return

def log_into_site():
    global driver
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.get("http://www.logarun.com/logon.aspx")

    driver.find_element_by_id("LoginName").send_keys(USERNAME)
    driver.find_element_by_id("Password").send_keys(PASSWORD)

    driver.find_element_by_id("LoginNow").click()


def authenticate():
    server = http.server.HTTPServer(('', PORT_NUMBER), myHandler)

    print("Paste this URL: " + URL)

    server.handle_request()

    resp = requests.post("https://www.strava.com/oauth/token", params={"client_id":CLIENT_ID, "client_secret":CLIENT_SECRET, "code":CODE, "grant_type":GRANT_TYPE}).json()

    return resp["access_token"], resp["refresh_token"], resp["expires_at"]


def upload_run(date, distance):
    driver.get('http://www.logarun.com/Edit.aspx?username={0}&date={1}/{2}/{3}'.format(USERNAME, date["month"], date["day"], date["year"]))

    dist_elem = driver.find_element_by_xpath('//*[@datatype="Distance"]')
    ActionChains(driver).click(dist_elem).key_down(Keys.CONTROL).key_down("A").key_up("A").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
    dist_elem.send_keys(distance)

    title_elem = driver.find_element_by_id("ctl00_Content_c_dayTitle_c_title")
    ActionChains(driver).click(title_elem).key_down(Keys.CONTROL).key_down("A").key_up("A").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
    title_elem.send_keys("{0}/{1}/{2}".format(date["month"], date["day"], date["year"]))

    driver.find_element_by_xpath('//*[@value="Save"]').click()

def check_for_data():
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities", headers={'Authorization': 'access_token ' + RECORDS["ACCESS_TOKEN"]}).json()

    log_into_site()

    for activity in resp:
        start_date_local = activity["start_date_local"].split("T")[0].split("-")
        date = {"year": start_date_local[0], "month": start_date_local[1], "day": start_date_local[2]}
        upload_id = activity["upload_id"]
        distance_mi = float(activity["distance"])

        if upload_id in RECORDS["uploaded_ids"]:
            continue
        else:
            try:
                upload_run(date, str(distance_mi))
                print("Uploaded: " + str(upload_id))
            except:
                print("Failed to upload: " + str(upload_id))

            RECORDS["uploaded_ids"][upload_id] = None


def main():
    global driver
    global RECORDS
    cur_path = os.path.dirname(os.path.realpath(__file__))
    try:
        if not os.path.exists(cur_path + "/records.pkl"):
            print("First time setting up: ")
            RECORDS["ACCESS_TOKEN"], RECORDS["REFRESH_TOKEN"], RECORDS["EXPIRES_AT"] = authenticate()

            with open(cur_path + "/records.pkl", "wb") as f:
                pickle.dump(RECORDS, f)

        with open(cur_path + "/records.pkl", "rb") as f:
            RECORDS = pickle.load(f)

        check_for_data()

        with open(cur_path + "/records.pkl", "wb") as f:
            pickle.dump(RECORDS, f)
    except KeyboardInterrupt:
        print('shutting down the web server')

    if driver:
        driver.quit()


if __name__ == "__main__":
    main()

