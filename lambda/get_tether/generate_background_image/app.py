from PIL import Image, ImageFont, ImageDraw
import MindTetherCore
import os
import boto3
from io import BytesIO

asset_bucket = os.environ['TETHER_ASSETS']

def generate_background_image(width: int, height: int, day: str):
    background_color = MindTetherCore.Day.get_day_color(day)
    return Image.new("RGB",(width,height),background_color)

def add_day_to_background(background_image: Image, width:int, height:int, day: str, max_screen_height_percent: int, day_vertical_start_percent: int):
    max_text_height = int(height - (height * max_screen_height_percent/100))
    max_text_width = width - 20
    text_vertical_start = int(height * day_vertical_start_percent/100)
    text_horizontal_start = 20
    text_image = Image.new("RGBA",(max_text_width,max_text_height))
    font_size = 1
    font_config = MindTetherCore.Font.DEFAULT_FONT
    font_file = f"/opt/fonts/{font_config.FILE}"
    font = ImageFont.truetype(font_file,font_size)
    while font.getsize(day)[0] < text_image.size[0] and font.getsize(day)[1] < text_image.size[1]:
        font_size += 1
        font = ImageFont.truetype(font_file,font_size)
    ImageDraw.Draw(text_image).text((1,1),day,font=font)
    background_image.paste(text_image,(text_horizontal_start,text_vertical_start),text_image)
    text_image.close()
    return background_image

def upload_image_to_s3(background_image: Image,width:int,height:int,day:str):
    image_buffer = BytesIO()
    background_image.save(image_buffer,"JPEG")
    image_buffer.seek(0)
    s3 = boto3.client("s3")
    key = MindTetherCore.AssetMapper.get_background_image_key(day,width,height)
    s3_response = s3.put_object(
        Bucket=asset_bucket,
        Key=key,
        Body=image_buffer
    )
    image_buffer.close()
    return s3_response 

def lambda_handler(event,context):
    if event.keys() >= {"width","height","day"}:
        day = str(event['day'])
        width = int(event['width'])
        height = int(event['height'])
        background_image = generate_background_image(width,height,day)
        background_image = add_day_to_background(background_image,width,height,day,15,70)
        upload_response = upload_image_to_s3(background_image,width,height,day)
        background_image.close()
        event['asset_key'] = MindTetherCore.AssetMapper.get_background_image_key(day,width,height)
        event['url'] = f"/{event['asset_key']}"
        return event
    else:
        return {
            "statusCode" : 500,
            "message": "Necessary input missing!"
        }