#!/usr/bin/env python3


# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pymupdf",
#   "PyYAML"
# ]
# ///


import os
import re
import shutil
import stat
import sys
from functools import reduce

import fitz
from yaml import CSafeLoader as Loader
from yaml import load

file_type_regex_list = {"pdf": r".pdf"}


def usage():
    print(f"Usage: {sys.argv[0]} [paths]")
    print("paths (optional): path1 path2 etc.")
    print("Paths will be retrieved either from command line or from doc_config.yaml.")
    print('Configuration examples can be found in "doc_config_example.yaml".')


def exit_usage():
    usage()
    exit(1)


def error(msg):
    print(f"ERR - {msg}")


def exit_cfg_error(msg):
    error(f"CONFIG ERROR: {msg}")
    exit(1)


def expand_home_dir(path):
    return os.path.expanduser(path)


def item_exists(item):
    return item is not None


def ic_match(pattern):
    def ic_mstring(string):
        return re.match(pattern, string, re.IGNORECASE)

    return ic_mstring


def ext_regex_match(regex_key):
    return ic_match(file_type_regex_list[regex_key])


def get_file_type(item_ext):
    def find_in_file_type_regex_list(regex_key):
        return ext_regex_match(regex_key)(item_ext)

    return next(filter(find_in_file_type_regex_list, file_type_regex_list.keys()), None)


def match_file_type_in_cfg(file_type):
    def compare_file_type_with_cfg_item(cfg_item):
        cfg_item_f_type = cfg_item["file_type"]
        return cfg_item_f_type == file_type

    return compare_file_type_with_cfg_item


def get_file_name_to_match(file_name):
    return [file_name]


def get_file_content_to_match(file_path, file_type):
    if file_type == "pdf":
        return fitz.open(file_path)
    else:
        return []


def get_content_to_match(item, method, file_type):
    if method == "file_name":
        return get_file_name_to_match(item.name)
    elif method == "read_file":
        return get_file_content_to_match(item.path, file_type)
    else:
        return None


# array_1 is a virtual indexed from '1' array
# We use this because we enumerate page nr, line nr, position in string from '1' and not '0'
def is_index_in_array_1(array, index):
    return index <= len(array)


def get_item_from_array_1(array):
    def get_item(index):
        if is_index_in_array_1(array, index):
            return array[index - 1]
        else:
            return None

    return get_item


def substitute_string(index, line, string):
    old_str = f"%{index}%"
    return string.replace(old_str, line)


def substitute_dest_path(matches):
    # position is position in string so obviously > 0
    def process_matches(dest, position):
        if is_index_in_array_1(matches, position):
            return substitute_string(position, get_item_from_array_1(matches)(position), dest)
        else:
            return dest

    return process_matches


# dest: /tmp/%2%..., matches: ['foo', 'bar', etc.]
def compute_path(dest, matches):
    pos_list_str = re.findall(r"%(\d+)%", dest)
    if not pos_list_str:
        return dest
    pos_list_int = map(lambda i: int(i), pos_list_str)
    return reduce(substitute_dest_path(matches), pos_list_int, dest)


def get_file_path_from_regex(lines, pattern):
    if "regex" not in pattern:
        exit_cfg_error("'regex' should be in 'pattern'")
    if "dest" not in pattern:
        exit_cfg_error("'dest' should be in 'pattern'")
    regex = pattern["regex"]
    dest = pattern["dest"]
    for line in lines:
        result = re.search(regex, line)
        if result:
            return compute_path(dest, result.groups())
    return None


def get_array_items_from_pattern_key(pattern, key, array):
    if key in pattern:
        positions = pattern[key]
    else:
        # positions: page nrs, line nrs, etc. so obviously [> 0]
        # defaults to [1] (1st page, 1st line, etc.)
        positions = [1]
    return list(filter(item_exists, map(get_item_from_array_1(array), positions)))


def get_page_lines(pattern):
    def get_lines(lines, page):
        page_split = page.splitlines() if type(page) is str else page.get_text().splitlines()
        return lines + get_array_items_from_pattern_key(pattern, "lines", page_split)

    return get_lines


def match_content_in_pattern(content, pattern):
    pages = get_array_items_from_pattern_key(pattern, "pages", content)
    lines = list(reduce(get_page_lines(pattern), pages, []))

    return get_file_path_from_regex(lines, pattern)


def build_file_name(content):
    def from_pattern(path, pattern):
        if path is None:
            return None
        tmp_path = match_content_in_pattern(content, pattern)
        if item_exists(tmp_path):
            return path + tmp_path
        else:
            return None

    return from_pattern


def match_content_in_cfg(content, cfg_item):
    if "patterns" in cfg_item:
        patterns = cfg_item["patterns"]
    else:
        exit_cfg_error("'patterns' should be in 'document'")
    return reduce(build_file_name(content), patterns, "")


