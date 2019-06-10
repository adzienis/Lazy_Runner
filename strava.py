import http.server
import socketserver
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options


PORT_NUMBER=5000

CLIENT_ID="***REMOVED***"
CLIENT_SECRET="***REMOVED***"
CODE= ""
GRANT_TYPE="authorization_code"

REDIRECT_URI="http://localhost:5000"
RESPONSE_TYPE="code"
SCOPE="activity:read_all"

URL="https://www.strava.com/oauth/authorize?client_id={0}&redirect_uri={1}&approval_prompt=auto&response_type={2}&scope={3}".format(CLIENT_ID, REDIRECT_URI, RESPONSE_TYPE, SCOPE)

ACCESS_TOKEN=""
REFRESH_TOKEN=""
EXPIRES_AT=""

RECORDS = {"ACCESS_TOKEN": "", "REFRESH_TOKEN": "", "EXPIRES_AT": "", "uploaded_ids": {} }

def check_for_data():
        for activity in resp:
            start_date_local = activity["start_date_local"].split("T")[0]
            upload_id = activity["upload_id"]
            distance = float(activity["distance"])

            if upload_id in RECORDS["uploaded_ids"]:
                continue
            else:
                RECORDS["uploaded_ids"][upload_id] = None
                print(distance)


def authenticate():
    try:
            temp_date = {"month":"06", "day":"10", "year":"2016"}

            upload_run(temp_date, "1")

            while True:
                pass

            server = http.server.HTTPServer(('', PORT_NUMBER), myHandler)

            print("Paste this URL: " + URL)

            server.handle_request()
            print("we got the token:" + CODE)

            resp = requests.post("https://www.strava.com/oauth/token", params={"client_id":CLIENT_ID, "client_secret":CLIENT_SECRET, "code":CODE, "grant_type":GRANT_TYPE}).json()

            RECORDS["ACCESS_TOKEN"] = resp["access_token"]
            RECORDS["REFRESH_TOKEN"] = resp["refresh_token"]
            RECORDS["EXPIRES_AT"] = resp["expires_at"]

            ACCESS_TOKEN = resp["access_token"]
            REFRESH_TOKEN = resp["refresh_token"]
            EXPIRES_AT = resp["expires_at"]

            resp = requests.get("https://www.strava.com/api/v3/athlete/activities", headers={'Authorization': 'access_token ' + ACCESS_TOKEN}).json()



    except KeyboardInterrupt:
            print('shutting down the web server')
            server.socket.close()

def upload_run(date, distance):
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.get("http://www.logarun.com/logon.aspx")
    username = "***REMOVED***"
    password = "***REMOVED***"

    driver.find_element_by_id("LoginName").send_keys(username)
    driver.find_element_by_id("Password").send_keys(password)

    driver.find_element_by_id("LoginNow").click()

    driver.get('http://www.logarun.com/Edit.aspx?username={0}&date="{1}/{2}/{3}"'.format(username, date["month"], date["day"], date["year"]))

    dist_elem = driver.find_element_by_xpath('//*[@datatype="Distance"]')
    dist_elem.click()
    dist_elem.send_keys([Keys.BACKSPACE for i in range(4)])
    dist_elem.send_keys(distance)

    title_elem = driver.find_element_by_id("ctl00_Content_c_dayTitle_c_title")
    title_elem.click()
    title_elem.send_keys("{0}/{1}/{2}".format(date["month"], date["day"], date["year"]))

    driver.find_element_by_xpath('//*[@value="Save"]').click()


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


def main():


if __name__ == "__main__":
    main()

