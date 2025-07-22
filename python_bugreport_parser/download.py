from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import os

from python_bugreport_parser.bugreport.bugreport_all import Log284


def download_log(url):
    user_data_dir = "browser_cache"
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
        )

        page = browser.new_page()
        # Listen to all responses
        redirect_chain = []

        def handle_response(response):
            status = response.status
            if 300 <= status < 400:  # Redirect status codes
                redirect_chain.append({"url": response.url, "status": status})
            print(f"Response: {response.url} - Status: {status}")

        page.on("response", handle_response)
        page.goto(url, wait_until="load")
        print("wait to scan qrcode")

        file_name = ""
        try:
            with page.expect_download(timeout=15000) as download_info:
                pass
            download = download_info.value
            print(download.suggested_filename)
            print(download.path())
            print("download finished")
            download.save_as(download.suggested_filename)
            file_name = download.suggested_filename
        except PlaywrightTimeoutError as e:
            # Catch TimeoutError from playwright if download does not start in time
            print(f"Download timed out: {e}")
        finally:
            browser.close()
        return file_name


def download_one_file(feedback_id, user_feedback_path):
    zip_file = download_log(
        f"https://feedback.pt.xiaomi.com/feedback/logDownloadBox?feedbackId={feedback_id}"
    )
    return Log284.from_zip(zip_file, user_feedback_path)
