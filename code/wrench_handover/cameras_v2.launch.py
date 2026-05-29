#!/usr/bin/env python3
#
# Launch cameras for OMX IL data collection (pair1 전용).
# mjpeg2rgb → mjpeg 변경 (mjpeg2rgb 크래시 수정)
# pair2 제거 (미연결)
#
# Topics:
#   /cam_top/image_raw/compressed  - overhead full view
#   /pair1/cam/image_raw/compressed - pair1 follower camera

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cam_top = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        namespace='cam_top',
        output='screen',
        parameters=[{
            'video_device': '/dev/cam_top',
            'image_width': 640,
            'image_height': 480,
            'framerate': 30.0,
            'pixel_format': 'yuyv',
        }],
    )

    cam_pair1 = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        namespace='pair1/cam',
        output='screen',
        parameters=[{
            'video_device': '/dev/cam_pair1',
            'image_width': 640,
            'image_height': 480,
            'framerate': 10.0,
            'pixel_format': 'yuyv',
        }],
    )

    return LaunchDescription([cam_top, cam_pair1])
