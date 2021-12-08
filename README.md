
# Mind Tether

Mind Tether is an app designed to provide small reminders that can help you feel more tethered to reality when remembering is a challenge. 


The current design will take advantage of the programability of iPhones through Shortcuts. The shortcut will be created and set to run on a schedule. It will have dynamic variables it will pass. In AWS, a unique phone background image is created, saved in S3 and a pre-signed URL is generated. The shortcut will then download the file from the provided background URL. The S3 lifecycle policies will expire images after 60 seconds. 
