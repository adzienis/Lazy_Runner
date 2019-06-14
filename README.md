# Required Packages
Tested on Python 3.4.3. Only external packages required are Selenium and Requests. So install them:
```
pip3 install selenium
pip3 install requests
pip3 install Random-Word
```

```
Or run pip3 install -r requirements.txt
```

# Configuration File
First setup your own app https://developers.strava.com/ and smash that "Create & Manage Your App".
None of the settings honestly matter. Just put random stuff for the settings.
This is an application restricted only to you, and no way in hell am I doing anything more
complicated for Logarun of all sites:

<img src="https://i.imgur.com/nCqUMmV.png" width="700"/>

Once you're done with that, you can just copy over the settings from https://www.strava.com/settings/api into the config file.
Rename "default.cfg" as "config.cfg" once you're done.

# Execution
Just execute "strava.py" using Python, and everything else should be straightforward. Headless mode is on by default
for navigating Logarun.
