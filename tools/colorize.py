#!/usr/bin/env python3
"""
Colorize sprites.
"""

import argparse
import json
import os
import sys

from pathlib import Path
from typing import Any, Optional, Tuple, Union

try:
    vips_path = os.getenv("LIBVIPS_PATH")
    if vips_path is not None and vips_path != "":
        os.environ["PATH"] += ";" + os.path.join(vips_path, "bin")
    import pyvips
    Vips = pyvips
except ImportError:
    import gi
    gi.require_version('Vips', '8.0')  # NoQA
    from gi.repository import Vips

PNGSAVE_ARGS = {
    'compression': 9,
    'strip': True,
    'filter': 8,
}

class ColorizingException(Exception):
    '''
    Base class for all colorizing exceptions
    '''


def read_json(json_path: Path) -> dict:
    with open(json_path, 'r', encoding="utf-8") as file:
        try:
            entries = json.load(file)
        except Exception:
            print(
                'error loading %s',
                json_path)
            raise

        if not isinstance(entries, list):
            entries = [entries]

    return entries


def load_image(
    png_path: Union[str, Path],
) -> pyvips.Image:
    '''
    Load and verify an image using pyvips
    '''
    try:
        image = Vips.Image.pngload(str(png_path))
    except pyvips.error.Error as pyvips_error:
        raise ColorizingException(
            f'Cannot load {png_path}: {pyvips_error.message}') from None
    except UnicodeDecodeError:
        raise ColorizingException(
            f'Cannot load {png_path} with UnicodeDecodeError, '
            'please report your setup at '
            'https://github.com/libvips/pyvips/issues/80') from None
    if image.interpretation != 'srgb':
        image = image.colourspace('srgb')

    try:
        if not image.hasalpha():
            image = image.addalpha()
        if image.get_typeof('icc-profile-data') != 0:
            image = image.icc_transform('srgb')
    except Vips.Error as vips_error:
        print(
            '%s: %s',
            png_path, vips_error)

    return image


def colorize(json_path: Path, output_dir: Path) -> None:
    directory = json_path.parents[0]
    entries = read_json(json_path)

    output_dir.mkdir(exist_ok=True)

    for entry in entries:
        out_id = entry.get("id")
        source = entry.get("file")
        colors = entry.get("colors")

        image = load_image(directory.joinpath(source+".png"))

        for mask, col in colors:
            if len(col) == 3:
                col = col + [255]
            col = list(map(lambda c: c / 255.0, col))
            mask = load_image(directory.joinpath(mask+".png")) / 255.0
            image = (image * (1.0 - mask)) + image * mask * col

        image.pngsave(str(output_dir.joinpath(out_id+".png")), **PNGSAVE_ARGS)


def main() -> Union[int, ColorizingException]:
    """
    Called when the script is executed directly
    """
    # read arguments and initialize objects
    arg_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument(
        '--dir', type=Path,
        default='.',
        help='Source files directory path')

    args_dict = vars(arg_parser.parse_args())
    path = args_dict.get('dir').resolve()

    colorize(path.joinpath("test.col"), path.joinpath("autocolor"))


if __name__ == '__main__':
    sys.exit(main())
