"""server/combine.py

Flask route to handle /combine calls.
"""

from typing import Tuple

from marshmallow import Schema, fields, validate, ValidationError
from flask import request, send_file, Response

from terracotta import exceptions
from terracotta.server.flask_api import TILE_API

class CombineQuerySchema(Schema):
    tile_z = fields.Int(required=True, description="Requested zoom level")
    tile_y = fields.Int(required=True, description="y coordinate")
    tile_x = fields.Int(required=True, description="x coordinate")

class CombineDatasetsSchema(Schema):
    keys_list = fields.List(
        required=True, description="List of dataset keys identifying datasets, in order",
        example=["europe/elevation", "europe/temperature", "europe/precipitation"],
        cls_or_instance=fields.String()
    )
    rgb_keys = fields.List(
        validate=validate.Length(equal=3),
        example=["R", "G", "B"],
        required=False, description="Keys for red, green, and blue bands",
        cls_or_instance=fields.String()
    )

@TILE_API.route("/combine/<int:tile_z>/<int:tile_x>/<int:tile_y>.png", methods=["POST"])
def get_combine(tile_z: int, tile_y: int, tile_x: int) -> Response:
    """Return the combined tiles from multiple datasets as a PNG image.
    ---
    post:
        summary: /combine (tile)
        description: Combine multiple datasets into one and retrieve the tiles from all datasets as a PNG image.
        requestBody:
            required: true
            content:
                application/json:
                    schema: CombineDatasetsSchema
        parameters:
            - in: path
              schema: CombineQuerySchema
        responses:
            200:
                description: PNG image of combined tiles from all datasets
            400:
                description: Invalid body data or dataset keys
            404:
                description: No dataset found for given key combination
    """
    tile_xyz = (tile_x, tile_y, tile_z)

    try:
        request_body = CombineDatasetsSchema().load(request.get_json())
    except ValidationError as err:
        raise exceptions.InvalidArgumentsError(" ".join(err.messages))

    keys_list = request_body.get("keys_list")
    keys_list = [[key.strip() for key in keys.split("/") if key.strip()] for keys in keys_list]

    rgb_keys = request_body.get("rgb_keys")
    rgb_keys = (rgb_keys[0], rgb_keys[1], rgb_keys[2])

    return _get_combine_image(keys_list, rgb_keys, tile_xyz=tile_xyz)

def _get_combine_image(
    keys_list: list[list[str]],
    rgb_keys: Tuple[str, str, str] = None,
    tile_xyz: Tuple[int, int, int] = None
) -> Response:
    from terracotta.handlers.rgb import rgb

    image = rgb(
        ["key1", "key2"],
        ("red", "green", "blue"),
        stretch_ranges=([0, 1], [0, 1], [0, 1]),
        tile_xyz=tile_xyz
    )

    return send_file(image, mimetype="image/png")
