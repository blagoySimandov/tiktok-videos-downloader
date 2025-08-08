import json
import os
import requests
from flask import Flask, request, jsonify, send_file
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import tempfile
import uuid

app = Flask(__name__)


def get_browser_context():
    browser = None
    try:
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        return p, browser, context
    except Exception as e:
        if browser:
            browser.close()
        raise e


def extract_video_data(video_url):
    p, browser, context = get_browser_context()
    try:
        page = context.new_page()
        page.goto(video_url, wait_until="networkidle", timeout=30000)

        soup = BeautifulSoup(page.content(), "html.parser")
        script_tag = soup.find("script", {"id": "__UNIVERSAL_DATA_FOR_REHYDRATION__"})

        if not script_tag:
            raise Exception("Could not find video data")

        data = json.loads(script_tag.text) if script_tag.text else "{}"
        download_url = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"][  # pyright: ignore
            "itemStruct"
        ]["video"]["downloadAddr"]

        all_cookies = context.cookies()
        cookies_dict = {
            cookie.get("name", ""): cookie.get("value", "") for cookie in all_cookies
        }

        if "msToken" not in cookies_dict:
            raise Exception("Failed to generate required token")

        return download_url, cookies_dict
    finally:
        browser.close()
        p.stop()


def download_video_file(download_url, cookies_dict, video_url, output_path):
    headers = {
        "Referer": video_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    }

    with requests.get(
        download_url, headers=headers, cookies=cookies_dict, stream=True
    ) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return os.path.getsize(output_path)


def download_tiktok_video(video_url, output_filename):
    try:
        download_url, cookies_dict = extract_video_data(video_url)
        file_size = download_video_file(
            download_url, cookies_dict, video_url, output_filename
        )
        return True, file_size
    except Exception as e:
        return False, str(e)


@app.route("/download", methods=["POST"])
def webhook_download():
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "URL is required"}), 400

        video_url = data["url"]
        temp_dir = tempfile.mkdtemp()
        filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(temp_dir, filename)

        success, result = download_tiktok_video(video_url, output_path)

        if not success:
            return jsonify({"error": result}), 500

        return send_file(
            output_path,
            as_attachment=True,
            download_name=filename,
            mimetype="video/mp4",
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
