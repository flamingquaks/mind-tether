from MindTetherCore import URLShortener


def lambda_handler(event, context):
    if event['url']:
        long_url = event['url']
        return URLShortener.shorten_url(long_url)
    else:
        return 400
        