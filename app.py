from flask import Flask, request, redirect, url_for, send_file, render_template
import pandas as pd
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

def login_instagram(driver, username, password):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)  # Wait for the login page to load

    try:
        # Enter username
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys(username)

        # Enter password
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)

        # Click login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()

        time.sleep(5)  # Wait for the main page to load
        print("Logged in successfully")
    except Exception as e:
        print(f"Error during login: {e}")

def logout_instagram(driver):
    try:
        # Go to the profile page
        profile_button = driver.find_element(By.XPATH, "(//div[contains(@class,'x1n2onr6 x6s0dn4 x78zum5')])[11]")
        profile_button.click()
        time.sleep(2)

        # Click on settings
        settings_button = driver.find_element(By.XPATH, "(//div[contains(@class,'x1q0g3np x2lah0s')])")
        settings_button.click()
        time.sleep(2)

        # Click on Log Out
        logout_button = driver.find_element(By.XPATH, "//button[text()='Log Out']")
        logout_button.click()
        time.sleep(2)
        print("Logged out successfully")
    except Exception as e:
        print(f"Error during logout: {e}")

def get_instagram_video_data(driver, video_url):
    driver.get(video_url)
    time.sleep(5)  # Wait for the page to load

    try:
        upload_date = driver.find_element(By.CSS_SELECTOR, "time").get_attribute("datetime")
    except Exception as e:
        upload_date = None
        print(f"Error extracting upload date: {e}")

    try:
        username = driver.find_element(By.XPATH, "(//span[contains(@class, 'xt0psk2')])[1]").text
    except Exception as e:
        username = None
        print(f"Error extracting username: {e}")

    try:
        likes = driver.find_element(By.XPATH, "(//a//span[contains(@class, 'html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs')])[1]").text
    except Exception as e:
        likes = None
        print(f"Error extracting likes: {e}")

    pattern = r"/reel/([^/?]+)"
    match = re.search(pattern, video_url)
    if match:
        reel_id = match.group(1)
    else:
        reel_id = None
        print("Reel ID not found in the URL.")

    try:
        username_click = driver.find_element(By.XPATH, "(//div[contains(@class,'xyinxu5 x1pi30zi')]//a)[1]")
        username_click.click()
        time.sleep(5)  # Wait for the profile page to load
        driver.execute_script('window.scrollBy(0, 1000)')

        reels_tab = driver.find_element(By.XPATH, "//span[contains(@class, 'x972fbf') and contains(@class, 'xcfux6l') and contains(@class, 'x1qhh985') and contains(text(), 'Reels')]")
        reels_tab.click()
        time.sleep(5)  # Wait for the reels tab to load

        views_element = None
        scroll_attempts = 0
        while not views_element and scroll_attempts < 10:
            try:
                driver.execute_script('window.scrollBy(0, 200)')
                views_element = driver.find_element(By.CSS_SELECTOR, f'a[href="/reel/{reel_id}/"] div._aajy span.html-span')
            except Exception as e:
                views_element = None
                scroll_attempts += 1
                time.sleep(2)

        if views_element:
            views = views_element.text
        else:
            views = 0
            print("Views element not found")

    except Exception as e:
        views = 0
        print(f"Error navigating to profile and reels or extracting views: {e}")

    return upload_date, username, likes, views

def read_excel(file_path):
    df = pd.read_excel(file_path)
    return df

def write_to_excel(df, output_file):
    df.to_excel(output_file, index=False)

def process_instagram_data(input_file, output_file, login_username, login_password):
    df = read_excel(input_file)
    dates = []
    usernames = []
    likes = []
    views = []

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    login_instagram(driver, login_username, login_password)

    for url in df['Video URL']:
        try:
            date, username, like_count, view_count = get_instagram_video_data(driver, url)
            dates.append(date)
            usernames.append(username)
            likes.append(like_count)
            views.append(view_count)
        except Exception as e:
            dates.append(None)
            usernames.append(None)
            likes.append(None)
            views.append(None)
            print(f"Error processing {url}: {e}")

    logout_instagram(driver)
    driver.quit()

    df['Upload Date'] = dates
    df['User Name'] = usernames
    df['Likes'] = likes
    df['Views'] = views

    write_to_excel(df, output_file)
    print("Data successfully written to output file.")

@app.route('/')
def upload_file():
    return render_template('upload.html')

@app.route('/uploader', methods=['GET', 'POST'])
def upload_file_route():
    if request.method == 'POST':
        f = request.files['file']
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
        f.save(input_path)

        output_filename = f'processed_{f.filename}'
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        if not os.path.exists(PROCESSED_FOLDER):
            os.makedirs(PROCESSED_FOLDER)

        login_username = 'thiru_thej'  # Replace with your Instagram username
        login_password = 'Narasimha@1999'  # Replace with your Instagram password
        process_instagram_data(input_path, output_path, login_username, login_password)

        return redirect(url_for('download_file', filename=output_filename))

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['PROCESSED_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
