# DepthAI-RTSP-HTTP

A script to extract a DepthAI camera's video and still image outputs to a RTSP server (H264 encoded) and JPEG HTTP server. Basic HTTP Authentication is supported. Based on [Luxonis](https://github.com/luxonis)' [gen2-play-encoded-stream](https://github.com/luxonis/depthai-experiments/tree/master/gen2-play-encoded-stream) and [http-server](https://github.com/luxonis/depthai-python/blob/main/examples/Script/script_http_server.py) projects.

## Usage
If you are looking for a way to re-use your DepthAI camera (e.g. Oak-D Lite) as a security camera, this is the right place! RTSP stream and snapshot JPEG through HTTP can be used to integrate to many home automation platforms such as [Homebridge](https://homebridge.io) or [Scrypted](https://github.com/koush/scrypted).

## Installation
### Ubuntu 20.04 / Debian / Raspberry Pi

```
sudo apt-get install ffmpeg
python3 -m pip install -r requirements.txt
```

### Mac OS 11 (Big Sur)

```
brew install ffmpeg
python3 -m pip install -r requirements.txt
```

(if you're using M1 processor, you might have to configure your homebrew properly to install these packages - check [this StackOverflow question](https://stackoverflow.com/q/64882584))

### [Docker](https://hub.docker.com/r/donkeystudio/depthai-rtsp-http)
Supported architectures: linux/arm/v7, linux/arm64, linux/amd64
```
docker run --rm --privileged -v /dev/bus/usb:/dev/bus/usb donkeystudio/depthai-rtsp-http:latest
```
> Note: If you are using OAK POE device on Linux host machine, you should add --network=host argument to your docker command, so depthai inside docker will be able to communicate with the OAK POE.

## Startup Configuration
```
python3 main.py --help
```
```
usage: main.py [-h] [-u USER] [-pwd PASSWORD] [-hp HTTP_PORT] [-ru RTSP_USER] [-rpwd RTSP_PWD] [-rip RTSP_HOST] [-rp RTSP_PORT] [-wt WIDTH] [-ht HEIGHT] [-qa QUALITY] [-sm SCALE_MODE]

optional arguments:
  -h, --help            show this help message and exit
  -u    USER,       --user        USER        Username to access HTTP Server (default: None)
  -pwd  PASSWORD,   --password    PASSWORD    Password to access HTTP Server (default: None)
  -hp   HTTP_PORT,  --http_port   HTTP_PORT   Port for HTTP Server (default: 8080)
  -ru   RTSP_USER,  --rtsp_user   RTSP_USER   Username to publish to RTSP Server (default: None)
  -rpwd RTSP_PWD,   --rtsp_pwd    RTSP_PWD    Password to publish to RTSP Server (default: None)
  -rip  RTSP_HOST,  --rtsp_host   RTSP_HOST   Host of the RTSP Server (default: localhost)
  -rp   RTSP_PORT,  --rtsp_port   RTSP_PORT   Port of the RTSP Server (default: 8554)
  -wt   WIDTH,      --width       WIDTH       Width of the video/preview size.
                                              In multiple of 32 (default: 1920)
  -ht   HEIGHT,     --height      HEIGHT      Height of the video/preview size.
                                              In multiple of 8 (default: 1080)
  -qa   QUALITY,    --quality     QUALITY     Video quality, from 1 to 100 (default: 100)
  -sm   SCALE_MODE, --scale_mode  SCALE_MODE  Scale or crop the video output. Default is scale.
                                              Set to false to switch to crop mode (default: True)
```

## RTSP Server

There are many RTSP server applications available, but you can consider to use [rtsp-simple-server](https://github.com/aler9/rtsp-simple-server)

## Example

Publish video stream to a RTSP server at port `8554` and host `192.168.0.50` using publish credential of `user1:password1`. HTTP server on port 8080, Basic HTTP Authentication with `user:password` as username and password.

```
python3 main.py -u user -pwd password -hp 8080 -rp 8554 -rip 192.168.0.50 -ru user1 -rpwd password1
```

To see the streamed frames, use a RTSP Client (e.g. VLC Network Stream) with the following link

```
rtsp://192.168.0.50:8554/preview
```

On Ubuntu or Mac OS, you can use `ffplay` (part of `ffmpeg` library) to preview the stream

```
ffplay rtsp://192.168.0.50:8554/preview
```

> *Note*: Username and Password to access/read the published RTSP Stream can be configured at the RTSP server.

To see the latest still image, access `http://localhost:8080/img`
