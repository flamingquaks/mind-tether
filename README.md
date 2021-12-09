
# Mind Tether

Mind Tether is an app designed to provide small reminders that can help you feel more tethered to reality when remembering is a challenge. 


The current design will take advantage of the programability of iPhones through Shortcuts. The shortcut will be created and set to run on a schedule. It will have dynamic variables it will pass. In AWS, a unique phone background image is created, saved in S3 and a pre-signed URL is generated. The shortcut will then download the file from the provided background URL. The S3 lifecycle policies will expire images after 60 seconds. 

--- 

Some additional notes:

Because the Presigned URL for the S3 object is so long, it gets truncated in the API response. To solve for that I have implemented a URL shortner solution as described in [this](https://aws.amazon.com/blogs/compute/build-a-serverless-private-url-shortener/) blog post. While this is effective, the shortener should be integrated directly into this application to reduce latency and cost while improving effeciency and simplicity. 

In the meantime, using a third-party shortner has allowed for me to push those changes to post-MVP

--- 
My immediate need was for this to work with iPhone 13 Pro screen size. Much of what is included is hardcoded to that. I will work to build out Phone objects with constants to allow various models to be supported.


---
Some future items:
* Custom daily background
* Weather Data
* Background layers based on time of day
