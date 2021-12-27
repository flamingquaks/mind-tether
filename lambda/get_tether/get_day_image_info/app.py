
import boto3
import botocore
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import MindTetherCore


asset_file_path = "/opt/%s/daily_background/day_text" % (os.environ['ASSET_LAYER_NAME'])
asset_object_prefix = "images/daily_background/day_text"
default_font = MindTetherCore.Font.DEFAULT_FONT
font_path = default_font.FILE

def get_exisiting_image(day:str, screen_width:int, screen_height:int):
    image_name = "%s@%sx%s.png"%(day,screen_width,screen_height)
    image_full_path= "%s/%s"%(asset_file_path,image_name)
    if os.path.exists(image_full_path):
        return {
            "location": "local",
            "path": "%s/%s" % (asset_file_path,image_name)
        }
    else:
        s3 = boto3.resource("s3")
        try:
            s3_object_summary = s3.ObjectSummary(os.environ['MIND_TETHER_API_ASSETS'], "%s/%s" % (asset_file_path,image_name))
            print(s3_object_summary.size)
            return {
                "location":"s3",
                "key": "%s/%s"%(asset_object_prefix,image_name),
                "bucket":s3_object_summary.bucket_name
            }
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return None
            else:
                raise
        
def generate_day_text(day:str, screen_width: int, screen_height: int):
    #Need to calculate some size values based on screen size. 
    #This is super early dev and will probs change
    text_img_bottom_y = screen_height - (screen_height * .25)
    text_img_top_y = screen_height - (screen_height * .30)
    print ("upper y = %s and lower y = %s" %(text_img_top_y,text_img_bottom_y))
    text_img_height =  int(text_img_bottom_y - text_img_top_y) # Pixel count starts at top left
    print("Image height = %s" % text_img_height)
    text_img_width = screen_width
    text_img = Image.new('RGBA',(text_img_width,text_img_height))
    font_size = 1
    text_width_percent = .90
    text_height_percent = .95
    draw = ImageDraw.Draw(text_img)
    font_file=MindTetherCore.Font.DEFAULT_FONT.FILE
    print("Font File Lives at %s"%font_file)
    fnt = ImageFont.truetype(font_file,font_size)
    while fnt.getsize(day)[0] < text_width_percent*text_img.size[0] and fnt.getsize(day)[1] < text_height_percent*text_img.size[1]:
        font_size += 1
        fnt = ImageFont.truetype(font_file,font_size)
    
    draw.text((1,1),day.capitalize(),font=fnt)
    file_name="%s@%s@%sx%s.png"%(day,default_font.NAME,screen_width,screen_height)
    buffer = BytesIO()
    text_img.save(buffer,format="PNG")
    text_img.close()
    buffer.seek(0)
    s3 = boto3.resource("s3")
    s3_key="%s/%s"%(asset_object_prefix,file_name)
    s3_object = s3.Bucket(os.environ['MIND_TETHER_API_ASSETS']).put_object(
        Body=buffer,
        Key=s3_key
    )
    if s3_object and s3_object.content_length:
        return {
            "location":"s3",
            "key": "%s/%s"%(asset_object_prefix,file_name),
            "bucket":os.environ['MIND_TETHER_API_ASSETS']
        }
    else:
        return None;



def lambda_handler(event,context):
    width = int(event['width'])
    height = int(event['height'])
    print("%sx%s"%(width,height))
    day=event['day']
    day_text_image = get_exisiting_image(day,width,height)
    if day_text_image:
        return event.update({
            "statusCode": 200,
            "day_text_img" : day_text_image
        })
    elif day_text_image := generate_day_text(day,width,height):
        return event.update({
            "statusCode": 200,
            "day_text_img": day_text_image
        })
    else:
        return {
            "statusCode":500
        }