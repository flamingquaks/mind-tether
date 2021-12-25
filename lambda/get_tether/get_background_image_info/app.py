import os
import boto3
import botocore
from PIL import Image
from io import BytesIO

import MindTetherCore

asset_file_path = "/opt/%s/daily_background" % (os.environ['ASSET_LAYER_NAME'])
asset_object_prefix = "images/daily_background"



def get_background_if_exists(width: int, height: int, day: str):
    """Gets the background image to be used

    Args:
        width (int): Screen width
        height (int): Screen height
        day (str): The day of week

    Returns:
        [str]: The file path or s3 object path of the background image if it exists. None if it doesn't exists.
    """
    image_name = "%s@%sx%s.jpeg" % (day,width,height)
    file_path = "%s/%s" % (asset_file_path,image_name)
    if os.path.exists(file_path):
        return file_path
    else:
        try:
            s3 = boto3.resource("s3")
            s3_object_summary = s3.ObjectSummary(os.environ['MIND_TETHER_API_ASSETS'],'%s/%s' % (asset_object_prefix,image_name))
            print(s3_object_summary.size)
            return '%s/%s' % (asset_object_prefix,image_name)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return None
            else:
                raise

def generate_new_background_image(width: int, height: int, day: str):
    """Generate a new background image

    Args:
        width (int): The image width
        height (int): The image height
        day (str): The day

    Returns:
        str: The s3 object key if upload is successful, None if upload was not
            successful.
    """
    bkg_img = Image.new('RGB',(width,height),MindTetherCore.Day.get_day_color(day))
    buffer = BytesIO()
    bkg_img.save(buffer,"JPEG")
    bkg_img.close()
    buffer.seek(0)
    s3 = boto3.resource("s3")
    image_name = "%s@%sx%s.jpeg" % (day,width,height)
    s3_object = s3.Bucket(os.environ['MIND_TETHER_API_ASSETS']).put_object(
        Key="%s/%s" % (asset_object_prefix,image_name),
        Body=buffer)
    if s3_object.content_length > 0:
        return "s3://%s/%s/%s" % (os.environ['MIND_TETHER_API_ASSETS'],asset_object_prefix,image_name)
    else:
        return None

def lambda_handler(event,context):
    """Generate Background Image Lambda Handler Function

    Args:
        event 
        context 

    """
    if event.keys() >= {"width", "height","day"}:
        width = int(event['width'])
        height = int(event['height'])
        day = event['day']
    else:
        return {
            "statusCode":400,
            "message": "Bad request. Ensure width, height and day are provided!"
        }
    
    if background := get_background_if_exists(width,height,day):
        return {
            "statusCode":200,
            "bkg_file_location" : background,
            "screen_width" : width,
            "screen_height" : height,
            "day": day
        }
    elif background := generate_new_background_image(width,height,day):
        return {
            "statusCode": 200,
            "bkg_file_location": background,
            "screen_width" : width,
            "screen_height" : height,
            "day":day
        }
    else:
        return {
            "statusCode": 400
        }
        
