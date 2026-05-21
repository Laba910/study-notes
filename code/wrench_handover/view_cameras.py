#!/usr/bin/env python3
"""
카메라 3대 실시간 뷰어 - 녹화 중 모니터링용
실행: python3 view_cameras.py
종료: q 키
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import cv2
import numpy as np
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from homography_utils import load_homography, apply_homography, draw_grid

ROI = (0, 0, 640, 640)  # cam_top ROI = 버드아이뷰 전체 (호모그래피 적용 후 기준)
_H, _H_SIZE = load_homography(os.path.join(os.path.dirname(__file__), 'homography.json'))

class CameraViewer(Node):
    def __init__(self):
        super().__init__('camera_viewer')
        self.frames = {'cam_top': None, 'pair1': None, 'pair2': None}

        self.create_subscription(CompressedImage, '/cam_top/image_raw/compressed',
            lambda msg: self.cb(msg, 'cam_top'), 1)
        self.create_subscription(CompressedImage, '/pair1/cam/image_raw/compressed',
            lambda msg: self.cb(msg, 'pair1'), 1)
        self.create_subscription(CompressedImage, '/pair2/cam/image_raw/compressed',
            lambda msg: self.cb(msg, 'pair2'), 1)

    def cb(self, msg, key):
        arr = np.frombuffer(msg.data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            self.frames[key] = img

    def render(self, show_grid=False):
        H, W = 240, 320
        black = np.zeros((H, W, 3), dtype=np.uint8)
        panels = []

        # cam_top: FULL + ROI 동시 표시
        top = self.frames['cam_top']
        if top is not None:
            full = cv2.resize(top, (W, H))
            x1, y1, x2, y2 = ROI
            roi_img = cv2.resize(top[y1:y2, x1:x2], (W, H))
            # ROI 박스 표시
            sx = W / top.shape[1]
            sy = H / top.shape[0]
            cv2.rectangle(full,
                (int(x1*sx), int(y1*sy)),
                (int(x2*sx), int(y2*sy)),
                (0, 255, 0), 2)
            cv2.putText(full, 'cam_top FULL', (6, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
            cv2.putText(roi_img, 'cam_top ROI', (6, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
            bird_src = apply_homography(top, _H, _H_SIZE) if _H is not None else top
            if show_grid:
                bird_src = draw_grid(bird_src, mat_mm=(600, 400), output_size=_H_SIZE)
            bird = cv2.resize(bird_src, (W, H))
            cv2.putText(bird, 'cam_top BIRD' + (' [G]' if show_grid else ''), (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 128), 1)
            panels.append(full)
            panels.append(bird)
        else:
            panels.append(black.copy())
            panels.append(black.copy())

        # pair1/cam
        p1 = self.frames['pair1']
        if p1 is not None:
            img = cv2.resize(p1, (W, H))
            cv2.putText(img, 'pair1/cam', (6, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 1)
            panels.append(img)
        else:
            panels.append(black.copy())

        # pair2/cam
        p2 = self.frames['pair2']
        if p2 is not None:
            img = cv2.resize(p2, (W, H))
            cv2.putText(img, 'pair2/cam', (6, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 100, 100), 1)
            panels.append(img)
        else:
            panels.append(black.copy())

        # 2x2 그리드
        row1 = np.hstack(panels[:2])
        row2 = np.hstack(panels[2:])
        grid = np.vstack([row1, row2])
        cv2.imshow('Camera Monitor (q: quit)', grid)


def main():
    rclpy.init()
    node = CameraViewer()
    show_grid = False
    print("카메라 뷰어 시작 (q: 종료 / g: 격자 on/off)")

    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.03)
        node.render(show_grid)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('g'):
            show_grid = not show_grid
            print(f"격자: {'ON' if show_grid else 'OFF'}")

    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
