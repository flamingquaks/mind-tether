import boto3
from uuid import uuid4
from PIL import Image
from io import BytesIO
from os import environ


asset_bucket = environ['MIND_TETHER_API_ASSETS']
request_table_name = environ['REQUEST_TABLE_NAME']
generated_assets_prefix = "get-tether/generated"

def get_s3_image(key:str,bucket:str,type:str):
    s3 = boto3.client("s3")
    file_name = key[key.rindex("/")+1]
    file_path = "/tmp/%s-%s"%(type,file_name)
    s3.download_file(bucket, key, file_path)
    return file_path
    

def lambda_handler(event,context):
    if event.keys() >= {"width", "height","day", \
        "bkg_img", "day_text_img", "requestId"}:
        width = event['width']
        height = int(event['height'])
        day = event["day"]
        bkg_img = event['bkg_img']
        request_id = event['requestId']
        day_text_img = event['day_text_img']
        if bkg_img['location'] == "s3":
            bkg_img['path'] = get_s3_image(bkg_img['key'],\
                bkg_img['bucket'],"BKG")
            
        if day_text_img['location'] == "s3":
            day_text_img['path'] = get_s3_image(day_text_img['key'],\
                day_text_img['bucket'], "DAYTEXT")
        bkg_image = Image.open(bkg_img['path']) 
        day_text_image = Image.open(day_text_img['path'])
        day_text_image_height = int(day_text_image.height)
        free_space_top_percent = 65
        free_space_bottom_percent = 80
        free_space_top_y = int(height*free_space_top_percent/100)
        free_space_bottom_y = int(height*free_space_bottom_percent/100)
        
        vertical_offset = ((free_space_bottom_y-free_space_top_y) - day_text_image_height)/2
        bkg_image.paste(day_text_image,(5,int(free_space_top_y+vertical_offset)),day_text_image)
        day_text_image.close()
        image_name = "%s.jpeg"%(uuid4())
        buffer = BytesIO()
        bkg_image.save(buffer,"JPEG")
        bkg_image.close()
        buffer.seek(0)
        s3 = boto3.client("s3")
        asset_key="%s/%s"%(generated_assets_prefix,image_name)
        s3_response = s3.put_object(
            Bucket=asset_bucket,
            Key=asset_key,
            Body=buffer
        )
        s3_presigned_url = s3.generate_presigned_url(
            'get_object', Params = {
                'Bucket' : asset_bucket,
                'Key': asset_key
            }, ExpiresIn=60
        )
        
        event['generatedImageURL'] = s3_presigned_url
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(request_table_name)
        update_response = table.update_item(
            Key={
                "requestId":request_id
            },
            UpdateExpression="set create_status=:s, image_url=:u",
            ExpressionAttributeValues={
                ':s': "COMPLETE",
                ':u': s3_presigned_url
            }
        )
        return event
