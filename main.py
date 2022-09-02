from socketserver import ThreadingMixIn, TCPServer
from http.server import BaseHTTPRequestHandler
from threading import Thread
import base64
import json
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import subprocess as sp


# Parse command line arguments
parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument("-u",   "--user",      default=None,                    help="Username to access HTTP Server")
parser.add_argument("-pwd", "--password",  default=None,                    help="Password to access HTTP Server")
parser.add_argument("-hp",  "--http_port", default=8080,        type=int,   help="Port for HTTP Server")
parser.add_argument("-ru",  "--rtsp_user", default=None,                    help="Username to publish to RTSP Server")
parser.add_argument("-rpwd","--rtsp_pwd",  default=None,                    help="Password to publish to RTSP Server")
parser.add_argument("-rip", "--rtsp_host", default="localhost", type=str,   help="Host of the RTSP Server")
parser.add_argument("-rp",  "--rtsp_port", default=8554,        type=int,   help="Port of the RTSP Server")
parser.add_argument("-wt",  "--width",     default=1920,        type=int,   help="Width of the video/preview size. In multiple of 32")
parser.add_argument("-ht",  "--height",    default=1080,        type=int,   help="Height of the video/preview size. In multiple of 8")
parser.add_argument("-qa",  "--quality",   default=100,         type=int,   help="Video quality, from 1 to 100")
parser.add_argument("-sm",  "--scale_mode",default=True,        type=bool,  help="Scale or crop the video output. Default is scale. Set to false to switch to crop mode")
args = vars(parser.parse_args())

HTTP_PORT = args["http_port"]
RTSP_PORT = args["rtsp_port"]
USER      = args["user"]
PWD       = args["password"]
RTSP_USER = args["rtsp_user"]
RTSP_PWD  = args["rtsp_pwd"]
RTSP_HOST = args["rtsp_host"]
WIDTH     = args["width"]
HEIGHT    = args["height"]
QUALITY   = args["quality"]
SCALE_ON  = args["scale_mode"]

if __name__ == "__main__":
    import depthai as dai

    pipeline = dai.Pipeline()

    FPS = 30
    colorCam = pipeline.create(dai.node.ColorCamera)
    colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    colorCam.setInterleaved(False)
    colorCam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
    colorCam.setFps(FPS)
    colorCam.setPreviewSize(WIDTH, HEIGHT)
    colorCam.setVideoSize(WIDTH, HEIGHT)
    if SCALE_ON is True:
        colorCam.setIspScale(WIDTH, 1920)

    videnc = pipeline.create(dai.node.VideoEncoder)
    videnc.setDefaultProfilePreset(FPS, dai.VideoEncoderProperties.Profile.H264_MAIN)
    videnc.setKeyframeFrequency(FPS * 4)
    videnc.setQuality(QUALITY)

    colorCam.video.link(videnc.input)

    veOut = pipeline.create(dai.node.XLinkOut)
    veOut.setStreamName("encoded")
    videnc.bitstream.link(veOut.input)

    device_infos = dai.Device.getAllAvailableDevices()
    if len(device_infos) == 0:
        raise RuntimeError("No DepthAI device found!")
    else:
        print("Available devices:")
        for i, info in enumerate(device_infos):
            print(f"[{i}] {info.getMxId()} [{info.state.name}]")
        if len(device_infos) == 1:
            device_info = device_infos[0]
        else:
            val = input("Which DepthAI Device you want to use: ")
            try:
                device_info = device_infos[int(val)]
            except:
                raise ValueError("Incorrect value supplied: {}".format(val))

    if device_info.desc.protocol != dai.XLinkProtocol.X_LINK_USB_VSC:
        print(
            "Running RTSP stream may be unstable due to connection... (protocol: {})".format(device_info.desc.protocol))

    ############################
    # HTTP server
    ############################
    # VideoEncoder
    jpeg = pipeline.create(dai.node.VideoEncoder)
    jpeg.setDefaultProfilePreset(FPS, dai.VideoEncoderProperties.Profile.MJPEG)
    # Connections
    still = pipeline.create(dai.node.XLinkOut)
    still.setStreamName("jpeg")
    colorCam.still.link(jpeg.input)
    jpeg.bitstream.link(still.input)

    controlIn = pipeline.create(dai.node.XLinkIn)
    controlIn.setStreamName('control')
    controlIn.out.link(colorCam.inputControl)

    class ThreadingTCPServer(ThreadingMixIn, TCPServer):
        daemon_threads = True
        key = None

        def set_auth(self, username, password):
            self.key = base64.b64encode(bytes('%s:%s' % (username, password), 'utf-8')).decode('ascii')

        def get_auth_key(self):
            return self.key


    def serveOnPort(port, dev, user, pwd):
        HTTPHandler.dev = dev
        ctrl = dai.CameraControl()
        ctrl.setCaptureStill(True)
        HTTPHandler.ctrl = ctrl
        http_server = ThreadingTCPServer(('0.0.0.0', port), HTTPHandler)
        if user is not None and pwd is not None:
            http_server.set_auth(user, pwd)
        print("Serving at localhost:{}".format(port))
        http_server.serve_forever()


    class HTTPHandler(BaseHTTPRequestHandler):
        dev = None
        ctrl = None

        def do_AUTHHEAD(self):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Demo Realm"')
            self.send_header('Content-type', 'application/json')
            self.end_headers()

        def do_GET(self):
            key = self.server.get_auth_key()
            ''' Present frontpage with user authentication. '''
            if self.headers.get('Authorization') is None and key is not None:
                self.do_AUTHHEAD()

                response = {
                    'success': False,
                    'error': 'No auth header received'
                }

                self.wfile.write(bytes(json.dumps(response), 'utf-8'))
            elif self.headers.get('Authorization') == 'Basic ' + str(key) or key is None:
                if self.path == '/img':
                    self.dev.getInputQueue("control").send(self.ctrl)
                    image = self.dev.getOutputQueue("jpeg", maxSize=1, blocking=False).get()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(image.getData())))
                    self.end_headers()
                    self.wfile.write(image.getData())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Url not found...')


    ############################

    credential = ""
    if RTSP_USER is not None and RTSP_PWD is not None:
        credential = f"{RTSP_USER}:{RTSP_PWD}@"

    command = [
        "ffmpeg",
        "-probesize", "100M",
        "-i", "-",
        "-f", "rtsp",
        "-rtsp_transport", "tcp",
        "-framerate", "30",
        "-vcodec", "copy",
        "-v", "error",
        f"rtsp://{credential}{RTSP_HOST}:{RTSP_PORT}/preview"
    ]

    try:
        proc = sp.Popen(command, stdin=sp.PIPE)  # Start the ffmpeg process
    except:
        exit("Error: cannot run ffmpeg!\nTry running: sudo apt install ffmpeg")

    with dai.Device(pipeline, device_info) as device:
        Thread(target=serveOnPort, args=[HTTP_PORT, device, USER, PWD]).start()
        encoded = device.getOutputQueue("encoded", maxSize=40, blocking=True)
        print(f"Setup finished, RTSP stream available under \"rtsp://{RTSP_HOST}:{RTSP_PORT}/preview\"")

        try:
            while True:
                data = encoded.get().getData()  # Blocking call, will wait until new data has arrived
                proc.stdin.write(data)
        except:
            pass

        proc.stdin.close()
