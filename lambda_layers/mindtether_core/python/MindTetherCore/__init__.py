from os import path,environ
import boto3
import botocore
import string
import random

    
    
    # def __init__(self) -> None:
    #     pass


_font_dir = path.join("/opt/%s" % (environ['ASSET_LAYER_NAME']),"fonts")
class Font():
    def __init__(self) -> None:
        pass
    class THE_BOLD_FONT:
        FILE = "%s/theboldfont.ttf" % (_font_dir)
        NAME = "TheBoldFont"
    
    DEFAULT_FONT = THE_BOLD_FONT
    
    
class Day():
    __days = {
        "monday": {
            "color": (242,212,214)
        },
        "tuesday": {
            "color": (238,232,184)
        },
        "wednesday": {
            "color": (242,139,132)
        },
        "thursday": {
            "color":(168,206,215)
        },
        "friday":{
            "color": (234,195,138)
        },
        "saturday":{
            "color":(183,181,208)
        },
        "sunday":{
            "color":(166,209,200)
        }
    }
    
    def __init__(self):
        pass
    
    
    @classmethod
    def get_day_color(self, day: str):
        return Day.__days[day.lower()]['color']
    
class URLShortener:
    def __init__(self) -> None:
        pass
    
    def shorten_url(long_url:str, short_url_bucket:str = None, short_url_host:str = None):
        """URLShortener.shorten_url
        
        This takes the long URL and generates a URL shortener link.
        
        NOTE: if optional values aren't provided, this method will attempt to use 
        the caller's environment variables. Make sure they are set on the caller.
        
        Additionally, ensure that the calling function has the necessary permissions
        to the AWS resources. 

        Args:
            long_url (str): URL that needs to be shortened
            short_url_bucket (str, optional): [description]. Defaults to environ['SHORT_URL_BUCKET'].
            short_url_host (str, optional): [description]. Defaults to ['SHORT_URL_HOST'].

        Raises:
            Exception: If necessary values are missing, an exception will be thrown

        Returns:
            [str]: Shortened URL
        """
        if not long_url:
            raise Exception("Missing long URL!")
        if not short_url_bucket or not short_url_host:
            short_url_bucket = environ['SHORT_URL_BUCKET']
            short_url_host = environ['SHORT_URL_HOST']
            if not short_url_bucket or not short_url_host:
                raise Exception("Error! Either the short_url_bucket or short_url_host values were not provided \
                    and were not set in the environment variables.")
        
        # generate a random string of n characters, lowercase and numbers
        def generate_random(n):
            return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(n))

        # checks whether an object already exists in the Amazon S3 bucket
        # we do a head_object, if it throws a 404 error then the object does not exist
        def exists_s3_key(s3_client, bucket, key):
            try:
                resp = s3_client.head_object(Bucket=bucket, Key=key)
                return True
            except botocore.exceptions.ClientError as e:
                # if ListBucket access is granted, then missing file returns 404
                if (e.response['Error']['Code'] == "404"): return False
                # if ListBucket access is not granted, then missing file returns 403 (which is the case here)
                if (e.response['Error']['Code'] == "403"): return False
                print(e.response)
                raise e 
            


        ### Generate a short id for the redirect
        # check if short_key object already exists - collision could occur
        s3 = boto3.client('s3')

        while (True):
            short_id = generate_random(7)
            short_key = "u/" + short_id
            if not(exists_s3_key(s3, short_url_bucket, short_key)):
                break
            else:
                print("We got a short_key collision: " + short_key + ". Retrying.")

        print("We got a valid short_key: " + short_key)

        ### Third step: create the redirection object in the S3 bucket
        resp = s3.put_object(Bucket=short_url_bucket,
                            Key=short_key,
                            Body=b"",
                            WebsiteRedirectLocation=long_url,
                            ContentType="text/plain")

        public_short_url = "https://" + short_url_host + "/" + short_id;

        return public_short_url