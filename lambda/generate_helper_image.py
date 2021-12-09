import requests
import boto3
import requests
import json

from PIL import (
    Image, 
    ImageDraw, 
    ImageFont
    )
import base64
import os
from io import BytesIO
from uuid import uuid4

days= dict({
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
})

def upload_image_to_s3 (uuid_path, img):
    # bucket_name = os.environ['S3_BUCKET']
    bucket_name="phonebackgroundhelperstack-assetbucket1d025086-q1yucn7kpzas"
    s3 = boto3.client("s3")
    s3_response = s3.put_object(Bucket=bucket_name,
                  Key=uuid_path,
                  Body=img)
    s3_presigned_response = s3.generate_presigned_url(
        'get_object', Params = {
            'Bucket': bucket_name,
            'Key': uuid_path
        }, ExpiresIn=60
    )
    return s3_presigned_response

def _get_base_day_image(day: str, phone_model: str):
    #TODO Validate day string and phone_model strings are approved. 
    return Image.open("/opt/images/daily_background/%s@%s.jpg" % (day,phone_model))

def _generate_day_text_image(day:str, background: Image):
    fnt = ImageFont.truetype("/opt/fonts/theboldfont.ttf", 200)
    draw = ImageDraw.Draw(background,"RGB")
    draw.text((25,2000),day.capitalize(),fill=(255,255,255), font=fnt)
    return background

def generate_image(*args, day:str=None, phone_model:str=None):
    background = _get_base_day_image(day,phone_model)
    _generate_day_text_image(day,background)
    return background

def shorten_url(img_url:str):
    # print("IMAGE URL IS\n %s" % (img_url))
    response = requests.post("https://link.mindtether.rudy.fyi/admin_shrink_url",
    json={
        "url_long": img_url,
        "cdn_prefix": "link.mindtether.rudy.fyi"
    },allow_redirects=True)
    response_values = json.loads(response.text)
    if response.status_code == 200:
        response.close()
        return response_values['url_short']
    else:
        response.close()
        return response.status_code

def lambda_handler(event, context):
    print("EVENT object = %s" % (event))
    phone_model="iphone13pro"
    width = 1170
    height = 2532
    day = event['queryStringParameters']['day']
    uuid_name = "%s.jpeg" % (uuid4())
    uuid_path = "images/daily-background/%s" % uuid_name
    buffer = BytesIO()
    img = generate_image(day=day,phone_model=phone_model)
    img.save(buffer, "JPEG")
    img.close()
    buffer.seek(0)
    image_url = upload_image_to_s3(uuid_path, buffer)
    image_url = shorten_url(image_url)
    return {
        'statusCode': 200,
        'body': {
            'image_url': image_url
        }
    }
    