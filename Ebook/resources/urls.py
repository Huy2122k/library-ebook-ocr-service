from cloud.minio_utils import generate_presigned_url
from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource


class InternalServerError(Exception):
    pass

class PreSignUrlApi(Resource):
    # @jwt_required
    def get(self):
        try:
            # user_id = get_jwt_identity()
            params = dict(request.args)
            print(params)
            url = generate_presigned_url(params["object_key"], params["method"], params["response_type"])
            if not url:
                return Response(400)
            return {"url": url}, 200
        except Exception:
            raise InternalServerError      