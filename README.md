## Setup

```
# create a Python virtual environment
python3 -m venv venv
# activate the virutal environment
source venv/bin/activate
# install Python libraries
pip3 install -r requirements.txt
# create a configuration file
printf "[pandora]\nusername=YOUR_USERNAME\npassword=YOUR_PASSWORD\n" > conf.ini
# run the script!
python3 main.py
```
