import http.server
import requests
import json
import os
import pickle
from random_word import RandomWords

from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains

import configparser

CODE = ""

RECORDS = {"ACCESS_TOKEN": "", "REFRESH_TOKEN": "",
           "EXPIRES_AT": "", "uploaded_ids": {}}

driver = None

CONFIG = None
CUR_PATH = os.path.dirname(os.path.realpath(__file__))

"""
Basic http server to handle retrieving authentication code when the
user logs in give access. Simply updates CODE above
"""


class myHandler(http.server.BaseHTTPRequestHandler):
    # Handler for the GET requests
    def do_GET(self):
        global CODE
        CODE = self.requestline.split(' ')[1].split('&')[1].split('=')[1]
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        # Send the html message
        self.wfile.write("All good, just exit the tab!".encode())
        return


"""
Handles logging into the Logarun website. Is done once
upon every invocation of strava.py. Also sets up the driver,
and makes it headless by default.
"""


def log_into_site():
    global driver
    options = Options()
    options.headless = False
    driver = webdriver.Firefox(options=options)
    driver.get("http://www.logarun.com/logon.aspx")

    driver.find_element_by_id("LoginName").send_keys(
        CONFIG["LOGARUN"]["USERNAME"])
    driver.find_element_by_id("Password").send_keys(
        CONFIG["LOGARUN"]["PASSWORD"])

    driver.find_element_by_id("LoginNow").click()
    return


"""
Handles initial authentication to use the Strava API. By default, our scope is to read
all information, which is necessary even for public activities, as I've found.
Quickly runs a really lightweight http server to handle one request, which is when
the user is redirected to localhost after clicking to accept. Makes a POST to
receive the access_token and refresh_tokens.
"""


def authenticate():
    server = http.server.HTTPServer(
        ('', CONFIG["LOGARUN"].getint("PORT")), myHandler)
    URL = ("https://www.strava.com/oauth/authorize?client_id={0}&"
           "redirect_uri={1}&"
           "approval_prompt=auto&"
           "response_type=code&"
           "scope={2}").format(CONFIG["STRAVA"]["CLIENT_ID"], CONFIG["STRAVA"]["REDIRECT_URI"], CONFIG["STRAVA"]["SCOPE"])

    print("Paste this URL: " + URL)

    server.handle_request()

    resp = requests.post("https://www.strava.com/oauth/token", params={
                         "client_id": CONFIG["STRAVA"]["CLIENT_ID"], "client_secret": CONFIG["STRAVA"]["CLIENT_SECRET"], "code": CODE, "grant_type": "authorization_code"})

    json_out = resp.json()

    return json_out["access_token"], json_out["refresh_token"], json_out["expires_at"]


"""
The access_token expires every some seconds, so we just refresh the token by default every time we sync up.
Just makes a POST to an endpoint and receives the tokens. Straightforward
"""


def refresh_token():
    URL = "https://www.strava.com/oauth/token"

    resp = requests.post(URL, params={"client_id": CONFIG["STRAVA"]["CLIENT_ID"],
                                      "client_secret": CONFIG["STRAVA"]["CLIENT_SECRET"],
                                      "grant_type": "refresh_token",
                                      "refresh_token": RECORDS["REFRESH_TOKEN"]})

    json_out = resp.json()

    RECORDS["access_token"] = json_out["access_token"]


"""
Uploads the run for a particular date. Sets the title to the date of the run. If a run already exists posted, it will fail and
throw an exception, which is handled in main.

@param date:str Dictionary consisting of "year", "month", and "day". Supposed to resemble a date as follows: MM/DD/YYYY
@param distance:str String encoding of the mileage for a particular date. In miles.
@see main
"""


def upload_run(date, distance):
    driver.get('http://www.logarun.com/Edit.aspx?username={0}&date={1}/{2}/{3}'.format(
        CONFIG["LOGARUN"]["USERNAME"], date["month"], date["day"], date["year"]))

    dist_elem = driver.find_element_by_xpath('//*[@datatype="Distance"]')
    ActionChains(driver).click(dist_elem).key_down(Keys.CONTROL).key_down(
        "A").key_up("A").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
    dist_elem.send_keys(distance)

    title_elem = driver.find_element_by_id("ctl00_Content_c_dayTitle_c_title")
    ActionChains(driver).click(title_elem).key_down(Keys.CONTROL).key_down(
        "A").key_up("A").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
    title_elem.send_keys(
        "{0}/{1}/{2}".format(date["month"], date["day"], date["year"]))

    desc_elem = driver.find_element_by_xpath(
        '//*[@id="ctl00_Content_c_note_c_note"]')
    desc_elem.send_keys("Logged by Lazy_Runner")
    # title_elem.send_keys(random_title)

    driver.find_element_by_xpath('//*[@id="ctl00_Content_c_save"]').click()

    return


"""
Queries Strava API for a list of all activities. Returns a dictionary in the form of a multi-map so we can handle
multiple activities per date. The distance of each run is by default in meters, so we convert to miles. We
also have to split the date passed back, which is in the format YYYY-MM-DD.
"""


def check_for_data():
    new_dict = defaultdict(list)
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities",
                        headers={'Authorization': 'access_token ' + RECORDS["ACCESS_TOKEN"]}).json()

    for activity in resp:
        full_date = activity["start_date_local"].split("T")[0]
        start_date_local = full_date.split("-")
        date = {
            "year": start_date_local[0], "month": start_date_local[1], "day": start_date_local[2]}
        upload_id = activity["upload_id"]
        distance_mi = float(activity["distance"])/1609.344

        new_dict[full_date].append(
            {"date": date, "upload_id": upload_id, "distance_mi": distance_mi})

    return new_dict


"""
Where the magic happens. We have the all the authentication crap stored as a pickled file,
and we load/create it if it doesn't exist. Might just move this all into the config file. Automatically
refreshes the token upon each invocation, checks the data, logs into Logarun, and uploads the data.
Upon each invocation of this script, we record all of the dates that we uploaded to Logarun, and skip
those which we have already uploaded. It's quicker. Dumps everything back into the pickled file
"""


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
            except Exception as e:
                print("Failed to upload: " + uploaded_entry["date"])
                print(e)

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
