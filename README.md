# depthai-rtsp-http

A script to extract a DepthAI camera's video and still image outputs to a RTSP H264 video stream and JPEG HTTP server. Basic HTTP Authentication is supported. Based on [Luxonis](https://github.com/luxonis)' [gen2-rtsp-streaming](https://github.com/luxonis/depthai-experiments/tree/master/gen2-rtsp-streaming) and [http-server](https://github.com/luxonis/depthai-python/blob/main/examples/Script/script_http_server.py) projects

## Installation
### Ubuntu 20.04 / Debian / Raspberry Pi

```
sudo apt-get install ffmpeg gstreamer-1.0 gir1.2-gst-rtsp-server-1.0 libgirepository1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-plugins-base
python3 -m pip install -r requirements.txt
```

### Mac OS 11 (Big Sur)

```
brew install pkg-config cairo gobject-introspection gst-plugins-bad gst-plugins-base gstreamer gst-rtsp-server ffmpeg gst-plugins-good
python3 -m pip install -r requirements.txt
```

(if you're using M1 processor, you might have to configure your homebrew properly to install these packages - check [this StackOverflow question](https://stackoverflow.com/q/64882584))

## Usage
```
python3 main.py --help
```
```
usage: main.py [-h] [-u USER] [-pwd PASSWORD] [-hp HTTP_PORT] [-rp RTSP_PORT]

optional arguments:
  -h,            --help                 show this help message and exit
  -u USER,       --user      USER       Username (default: None)
  -pwd PASSWORD, --password  PASSWORD   Password (default: None)
  -hp HTTP_PORT, --http_port HTTP_PORT  Port for HTTP Server (default: 8080)
  -rp RTSP_PORT, --rtsp_port RTSP_PORT  Port for RTSP Server (default: 8554)
```

## Example

Run RTSP server on port 8554, HTTP server on port 8080, Basic HTTP Authentication with `user:password` as username and password.

```
python3 main.py -u user -pwd password -hp 8080 -rp 8554
```

To see the streamed frames, use a RTSP Client (e.g. VLC Network Stream) with the following link

```
rtsp://localhost:8554/preview
```

On Ubuntu or Mac OS, you can use `ffplay` (part of `ffmpeg` library) to preview the stream

```
ffplay rtsp://localhost:8554/preview
```

To see the latest still image, access `http://localhost:8080/img`
