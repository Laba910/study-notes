#!/bin/bash
source /opt/ros/jazzy/setup.bash
source /home/laba/ros2_ws/install/setup.bash
# ros_jazzy venv의 GUI cv2를 최우선 로드
export PYTHONPATH=/home/laba/venv/ros_jazzy/lib/python3.12/site-packages:$PYTHONPATH
exec /home/laba/venv/bin/python3 /home/laba/scripts/omx_modes/camera_viewer_v2.py
