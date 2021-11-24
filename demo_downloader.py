import cloudscraper
import copy
import json
import os
import requests
import sys
import ssl

from optparse import OptionParser
from pathlib import Path
from shutil import copyfile
from time import sleep
from tqdm import tqdm


class DemoDownloader:
    """ CSGO Demo Downloader """

    def __init__(
        self, manifest_file_path: str, download_directory: str, max_retries: int = 3
    ):
        """ Constructor """
        self.max_retries = max_retries

        if not os.path.isfile(manifest_file_path):
            raise Exception("Unable to find manifest file")

        try:
            manifest_f = open(manifest_file_path, "r")
            manifest_data = json.load(manifest_f)
        except:
            raise Exception("Invalid manifest file content")
        else:
            event_id = manifest_data["event_url"].split("=")[1]

            self.output_dir = os.path.join(download_directory, event_id)

            if not os.path.exists(self.output_dir):
                Path(self.output_dir).mkdir(parents=True, exist_ok=True)

            self.progress_file_path = os.path.join(self.output_dir, "progress.json")

            if os.path.isfile(self.progress_file_path):
                with open(self.progress_file_path, "r") as progress_f:
                    self.progress = json.load(progress_f)
            else:
                self.progress = {"event_id": event_id, "matches": []}

                for match in manifest_data["matches"]:
                    self.progress["matches"].append(
                        {
                            "match_url": match["match_url"],
                            "demos_url": match["gotv_demo_url"],
                            "status": "pending",
                        }
                    )

                # creating file for tracking progress
                with open(self.progress_file_path, "w+") as progress_f:
                    json.dump(self.progress, progress_f, ensure_ascii=True)

            # making local copy of manifest file
            copyfile(manifest_file_path, os.path.join(self.output_dir, "manifest.json"))
        finally:
            manifest_f.close()

    def update_progress():
        """ Updates progress file with already downloaded files """
        json.dump(self.progress, self.progress_file_path, ensure_ascii=True)

    def download_from_url_bypass_cloudflare(self, scraper, url: str, fname: str):
        """ Downloads a file from a URL """
        resp = scraper.get(url, verify=False, stream=True)

        total = int(resp.headers.get("content-length", 0))
        print(f"Downloading demofile '{url}' from HLTV with {total} bytes")

        with open(fname, "wb") as file, tqdm(
            desc=fname,
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in resp.iter_content(chunk_size=1024):
                size = file.write(data)
                bar.update(size)

    def download_demos(self):
        """ Downloads demo files marked as pending in progress file """
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True},
            ssl_context=ctx
        )

        for index, match in enumerate(self.progress["matches"]):
            if match["status"] != "pending":
                continue

            file_name = match["match_url"].split("/")[-1] + ".rar"
            file_path = os.path.join(self.output_dir, file_name)

            print(f"Downloading {file_name} ({match['demos_url']})")
            tries = 1

            while tries <= self.max_retries:
                try:
                    self.download_from_url_bypass_cloudflare(
                        scraper, match["demos_url"], file_path
                    )

                    # since we're here, no errors occurred (supposedly)
                    # updating progress
                    match["status"] = "done"
                    self.progress["matches"][index] = match

                    with open(self.progress_file_path, "w+") as progress_f:
                        json.dump(self.progress, progress_f, ensure_ascii=True)

                    break
                except Exception as e:
                    print(e)
                    sleep(pow(2, tries))
                    tries += 1


if __name__ == "__main__":

    parser = OptionParser()

    parser.add_option(
        "-m",
        "--manifest-file-path",
        dest="manifest_file_path",
        help="parses MANIFEST to fetch demo-file urls",
        metavar="MANIFEST",
    )

    parser.add_option(
        "-d",
        "--download-dir",
        dest="download_dir",
        help="saves progress file and downloaded files into subdirectories inside the DIRECTORY",
        metavar="DIRECTORY",
    )

    options, args = parser.parse_args()

    downloader = DemoDownloader(
        options.manifest_file_path,
        options.download_dir,
    )

    downloader.download_demos()
