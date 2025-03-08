"""server/combine.py

Flask route to handle /combine calls.
"""


from marshmallow import Schema, fields
from flask import request

from terracotta.server.flask_api import TILE_API

class Datasets(Schema):
    keys = fields.String(
        required=True, description="Keys identifying dataset, in order"
    )

@TILE_API.route("/combine", methods=["POST"])
def get_combine():
    """Return the combined tiles from multiple datasets as a PNG image.
    ---
    post:
        summary: /combine (tile)
        description: Combine multiple datasets into one and retrieve the tiles from all datasets as a PNG image.
        parameters:
            - in: path
              schema: Datasets
        responses:
            200:
                description: PNG image of combined tiles from all datasets
            400:
                description: Invalid body data or dataset keys
            404:
                description: No dataset found for given key combination
    """
    print("a request was made!")
    pass