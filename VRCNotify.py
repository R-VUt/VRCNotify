import json
import colorama
import pyfiglet
import watchdog.observers
import watchdog.events

import platform
import time
import requests

colorama.init()


class LogEventHandler(watchdog.events.PatternMatchingEventHandler):
    def __init__(
        self,
        patterns,
        ignore_patterns=None,
        ignore_directories=False,
        case_sensitive=False,
    ):
        super().__init__(patterns, ignore_patterns, ignore_directories, case_sensitive)
        self.last_lines = None
        self.is_first = True
        self.not_in_room = False
        self.join_time = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        # filename check - output_log_YYYY-MM-DD_HH-MM-SS.txt
        if not event.src_path.endswith(".txt"):
            return
        if not event.src_path.find("output_log_"):
            return

        # read last line
        self.last_lines = get_last_line(event.src_path, self.last_lines)
        if self.is_first:
            print()
            print("> first analyse.")
            for found_line in self.last_lines:
                if "User Authenticated" in found_line:
                    self.user_name = (
                        found_line.split("User Authenticated: ")[1]
                        .split(" (")[0]
                        .replace("\n", "")
                    )
                    print(
                        colorama.Fore.WHITE
                        + "["
                        + colorama.Fore.GREEN
                        + "INFO"
                        + colorama.Fore.WHITE
                        + "]"
                        + colorama.Fore.GREEN
                        + "Found User Data: "
                        + colorama.Fore.YELLOW
                        + self.user_name
                        + colorama.Fore.WHITE
                    )
            self.is_first = False
            print()

        else:
            for found_line in self.last_lines:
                if "User Authenticated" in found_line:
                    self.user_name = (
                        found_line.split("User Authenticated: ")[1]
                        .split(" (")[0]
                        .replace("\n", "")
                    )
                    print(
                        colorama.Fore.WHITE
                        + "["
                        + colorama.Fore.GREEN
                        + "INFO"
                        + colorama.Fore.WHITE
                        + "]"
                        + colorama.Fore.GREEN
                        + "Found User Data: "
                        + colorama.Fore.YELLOW
                        + self.user_name
                        + colorama.Fore.WHITE
                    )

                if "[Behaviour]" in found_line:
                    # print(found_line.replace("\n", ""))
                    # print(colorama.Fore.GREEN + "Behaviour found." + colorama.Fore.WHITE)
                    now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                    if "OnLeftRoom" in found_line:
                        self.not_in_room = True
                        print(
                            colorama.Fore.WHITE
                            + "["
                            + now_time
                            + "] "
                            + colorama.Fore.GREEN
                            + "left room. ignore after users."
                            + colorama.Fore.WHITE
                        )

                    elif "Joining or Creating Room" in found_line:
                        self.not_in_room = False
                        self.join_time = time.time()
                        print()
                        print(
                            colorama.Fore.WHITE
                            + "["
                            + now_time
                            + "] "
                            + colorama.Fore.GREEN
                            + "joined room. notify after users."
                            + colorama.Fore.WHITE
                        )
                        room_name = found_line.split("Joining or Creating Room: ")[
                            1
                        ].replace("\n", "")
                        print(
                            colorama.Fore.WHITE
                            + "["
                            + now_time
                            + "] "
                            + colorama.Fore.GREEN
                            + "Room name: "
                            + colorama.Fore.YELLOW
                            + room_name
                            + colorama.Fore.WHITE
                        )

                    elif "OnPlayerJoined " in found_line:
                        nickname = found_line.split("OnPlayerJoined ")[1].replace(
                            "\n", ""
                        )
                        print(
                            colorama.Fore.WHITE
                            + "["
                            + now_time
                            + "] "
                            + colorama.Fore.GREEN
                            + "Player joined: "
                            + colorama.Fore.YELLOW
                            + nickname
                            + colorama.Fore.WHITE
                        )

                        # check join time is less than 10 seconds
                        if time.time() - self.join_time < 10:
                            print(
                                colorama.Fore.WHITE
                                + "["
                                + now_time
                                + "] "
                                + colorama.Fore.GREEN
                                + "Not sending message. Too short time after join."
                                + colorama.Fore.WHITE
                            )
                        if self.not_in_room:
                            pass
                        elif nickname == self.user_name:
                            print(
                                colorama.Fore.WHITE
                                + "["
                                + now_time
                                + "] "
                                + colorama.Fore.WHITE
                                + "Not sending message. local user."
                            )
                        else:
                            send_line_notify(
                                "[" + now_time + "] " + "Player joined: " + nickname
                            )

                    elif "OnPlayerLeft " in found_line:
                        nickname = found_line.split("OnPlayerLeft ")[1].replace(
                            "\n", ""
                        )
                        print(
                            colorama.Fore.WHITE
                            + "["
                            + now_time
                            + "] "
                            + colorama.Fore.GREEN
                            + "Player left: "
                            + colorama.Fore.YELLOW
                            + nickname
                            + colorama.Fore.WHITE
                        )
                        if self.not_in_room:
                            pass
                        elif nickname == self.user_name:
                            print(
                                colorama.Fore.WHITE
                                + "["
                                + now_time
                                + "] "
                                + colorama.Fore.WHITE
                                + "Not sending message. local user."
                            )
                        else:
                            send_line_notify(
                                "[" + now_time + "] " + "Player left: " + nickname
                            )

            self.last_lines = found_line


