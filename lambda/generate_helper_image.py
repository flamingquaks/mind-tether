import uuid
import boto3
from PIL import Image
import base64
import os
from io import BytesIO
from uuid import uuid4

days={
    'sunday' :{
        'color': (165,209,200)
    },
    'monday':{
        'color': (242,212,213) 
    },
    'tuesday':{
        'color': (238,231,184)
    },
    'wednesday':{
        'color': (241,139,132)
    },
    'thursday':{
        'color': (168,206,215)
    },
    'friday':{
        'color': (234,195,138)
    },
    'saturday':{
        'color': (183,181,204)
    }
}
def upload_image_to_s3 (uuid_path, img):
    bucket_name = os.environ['S3_BUCKET']
    s3 = boto3.client("s3")
    s3_response = s3.put_object(Bucket=bucket_name,
                  Key=uuid_path,
                  Body=img)
    print(s3_response)
    return uuid_path;


def lambda_handler(event, context):
    print("layer info: %s" % (os.listdir("/opt/")))

    width = 1170
    height = 2532
    day = event['body']['day']
    print('day requested is %s' % (day))
    # uuid_name = "%s.jpeg" % (uuid4())
    uuid_name = '%s@iPhone13Pro' % (day)
    uuid_path = "/assets/images/daily-background/%s" % uuid_name
    print("color is %" % (days[day]))
    print("color is %" % (days[day]['color']))
    img = Image.new("RGB", [width,height],color=days[day]['color'])
    img.format = "JPEG"
    buffer = BytesIO()
    img.save(buffer, "JPEG")
    img.close()
    buffer.seek(0)
    image_url = upload_image_to_s3(uuid_path, buffer)
    return {
        'statusCode': 200,
        'body': {
            "ImageUUID":uuid_name
        }
    }