def get_file_path_from_content(content, cfg_list):
    for cfg_item in cfg_list:
        for document in cfg_item["documents"]:
            path = match_content_in_cfg(content, document)
            if item_exists(path):
                full_path = "{}{}".format(cfg_item.get("dest_prefix", ""), path)
                return full_path
    return None


def match_method(method):
    def match_in_cfg_item(cfg_item):
        return cfg_item["method"] == method

    return match_in_cfg_item


def adjust_path(path, file_name):
    if os.path.isdir(path):
        return os.path.dirname(path + "/") + "/" + file_name
    else:
        return path


def is_the_same_inode(file1, file2):
    return (
        os.path.isfile(file1) and os.path.isfile(file2) and os.stat(file1)[stat.ST_INO] == os.stat(file2)[stat.ST_INO]
    )


def process_cfg(item, method, cfg):
    cfg_match_method = list(filter(match_method(method), cfg))
    if len(cfg_match_method) == 0:
        return None
    content_to_match = get_content_to_match(item, method, cfg[0]["file_type"])
    tmp_path = get_file_path_from_content(content_to_match, cfg_match_method)
    if tmp_path is None:
        return None
    new_path = adjust_path(expand_home_dir(tmp_path), item.name)
    if is_the_same_inode(new_path, item.path):
        return None
    return {"file": item.path, "new_path": new_path}


def process_file(config):
    def f(item):
        if not item.is_file():
            return None
        _, item_ext = os.path.splitext(item.path)
        file_type = get_file_type(item_ext)
        print(f'Process "{item.name}" ({file_type})')
        if file_type is None:
            return None
        # Seek the configuration matching this file_type
        cfg_with_f_type = list(filter(match_file_type_in_cfg(file_type), config))
        if cfg_with_f_type is None:
            return None
        ret = process_cfg(item, "file_name", cfg_with_f_type)
        if ret is not None:
            return ret
        return process_cfg(item, "read_file", cfg_with_f_type)

    return f


def process_path(config):
    def f(path: str):
        print(f'Process path "{path}"')
        processed_list = map(process_file(config), os.scandir(path))
        return list(filter(item_exists, processed_list))

    return f


def get_new_path_dir(item):
    return os.path.dirname(item["new_path"])


def compute_directories_from_file(dir_list, file_path):
    if file_path == "/" or os.path.exists(file_path):
        return dir_list
    else:
        return compute_directories_from_file([file_path] + dir_list, os.path.dirname(file_path))


def compute_directories_from_file_list(file_list):
    return reduce(compute_directories_from_file, file_list, [])


def display_info_dir(directory):
    print(f"Will create directory '{directory}'")


def display_info_move(item):
    info = "file exists" if os.path.isfile(item["new_path"]) else "new file"
    print("Will move '{}' to '{}' ({})".format(item["file"], item["new_path"], info))


def display_actions(dir_list, items):
    print("")
    for d in dir_list:
        display_info_dir(d)
    if len(dir_list) > 0:
        print("")
    for item in items:
        display_info_move(item)


def confirm():
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("Proceed? (y/n) ").lower()
    return answer == "y"


def create_dir(d):
    os.mkdir(d)


def move_file(item):
    shutil.move(item["file"], item["new_path"])


def do_actions(dir_list, items):
    for d in dir_list:
        create_dir(d)
    for item in items:
        move_file(item)


def get_paths(config):
    paths = config["paths"] if "paths" in config else []
    # argv will overwrite paths written in config
    final_paths = sys.argv[1:] if len(sys.argv) != 1 else paths
    # For each path, replace '~' by user's home dir
    return list(map(expand_home_dir, final_paths))


def main():
    script_path = os.path.realpath(sys.argv[0])
    script_dir = os.path.dirname(script_path)
    config_path = "{}/{}".format(script_dir, "doc_config.yaml")

    # Load config
    with open(config_path) as ymlfile:
        config = load(ymlfile, Loader=Loader)

    paths = get_paths(config)

    if len(paths) == 0:
        exit_usage()
    print(f"Paths to process: {paths}")

    # Sum will flatten list
    processed_list = sum(map(process_path(config["files_patterns"]), paths), [])

    if len(processed_list) == 0:
        print("No action to perform")
        exit(0)

    new_path_dir_list = list(map(get_new_path_dir, processed_list))
    dir_list = compute_directories_from_file_list(new_path_dir_list)
    dir_list_cleaned = sorted(list(set(dir_list)))

    display_actions(dir_list_cleaned, processed_list)

    if not confirm():
        exit(1)

    do_actions(dir_list_cleaned, processed_list)


if __name__ == "__main__":
    main()
