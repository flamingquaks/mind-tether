from MindTetherCore import URLShortener


def lambda_handler(event, context):
    if event['url']:
        long_url = event['url']
        short_url = URLShortener.shorten_url(long_url)
        event['short_url'] = short_url
        return event
    else:
        return 400
        