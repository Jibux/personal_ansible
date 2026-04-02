#!/usr/bin/env python3


# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pymupdf"
# ]
# ///


import sys

import fitz


def usage():
    print(f"{sys.argv[0]} path_to_pdf")


def exit_usage():
    usage()
    exit(1)


len(sys.argv) == 1 and exit_usage()
doc = sys.argv[1]

with fitz.open(doc) as pdf:
    for page_idx, page in enumerate(pdf):
        page_split = page.get_text().splitlines()
        print(f"############################ PAGE {page_idx + 1} ############################")
        for line_idx, line in enumerate(page_split):
            print(f"{line_idx + 1}: {line}")
