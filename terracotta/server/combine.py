"""server/combine.py

Flask route to handle /combine calls.
"""

from typing import Tuple, Any, Mapping, Dict
import json

from marshmallow import Schema, fields, validate, pre_load, ValidationError, EXCLUDE
from flask import request, send_file, Response

from terracotta import exceptions
from terracotta.server.fields import StringOrNumber, validate_stretch_range
from terracotta.server.flask_api import TILE_API

class CombineQuerySchema(Schema):
    tile_z = fields.Int(required=True, description="Requested zoom level")
    tile_y = fields.Int(required=True, description="y coordinate")
    tile_x = fields.Int(required=True, description="x coordinate")

class CombineOptionSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    keys_list = fields.List(
        required=True, description="List of dataset keys identifying datasets, in order",
        example="[\"europe/elevation\", \"europe/temperature\", \"europe/precipitation\"]",
        cls_or_instance=fields.String()
    )
    rgb_keys = fields.List(
        validate=validate.Length(equal=3),
        example="[\"red\", \"green\", \"blue\"]",
        required=False, description="Keys for red, green, and blue bands",
        cls_or_instance=fields.String()
    )
    r_range = fields.List(
        StringOrNumber(allow_none=True, validate=validate_stretch_range),
        validate=validate.Length(equal=2),
        example="[0,1]",
        missing=None,
        description=(
            "Stretch range [min, max] to use for the red band as JSON array. "
            "Min and max may be numbers to use as absolute range, or strings "
            "of the format `p<digits>` with an integer between 0 and 100 "
            "to use percentiles of the image instead. "
            "Null values indicate global minimum / maximum."
        ),
    )
    g_range = fields.List(
        StringOrNumber(allow_none=True, validate=validate_stretch_range),
        validate=validate.Length(equal=2),
        example="[0,1]",
        missing=None,
        description=(
            "Stretch range [min, max] to use for the gren band as JSON array. "
            "Min and max may be numbers to use as absolute range, or strings "
            "of the format `p<digits>` with an integer between 0 and 100 "
            "to use percentiles of the image instead. "
            "Null values indicate global minimum / maximum."
        ),
    )
    b_range = fields.List(
        StringOrNumber(allow_none=True, validate=validate_stretch_range),
        validate=validate.Length(equal=2),
        example="[0,1]",
        missing=None,
        description=(
            "Stretch range [min, max] to use for the blue band as JSON array. "
            "Min and max may be numbers to use as absolute range, or strings "
            "of the format `p<digits>` with an integer between 0 and 100 "
            "to use percentiles of the image instead. "
            "Null values indicate global minimum / maximum."
        ),
    )
    tile_size = fields.List(
        fields.Integer(),
        validate=validate.Length(equal=2),
        example="[256,256]",
        description="Pixel dimensions of the returned PNG image as JSON list.",
    )

    @pre_load
    def process_ranges(self, data: Mapping[str, Any], **kwargs: Any) -> Dict[str, Any]:
        print("OK")
        data = dict(data.items())

        for var in ("keys_list", "rgb_keys"):
            val = data.get(var)
            if val:
                if isinstance(val, str):
                    try:
                        data[var] = json.loads(val)
                    except json.decoder.JSONDecodeError as exc:
                        raise ValidationError(
                            f"Could not decode value for {var} as JSON"
                        ) from exc
                elif not isinstance(val, list):
                    raise ValidationError(f"{var} must be a list.")
        
        return data


@TILE_API.route("/combine/<int:tile_z>/<int:tile_x>/<int:tile_y>.png", methods=["GET"])
def get_combine(tile_z: int, tile_y: int, tile_x: int) -> Response:
    """Return the combined tiles from multiple datasets as a PNG image.
    ---
    get:
        summary: /combine (tile)
        description: Combine multiple datasets into one and retrieve the tiles from all datasets as a PNG image.
        parameters:
            - in: path
              schema: CombineQuerySchema
            - in: query
              schema: CombineOptionSchema
        responses:
            200:
                description: PNG image of combined tiles from all datasets
            400:
                description: Invalid body data or dataset keys
            404:
                description: No dataset found for given key combination
    """
    tile_xyz = (tile_x, tile_y, tile_z)
    return _get_combine_image(tile_xyz)

def _get_combine_image(
    tile_xyz: Tuple[int, int, int]
) -> Response:
    from terracotta.handlers.combine import combine

    options = CombineOptionSchema().load(request.args)

    keys_list = options.pop("keys_list")
    keys_list = [[key.strip() for key in keys.split("/") if key.strip()] for keys in keys_list]

    rgb_values = options.get("rgb_keys")
    tile_size = options.get("tile_size")
    
    if rgb_values is not None:
        rgb_values = (rgb_values[0], rgb_values[1], rgb_values[2])

    stretch_ranges = tuple(options.pop(k) for k in ("r_range", "g_range", "b_range"))

    image = combine(
        keys_list=keys_list,
        tile_xyz=tile_xyz,
        rgb_values=rgb_values,
        tile_size=tile_size,
        stretch_ranges=stretch_ranges
    )

    return send_file(image, mimetype="image/png")
#