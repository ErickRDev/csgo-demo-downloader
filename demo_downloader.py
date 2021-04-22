import cloudscraper
import copy
import json
import os
import requests
import sys

from tqdm import tqdm


def download_from_url_bypass_cloudflare(scraper, url: str, fname: str):
    """ Downloads a file from a URL """
    resp = scraper.get(url, stream=True)

    total = int(resp.headers.get("content-length", 0))
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


def download_demo_files(manifest_fp: str):
    """ Downloads demo files present in a manifest JSON file """
    scraper = cloudscraper.create_scraper()

    try:
        with open(manifest_fp, "r") as fin:
            manifest_data = json.load(fin)

            event_id = manifest_data["event_url"].split("=")[1]

            if not os.path.isdir(event_id):
                os.mkdir(event_id)

            for match in manifest_data["matches"]:
                if match["match_id"] == "2347028":
                    # skipping ESL-PRO S13 final match
                    continue

                file_name = match["match_url"].split("/")[-1]
                file_path = os.path.join(event_id, file_name)

                print(f"Starting file download => {file_name}")
                download_from_url_bypass_cloudflare(scraper, match["gotv_demo_url"], file_path)

    except Exception as e:
        print("Failed to parse manifest file:")
        print(e)
        print("Aborting..")


def print_usage():
    """ Prints CLI usage """
    print("-" * 40)
    print("Usage:")
    print
    print("\t--manifest=<path_to_file>")
    print("-" * 40)


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Invalid arguments!")
        print_usage()
        exit()

    try:
        manifest_fp = sys.argv[1].split("=")[1]

        if not os.path.exists(manifest_fp):
            print("Manifest file not found!")
            exit()
    except:
        print("Failed to parse provided file path")
        print_usage()
        exit()
    else:
        download_demo_files(manifest_fp)
