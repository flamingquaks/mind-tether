import wikipedia

def lambda_handler(event,context):
    """Main Handler for Lambda. Returns Phone Data if phone is valid
    InputPayload:
        phone_model:str The model of the phone to search Wikipedia
    
    Args:
        event
        context
    """
    if event['phone_model']:
        phone_model = event['phone_model']
        print("Phone Model is %s" %(phone_model))
        print(wikipedia.search(phone_model))
        
    return {
        "statusCode":200
    }