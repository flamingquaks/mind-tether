
import boto3
import os
from PIL import Image, ImageDraw
from io import BytesIO
import MindTetherCore


asset_file_path = "/opt/%s/daily_background/day_text" % (os.environ['ASSET_LAYER_NAME'])
asset_object_prefix = "images/daily_background/day_text"
default_font = MindTetherCore.Font.DEFAULT_FONT
font_path = default_font.FILE

def get_exisiting_image(day:str, screen_width:int, screen_height:int):
    image_name = "%s@%sx%s.png"%(day,screen_width,screen_height)
    if os.path.exists("%s/%s")%(asset_file_path,image_name):
        return "%s/%s" % (asset_file_path,image_name)
    else:
        s3 = boto3.resource("s3")
        s3_object_summary = s3.ObjectSummary(os.environ['MIND_TETHER_API_ASSETS'], "%s/%s" % (asset_file_path,image_name))
        if s3_object_summary and s3_object_summary.size:
            return "s3://%s/%s"%(asset_object_prefix,image_name)
        else:
            return None
        
def generate_day_text(day:str, screen_width: int, screen_height: int):
    #Need to calculate some size values based on screen size. 
    #This is super early dev and will probs change
    text_img_bottom_y = screen_height - (screen_height * .25)
    text_img_top_y = screen_height - (screen_height * .30)
    text_img_height = text_img_top_y - text_img_bottom_y
    text_img_width = screen_width
    text_img = Image.new('RGBA',(text_img_width,text_img_height))
    font_size = 1
    text_width_percent = .90
    draw = ImageDraw.Draw(text_img)
    fnt = ImageDraw.truetype('/opt/%s/fonts/%s'%(os.environ['ASSET_LAYER_NAME'],MindTetherCore.Font.DEFAULT_FONT.FILE),
                             font_size)
    while fnt.getsize(day)[0] < text_width_percent*text_img.size[0]:
        font_size += 1
        fnt = ImageDraw.TrueType('/opt/%s/fonts/%s'%(os.environ['ASSET_LAYER_NAME'],MindTetherCore.Font.DEFAULT_FONT.FILE),
                             font_size)
    
    draw.text((0,0),day.capitalize,font=fnt)
    file_name="%s@%s@%sx%s.png"%(day,default_font.NAME,screen_width,screen_height)
    tmp_file_path = "/tmp/%s"%(file_name)
    text_img.save(tmp_file_path,format="PNG")
    s3 = boto3.resource("s3")
    s3_key="%s/%s"%(asset_object_prefix,file_name)
    s3_object = s3.Bucket(os.environ['MIND_TETHER_API_ASSETS']).put_object(
        file=tmp_file_path,
        key=s3_key
    )
    if s3_object and s3_object.content_length:
        return "%s/%s"%(asset_object_prefix,file_name)
    else:
        return None;



def lambda_handler(event,context):
    screen_width = event['screen_width']
    screen_height = event['screen_height']
    day=event['day']
    day_text_image = get_exisiting_image(day,screen_height,screen_height)
    if day_text_image:
        return {
            "day_text_image" : day_text_image
        }
    elif day_text_image := generate_day_text(day,screen_width,screen_height):
        return {
            "day_text_image": day_text_image
        }
    else:
        return {
            "statusCode":500
        }