def send_line_notify(message):
    # config.json
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    line_notify_token = config["token"]
    line_notify_api = "https://notify-api.line.me/api/notify"

    payload = {"message": message}

    r = requests.post(
        line_notify_api,
        headers={"Authorization": "Bearer " + line_notify_token},
        data=payload,
    )

    if r.status_code == 200:
        print(
            colorama.Fore.WHITE
            + "["
            + colorama.Fore.GREEN
            + "INFO"
            + colorama.Fore.WHITE
            + "]"
            + colorama.Fore.GREEN
            + "Line notify send success."
            + colorama.Fore.WHITE
        )


def get_last_line(file_path, before_last_line: str = None):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # remove empty lines
        lines = [line for line in lines if line != "\n"]
        if before_last_line != None:
            if before_last_line in lines:
                lines = lines[lines.index(before_last_line) :]
            else:
                lines = lines[-1:]
        return lines


def main():
    print(
        colorama.Fore.LIGHTCYAN_EX + pyfiglet.figlet_format("VRCNotify", font="slant")
    )
    print(colorama.Fore.WHITE + "=============================")
    print(colorama.Fore.GREEN + "Line notifyを使ってVRCのログを通知するツール")
    print(colorama.Fore.GREEN + "Ideas by: " + colorama.Fore.YELLOW + "@VRCLouisa")
    print()
    print(colorama.Fore.WHITE + "Version: " + colorama.Fore.YELLOW + "1.0.0")
    print(colorama.Fore.WHITE + "Developed by: " + colorama.Fore.YELLOW + "@rerassi")

    print(colorama.Fore.WHITE + "=============================")

    if platform.system() != "Windows":
        print(colorama.Fore.RED + "error.")
        print(colorama.Fore.RED + "このプログラムはWindowsでしか動作しません。")
        print(colorama.Fore.RED + "プログラムを終了します。")
        exit()

    print(colorama.Fore.WHITE + "1. " + colorama.Fore.YELLOW + "設定お読みます。")
    print(colorama.Fore.GREEN + "> reading config.json...", end="")

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print(colorama.Fore.GREEN + "done.")
    except FileNotFoundError:
        print(colorama.Fore.RED + "error.")
        print(colorama.Fore.RED + "config.jsonが見つかりません。")
        print(colorama.Fore.RED + "config.jsonをつくります。")

        print(colorama.Fore.WHITE + "====================================")
        print("line notifyのトークンを入力してください。")
        print("line notifyのトークンはこちらから取得できます。")
        print("> " + colorama.Fore.YELLOW + "https://notify-bot.line.me/ja/")
        print(colorama.Fore.WHITE + "====================================")
        print("> ", end="")
        token = input()
        print()
        print()
        print(colorama.Fore.WHITE + "line notifyのトークンをテストします。")

        print(colorama.Fore.GREEN + "> test message sending...", end="")
        r = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": "Bearer " + token},
            data={"message": "VRCNotifyのテストです。"},
        )

        if r.status_code == 200:
            print(colorama.Fore.GREEN + "done.")
            print(colorama.Fore.GREEN + "トークンは正しいです。")
            print(colorama.Fore.WHITE + "config.jsonを作成します。")
            print(colorama.Fore.GREEN + "> writing config.json...", end="")
            config = {"token": token}
            with open("config.json", "w") as f:
                json.dump(config, f)
            print(colorama.Fore.GREEN + "done.")
        else:
            print(colorama.Fore.RED + "error.")
            print(colorama.Fore.RED + "トークンが正しくありません。")
            print(colorama.Fore.RED + "プログラムを終了します。")
            exit()

    print(colorama.Fore.WHITE + "=============================")
    print(colorama.Fore.WHITE + "2. " + colorama.Fore.YELLOW + "VRCのログのディレクトリを確認します。")
    print(colorama.Fore.GREEN + "> checking VRChat's log directory...", end="")
    import os
    import sys

    if not os.path.exists(
        os.path.join(
            os.environ["USERPROFILE"], "AppData", "LocalLow", "VRChat", "VRChat"
        )
    ):
        print(colorama.Fore.RED + "error.")
        print(colorama.Fore.RED + "VRCのログのディレクトリが見つかりません。")
        print(colorama.Fore.RED + "プログラムを終了します。")
        exit()
    print(colorama.Fore.GREEN + "done.")
    print(colorama.Fore.WHITE + "=============================")

    print(colorama.Fore.WHITE + "3. " + colorama.Fore.YELLOW + "VRCのログ監視お起動ます。")
    print(colorama.Fore.GREEN + "> starting watchdog for VRChat's log...", end="")

    event_handler = LogEventHandler(
        patterns=["*.txt"],
        ignore_patterns=None,
        ignore_directories=False,
        case_sensitive=False,
    )
    observer = watchdog.observers.Observer()
    observer.schedule(
        event_handler,
        os.path.join(
            os.environ["USERPROFILE"], "AppData", "LocalLow", "VRChat", "VRChat"
        ),
        recursive=False,
    )
    observer.start()
    print(colorama.Fore.GREEN + "done.")
    print(colorama.Fore.WHITE + "=============================")
    print()
    print(
        "["
        + colorama.Fore.GREEN
        + "INFO"
        + colorama.Fore.WHITE
        + "] VRCNotifyお正常に起動しました。"
    )
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            break


if __name__ == "__main__":
    main()
