FROM luxonis/depthai-library:latest

WORKDIR /donkeystudio
ADD main.py .

ENV TZ="Asia/Singapore"
RUN ln -snf /user/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get -y update
RUN apt-get install -y udev
RUN apt-get install -y ffmpeg
RUN echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | tee /etc/udev/rules.d/80-movidius.rules
VOLUME [ "/dev/bus/usb"]

CMD [ "python3", "./main.py" ]