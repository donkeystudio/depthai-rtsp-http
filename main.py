import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

import threading
from socketserver import ThreadingMixIn, TCPServer
from http.server import BaseHTTPRequestHandler
from threading import Thread
import base64
import json
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


class RtspSystem(GstRtspServer.RTSPMediaFactory):
    def __init__(self, **properties):
        super(RtspSystem, self).__init__(**properties)
        self.data = None
        self.launch_string = 'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME ! h264parse ! ' \
                             'rtph264pay name=pay0 config-interval=1 name=pay0 pt=96 '

    def send_data(self, data):
        self.data = data

    def start(self):
        t = threading.Thread(target=self._thread_rtsp)
        t.start()

    def _thread_rtsp(self):
        loop = GLib.MainLoop()
        loop.run()

    def on_need_data(self, src, length):
        if self.data is not None:
            retval = src.emit('push-buffer', Gst.Buffer.new_wrapped(self.data.tobytes()))
            if retval != Gst.FlowReturn.OK:
                print(retval)

    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)

    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)


class RTSPServer(GstRtspServer.RTSPServer):
    def __init__(self, user, password, **properties):
        super(RTSPServer, self).__init__(**properties)
        auth = GstRtspServer.RTSPAuth()
        token = GstRtspServer.RTSPToken()
        token.set_string('media.factory.role', user)
        basic = GstRtspServer.RTSPAuth.make_basic(user, password)
        auth.add_basic(basic, token)
        self.set_auth(auth)
        self.set_service(str(RTSP_PORT))

        permissions = GstRtspServer.RTSPPermissions()
        permissions.add_permission_for_role(user, "media.factory.access", True)
        permissions.add_permission_for_role(user, "media.factory.construct", True)

        self.rtsp = RtspSystem()
        self.rtsp.set_shared(True)
        self.rtsp.add_role_from_structure(permissions.get_role(user))
        self.get_mount_points().add_factory("/preview", self.rtsp)
        self.attach(None)
        Gst.init(None)
        self.rtsp.start()

    def send_data(self, data):
        self.rtsp.send_data(data)


# Parse command line arguments
parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument("-u", "--user", default=None, help="Username")
parser.add_argument("-pwd", "--password", default=None, help="Password")
parser.add_argument("-hp", "--http_port", default=8080, type=int, help="Port for HTTP Server")
parser.add_argument("-rp", "--rtsp_port", default=8554, type=int, help="Port for RTSP Server")
args = vars(parser.parse_args())

HTTP_PORT = args["http_port"]
RTSP_PORT = args["rtsp_port"]
USER = args["user"]
PWD = args["password"]


if __name__ == "__main__":
    import depthai as dai

    server = RTSPServer(USER, PWD)

    pipeline = dai.Pipeline()

    FPS = 30
    colorCam = pipeline.create(dai.node.ColorCamera)
    colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    colorCam.setInterleaved(False)
    colorCam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
    colorCam.setFps(FPS)

    videnc = pipeline.create(dai.node.VideoEncoder)
    videnc.setDefaultProfilePreset(1280, 720, FPS, dai.VideoEncoderProperties.Profile.H264_MAIN)
    videnc.setKeyframeFrequency(FPS * 4)
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

    with dai.Device(pipeline, device_info) as device:
        Thread(target=serveOnPort, args=[HTTP_PORT, device, USER, PWD]).start()
        encoded = device.getOutputQueue("encoded", maxSize=40, blocking=True)
        print("Setup finished, RTSP stream available under \"rtsp://localhost:{}/preview\"".format(RTSP_PORT))
        while True:
            data = encoded.get().getData()
            server.send_data(data)
