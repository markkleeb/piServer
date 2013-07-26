## Raspberry Pi web server


This site will accept uploads from all four devices and route them to the corresponding platform (instagram, twitter, etc) 

It also stores the hash tags and questions that need to be displayed on each device.

The Pi will need to grab the question and hash tag from the server, then check credentials stored in our database using an RFID code. When verified, the Pi will accept input (text, still image, video) and send it back to the server for optimization and transmission to the platform.
