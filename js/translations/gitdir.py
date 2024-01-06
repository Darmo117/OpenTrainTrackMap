#!/usr/bin/python3
"""
Adapted from:
https://github.com/sdushantha/gitdir/blob/master/gitdir/gitdir.py
Licensed under MIT License.
"""
import argparse
import json
import pathlib
import re
import signal
import sys
import typing
import urllib.request

from colorama import Fore, Style, init

init()

# this ANSI code lets us erase the current line
ERASE_LINE = '\x1b[2K'

COLOR_NAME_TO_CODE = {'default': '', 'red': Fore.RED, 'green': Style.BRIGHT + Fore.GREEN}


def print_text(text: str, color: str = 'default', in_place: bool = False, **kwargs):
    """Print text to console, a wrapper to built-in print.

    :param text: text to print
    :param color: can be one of "red" or "green", or "default"
    :param in_place: whether to erase previous line and print in place
    :param kwargs: other keywords passed to built-in print
    """
    if in_place:
        print('\r' + ERASE_LINE, end='')
    print(COLOR_NAME_TO_CODE[color] + text + Style.RESET_ALL, **kwargs)


def _create_url(url: str) -> tuple[str, pathlib.Path]:
    """From the given url, produce a URL that is compatible with Github's REST API. Can handle blob or tree paths."""
    repo_only_url = re.compile(r'https://github\.com/[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}/[a-zA-Z0-9]+$')
    re_branch = re.compile('/(tree|blob)/(.+?)/')

    # Check if the given url is a url to a GitHub repo. If it is, tell the
    # user to use 'git clone' to download it
    if re.match(repo_only_url, url):
        message = 'The given url is a complete repository. Use "git clone" to download the repository'
        print_text('✘ ' + message, 'red', in_place=True)
        raise RuntimeError(message)

    # extract the branch name from the given url (e.g master)
    branch = re_branch.search(url)
    download_dirs = url[branch.end():]
    api_url = (url[:branch.start()].replace('github.com', 'api.github.com/repos', 1) +
               '/contents/' + download_dirs + '?ref=' + branch.group(2))
    return api_url, pathlib.Path(download_dirs)


def download(repo_url: str, output_dir: pathlib.Path = pathlib.Path('.'),
             filter_: typing.Callable[[str], bool] = lambda _: True) -> int:
    """Downloads the files and directories in repo_url."""
    api_url, download_dirs = _create_url(repo_url)

    try:
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        response = urllib.request.urlretrieve(api_url)
    except KeyboardInterrupt:
        # when CTRL+C is pressed during the execution of this script,
        # bring the cursor to the beginning, erase the current line, and dont make a new line
        print_text('✘ Got interrupted', 'red', in_place=True)
        sys.exit()

    total_files = 0

    with open(response[0], mode='r') as f:
        data = json.load(f)
        # getting the total number of files so that we
        # can use it for the output information later
        total_files += len(data)

        # If the data is a file, raise error.
        if isinstance(data, dict) and data['type'] == 'file':
            message = 'Not a directory'
            print_text('✘ ' + message, 'red', in_place=False)
            raise RuntimeError(message)

        for file in data:
            file_url = file['download_url']

            if file_url is not None:
                file_name = file['name']
                if not filter_(file_name):
                    continue
                try:
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                    urllib.request.install_opener(opener)
                    dir_out = (output_dir / file['path']).parent
                    dir_out.mkdir(parents=True, exist_ok=True)
                    # download the file
                    urllib.request.urlretrieve(file_url, dir_out / file_name)
                    # bring the cursor to the beginning, erase the current line, and dont make a new line
                    print_text(
                        f'Downloaded: {Fore.WHITE}{"{}".format(file_name)}',
                        'green',
                        in_place=False,
                        end='\n',
                        flush=True
                    )
                except KeyboardInterrupt:
                    # when CTRL+C is pressed during the execution of this script,
                    # bring the cursor to the beginning, erase the current line, and dont make a new line
                    print_text('✘ Got interrupted', 'red', in_place=False)
                    sys.exit()
            else:
                total_files += download(file['html_url'], output_dir)

    return total_files


def main():
    if sys.platform != 'win32':
        # disable CTRL+Z
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    parser = argparse.ArgumentParser(description='Download directories/folders from GitHub')
    parser.add_argument('urls', nargs='+',
                        help='List of Github directories to download.')
    parser.add_argument('--output_dir', '-d', dest='output_dir', default=pathlib.Path('.'),
                        type=pathlib.Path, help='All directories will be downloaded to the specified directory.')
    args = parser.parse_args()

    total_files = 0
    for url in args.urls:
        try:
            total_files += download(url, args.output_dir)
        except RuntimeError as e:
            print_text(f'Error: {e}', 'red')

    print_text(f'✔ Download complete: {total_files} file(s)', 'green', in_place=True)


if __name__ == '__main__':
    main()
