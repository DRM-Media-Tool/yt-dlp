from yt_dlp.postprocessor.common import PostProcessor
import os
import subprocess
import requests
from bs4 import BeautifulSoup
import json


class MP4DecryptPP(PostProcessor):
    def __init__(self, downloader=None, **kwargs):
        super().__init__(downloader)
        self._kwargs = kwargs

    def run(self, info):
        filepath = info.get('filepath')
        license_url = info.get('licence_url')
        formats = info.get('formats')
        manifest_url = None
        for format_obj in formats:
            url = format_obj.get('manifest_url', '')
            if ".mpd" in url:
                manifest_url = url
                break
        if manifest_url:
            # print('manifest_url', manifest_url)
            cookies = formats[0].get('http_headers')
            if cookies:
                session = requests.Session()
                response = session.get(manifest_url, headers=cookies)
                # print(response.text)
                soup = BeautifulSoup(response.text, 'xml')
                cenc_pssh_tag = soup.find('cenc:pssh')
                if cenc_pssh_tag:
                    cenc_pssh_value = cenc_pssh_tag.get_text()
                    # print("pssh", cenc_pssh_value)
                else:
                    print("No <cenc:pssh> tag found in the response.")
            else:
                print("No cookies found in the format object.")
        else:
            print("No manifest URL containing '.mpd' found.")

        if filepath:
            if 'decrypt' in self._kwargs:
                # decryption_key = self._kwargs['decrypt']
                # print(decryption_key)
                success = self.keydb(filepath, cenc_pssh_value, license_url)
                if success:
                    self.to_screen(f'Decryption successful for "{filepath}"')
                else:
                    self.to_screen(f'Decryption successful for "{filepath}"')
            elif 'keyfile' in self._kwargs:
                keyfile = self._kwargs['keyfile']
                if os.path.exists(keyfile):
                    success = self.decrypt_with_keyfile(filepath, keyfile)
                    if success:
                        self.to_screen(f'Decryption successful for "{filepath}" using keyfile: "{keyfile}"')
                    else:
                        self.to_screen(f'Decryption failed for "{filepath}" using keyfile  "{keyfile}"')
                else:
                    self.to_screen(f'Keyfile not found: "{keyfile}"')
            else:
                self.to_screen("No decryption key or keyfile provided.")
                return [], info

        else:
            filepath = info.get('_filename')
            self.to_screen(f'Pre-processed "{filepath}" with {self._kwargs}')

        return [], info

    def keydb(self, filepath, cenc_pssh_value, license_url):
        api_key = os.environ.get("API_KEY")
        try:
            print()
            print("pssh:", cenc_pssh_value)
            print()
            print("licence_url:", license_url)
            print()
            api_url = "https://keysdb.net/api"
            url = license_url
            pssh = cenc_pssh_value
            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Ktesttemp, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            }
            payload = {
                "license_url": url,
                "pssh": pssh,
            }
            r = requests.post(api_url, headers=headers, json=payload)
            output_file = f"{os.path.splitext(filepath)[0]}_decrypted{os.path.splitext(filepath)[1]}"
            print(r.text)
            if r is not None:
                data = json.loads(r.text)
                # print(data)
                cmd = ["mp4decrypt"]
                key_data = data.get("keys")
                # key_d = key_data.get('key')
                # print('test', key_data)
                if key_data is not None:
                    key_value = key_data[0]['key']
                    cmd.extend(["--key", key_value])
                else:
                    data = data.get("keys")
                    # print(data)
                    for key in data:
                        # print('test2', key)
                        cmd.extend(["--key", key])
                    cmd.extend([filepath, output_file])
                    # USE FOR DEBUGGING PURPOSES
                    # self.to_screen(f'Executing command: {" ".join(cmd)}')
                    subprocess.run(cmd, check=True)
                    os.remove(filepath)
                    os.rename(output_file, filepath)
                    return True
                # print(cmd)
            else:
                print("No 'keys' found in the response.")
        except subprocess.CalledProcessError:
            return False

    def decrypt_with_keyfile(self, filepath, keyfile):
        try:
            with open(keyfile, 'r') as f:
                keys = f.read().splitlines()

            output_file = f"{os.path.splitext(filepath)[0]}_decrypted{os.path.splitext(filepath)[1]}"
            cmd = ["mp4decrypt"]
            for key in keys:
                cmd.extend(["--key", key])
            cmd.extend([filepath, output_file])
            # USE FOR DEBUGGING PURPOSES
            # self.to_screen(f'Executing command: {" ".join(cmd)}')
            subprocess.run(cmd, check=True)
            os.remove(filepath)
            os.rename(output_file, filepath)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False


def setup(downloader, **kwargs):
    downloader.add_post_processor(MP4DecryptPP(downloader, **kwargs))
