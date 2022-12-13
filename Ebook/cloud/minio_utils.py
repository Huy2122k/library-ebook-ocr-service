from datetime import *

from dotenv import dotenv_values
from minio import Minio
from minio.datatypes import PostPolicy

config = dotenv_values("cloud/.env.cloud")

print(config)

minio_client = Minio(
    endpoint=config["HOST"],
    access_key=config["ACCESS_KEY"],
    secret_key=config["SECRET_KEY"],
    secure=False
)
buckets = minio_client.list_buckets()
for bucket in buckets:
    print(bucket.name, bucket.creation_date)
def create_if_not_found(bucket_name):
    try:
        if minio_client.bucket_exists(f"{config['BASE_BUCKET']}/{bucket_name}"):
            return True
        else:
            minio_client.make_bucket(f"{config['BASE_BUCKET']}/{bucket_name}")
            return True
    except Exception as e:
        return False

# def get_put_presigned_url(bucket, object_key, expires_hours = 2 ):
#     try:
#         url = minio_client.presigned_put_object(
#             bucket, object_key, expires=timedelta(hours=2),
#         )
#         return url 
#     except Exception as e:
#         return None

#     # Get presigned URL string to upload data to 'my-object' in
#     # 'my-bucket' with two hours expiry.

# def get_post_presigned(bucket, object_key, expires_hours = 2 ):
#     policy = PostPolicy(
#         bucket , datetime.utcnow() + timedelta(days=10),
#     )
#     policy.add_starts_with_condition("key", "my/object/prefix/")
#     policy.add_content_length_range_condition(
#         1*1024*1024, 10*1024*1024,
#     )
#     form_data = minio_client.presigned_post_policy(policy)


def get_image_post_presigned_url(object_key, expires_hours = 2 ):
    try:
        url = minio_client.get_presigned_url(
            "PUT",
            config['BASE_BUCKET'],
            object_key,
            expires=timedelta(hours=expires_hours),
            response_headers={"response-content-type": "application/json"},
        )
        return url
    except Exception as e:
        print(e.message)
        return None

def generate_presigned_url(object_key, method, response_type ="application/json", expires_hours = 2 ):
    try:
        print(response_type)
        if method not in ("GET", "PUT"):
            return None
        url = minio_client.get_presigned_url(
            method,
            config['BASE_BUCKET'],
            object_key,
            expires=timedelta(hours=expires_hours),
            response_headers={"response-content-type": response_type },
        )
        return url
    except Exception as e:
        print(e.message)
        return None