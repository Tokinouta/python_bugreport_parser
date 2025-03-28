from playwright.sync_api import sync_playwright
import os
import zipfile
import glob
import pandas as pd


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

        # page.on("response", handle_response)
        page.goto(url, wait_until="load")
        print("wait to scan qrcode")

        try:
            with page.expect_download(timeout=5000) as download_info:
                pass
            download = download_info.value
            print(download.suggested_filename)
            print(download.path())
            print("download finished")
            download.save_as(download.suggested_filename)
        except Exception as e:
            print(e)
        browser.close()
        return download.suggested_filename


def download_one_file(id):
    # Set user feedback path
    home_dir = os.getenv("HOME")
    if not home_dir:
        home_dir = "."

    user_feedback_path = os.path.join(home_dir, "jira", "o1-feedback")

    download_file_inner(
        id,
        f"https://feedback.pt.xiaomi.com/feedback/logDownloadBox?feedbackId={id}",
        user_feedback_path,
    )


# for each row, map a function on them
def download_file_from_df(row):
    user_feedback_path = os.path.join(os.getenv("HOME"), "jira", "o3-feedback")

    id, log_url = row["反馈ID"], row["日志"]
    download_file_inner(id, log_url, user_feedback_path)


def download_file_inner(id, log_url, user_feedback_path):
    print(id, log_url)
    try:
        bugreport_zip = download_log(log_url)
    except Exception as e:  # 修复此处的语法错误
        print(f"Error downloading log for ID {id}: {e}")
        return
    last_current_dir = os.getcwd()
    print(last_current_dir)
    # extract(id, bugreport_zip, user_feedback_path)
    # Change back to original directory
    os.chdir(last_current_dir)


if __name__ == "__main__":
    # df = pd.read_excel("data.xlsx")
    # filter out the rows where the column "原因及分析详情" is null and "日志" is not null
    # df = df[df["原因及分析详情"].isna() & df["日志"].notna()]
    # print(df.head())

    # df.apply(lambda x: download_file_from_df(x), axis=1)
    # download_file_inner(
    #     "BUGOS2-190990",
    #     "https://feedback.pt.india.miui.com/feedback/logDownloadBox?feedbackId=611801724",
    # )

    download_one_file("111305893")
