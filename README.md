
# Mind Tether

Many individuals in many stages of life struggle to stay grounded to the day to day. Whether it's pain or medication induced brain fog, damensia, or a multide of ther things, keeping oneself connected to each day can be an uphill battle.

Mind Tether is designed to provide users with visual indicators in convienient locations to help mentally tether someone back to what the now is.


The current design MVP takes advantage of the programability of iPhones through Shortcuts. See [SiriShortcut.md](SiriShortcut.md) for the latest released version of the shortcut. It will have dynamic variables it will pass. In AWS, a unique phone background image is created, saved in S3 and a pre-signed URL is generated. The shortcut will then download the file from the provided background URL. The S3 lifecycle policies will expire images after 60 seconds. 

--- 

Some additional notes:

Because the Presigned URL for the S3 object is so long, it gets truncated in the API response. To solve for that I have implemented a URL shortner solution as described in [this](https://aws.amazon.com/blogs/compute/build-a-serverless-private-url-shortener/) blog post. While this is effective, the shortener should be integrated directly into this application to reduce latency and cost while improving effeciency and simplicity. 

In the meantime, using a third-party shortner has allowed for me to push those changes to post-MVP

--- 
My immediate need was for this to work with iPhone 13 Pro screen size. Much of what is included is hardcoded to that. I will work to build out Phone objects with constants to allow various models to be supported.


---


## Technical Design
The Siri Shortcut is fairly simple. It hits the api, the api gives it a url, it downloads an image from the URL and sets it as the background.
As far as the backend, it's running on serverless resources in AWS that are Edge optimized. 
The infrastructure is built and deployed using the AWS Cloud Development Kit (CDK).
The API is powered by Amazon API Gateway backed by AWS Lambda functions. 

__Currently__ the API endpoint receives the request with the current day provided. The lambda then fires up, opens the background image for the specific day and phone model (currently hardcoded to iPhone 13 Pro). Once it's open, it 
draws the text of the day and then saves the image with a UUID in S3. After it is saved, a S3 pre-signed URL is generated. Because of the URL length, the link is sent to a private URL shortner. The shortener currently runs in its own stack. 

### A little bit a reasoning behind my design
There are few aspects I'm trying to keep in consideration. First and formost, I'd really rather this not cost much, hence the serverless. I also don't want to deal with scaling and infrastructure management, another win for serverless. One of the key questions I had to answer was the location of the static assets used as the image components. Three options came to mind: Lambda Layer, S3 Bucket or EFS. Ultimately, I chose Lambda Layer, mostly because S3 means downloading files (which may not take that long, especially if you used a private endpoint) whereas 
Lambda layers is directly attached to the lambda, creating high speed access to the files. EFS was also a high candidate for asset storage. With EFS, I can pull the images fairly quickly. In the initialization phase of the Lambda, the layer has to get attached or EFS needs to be mounted. Either way, both of these options added a slight increase on startup. 

After reviewing my options, I chose Lambda Layers. Since currently I have a low volume of data in the assets, EFS would be cost prohibitive. S3 on the other hand means constant get_object calls which isn't so efficient. So Lambda Layers won out. BUT I have plans for the future.

The overall goal is to all the infrastructure to enable plugins, addons, etc. To do this, I plan orchestrate the image creation through Step Functions. As more functionality comes in, they can be incorporated into the workflow. 
As the shift to an orchestrated model happens, this will be when the switch to EFS most likely will come into play. 
Since the image may be manipulated multiple times, it needs to be persistently stored outstand the lambda (so Layers are not possible in this use case). With EFS, I can store the static assets in a read only section of the cluster while having dynamic assets stored elsewhere, accessible to multiple lambda functions along the workflow. TTLs will help ensure image storage costs are kept in check. 

### Why are you drawing the day on the image if you already have 7 background bases?
I wanted to include this here as it seemed kinda silly and overengineered at this point to write text on an image that is already specific to that day. This goals is focused towards my long-term goals. As more data is able to be presented to the end-user in different areas of the image, I don't want to build in a manner that is too static for change. 


## Contributing
The goal is to truly open-source the project. That being said, I want to lay some foundation before accepting new contributores. Once the app has a core functionality for a broader range of phones, I hope to welcome curious contributors!
## Contact Me!
I love feedback, but I also need to not have feedback in every direction. Please post feedback on GitHub. ❤️