
"""handlers/combine.py

Handle /combine API endpoint.
"""
from typing import Sequence, Tuple, Optional, TypeVar, BinaryIO
from concurrent.futures import Future

from terracotta import get_driver, get_settings, image, xyz, exceptions
from terracotta.profile import trace

NumberOrString = TypeVar("NumberOrString", int, float, str)
ListOfRanges = Sequence[
    Optional[Tuple[Optional[NumberOrString], Optional[NumberOrString]]]
]


@trace("combine_handler")
def combine(
    keys_list: list[list[str]],
    rgb_values: Optional[Tuple[str, str, str]] = None,
    tile_xyz: Optional[Tuple[int, int, int]] = None,
    stretch_ranges: Optional[ListOfRanges] = None,
    tile_size: Optional[Tuple[int, int]] = None,
) -> BinaryIO:
    """Returns a combined image from multiple datasets based on the provided keys

    Band data is retrieved asynchronously for each specified key.
    """
    import numpy as np

    # make sure all stretch ranges contain two values
    if stretch_ranges is None:
        stretch_ranges = [None, None, None]

    if len(stretch_ranges) != 3:
        raise exceptions.InvalidArgumentsError(
            "stretch_ranges argument must contain 3 values"
        )

    stretch_ranges_ = [
        stretch_range or (None, None) for stretch_range in stretch_ranges
    ]

    if rgb_values is not None:
        if len(rgb_values) != 3:
            raise exceptions.InvalidArgumentsError(
                "rgb_values argument must contain 3 values"
            )

    settings = get_settings()

    if tile_size is None:
        tile_size_ = settings.DEFAULT_TILE_SIZE
    else:
        tile_size_ = tile_size

    driver = get_driver(settings.DRIVER_PATH, provider=settings.DRIVER_PROVIDER)
    
    with driver.connect():
        key_names = driver.key_names

        for i in range(len(keys_list)):
            some_keys = keys_list[i]
            if len(some_keys) != len(key_names) - 1:
                raise exceptions.InvalidArgumentsError(
                    f"must specify all keys except last for keys_list[{i}]"
                )

        def get_band_future(some_keys: list[str], band_key: Optional[str] = None) -> Future:
            band_keys = (*some_keys, band_key) if band_key else some_keys

            return xyz.get_tile_data(
                driver,
                band_keys,
                tile_xyz=tile_xyz,
                tile_size=tile_size_,
                asynchronous=True,
            )

        if rgb_values is not None:
            # for each dataset get its red, green, and blue channel data
            futures = [get_band_future(some_keys, b_key) for some_keys in keys_list for b_key in rgb_values]
        else:
            futures = [get_band_future(some_keys) for some_keys in keys_list]

        out_arrays = []
        band_items = zip(rgb_values, stretch_ranges_, futures)

        for i, (band_key, band_stretch_override, band_data_future) in enumerate(
            band_items
        ):
            keys = (*some_keys, band_key)
            metadata = driver.get_metadata(keys)

            band_stretch_range = list(metadata["range"])
            scale_min, scale_max = band_stretch_override

            percentiles = metadata.get("percentiles", [])
            if scale_min is not None:
                band_stretch_range[0] = image.get_stretch_scale(scale_min, percentiles)

            if scale_max is not None:
                band_stretch_range[1] = image.get_stretch_scale(scale_max, percentiles)

            if band_stretch_range[1] < band_stretch_range[0]:
                raise exceptions.InvalidArgumentsError(
                    "Upper stretch bound must be higher than lower bound"
                )

            band_data = band_data_future.result()
            out_arrays.append(image.to_uint8(band_data, *band_stretch_range))
    
    out = np.ma.stack(out_arrays, axis=-1)
    return image.array_to_png(out)