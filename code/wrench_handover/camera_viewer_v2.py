#!/usr/bin/env python3
"""
3개 카메라 실시간 뷰어 (tkinter + PIL, cv2 GUI 불필요)
사용법: python3 camera_viewer_v2.py
키: q 또는 창 닫기 → 종료
"""
import sys, os, threading
import numpy as np
import cv2
import tkinter as tk
from PIL import Image, ImageTk
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

sys.path.insert(0, os.path.expanduser('~/datasets/wrench_handover'))
from homography_utils import load_homography, apply_homography

_H, _H_SIZE = load_homography(os.path.expanduser('~/datasets/wrench_handover/homography.json'))

W, H = 640, 480


class CameraViewer(Node):
    def __init__(self):
        super().__init__('camera_viewer')
        self.imgs = {'top': None, 'p1': None}
        self.lock = threading.Lock()
        self.create_subscription(CompressedImage, '/cam_top/image_raw/compressed',
            lambda msg: self._cb(msg, 'top'), 10)
        self.create_subscription(CompressedImage, '/pair1/cam/image_raw/compressed',
            lambda msg: self._cb(msg, 'p1'), 10)

    def _cb(self, msg, key):
        arr = np.frombuffer(bytes(msg.data), np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            with self.lock:
                self.imgs[key] = img

    def get_frame(self):
        with self.lock:
            top = self.imgs['top'].copy() if self.imgs['top'] is not None else np.zeros((H, W, 3), np.uint8)
            p1  = self.imgs['p1'].copy()  if self.imgs['p1']  is not None else np.zeros((H, W, 3), np.uint8)

        bird = apply_homography(top, _H, _H_SIZE) if _H is not None else top.copy()

        top_r  = cv2.resize(top,  (W, H))
        bird_r = cv2.resize(bird, (W, H))
        p1_r   = cv2.resize(p1,   (W, H))

        cv2.putText(top_r,  'cam_top RAW',  (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(bird_r, 'cam_top BIRD', (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 128), 2)
        cv2.putText(p1_r,   'pair1/cam',    (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200,  0), 2)

        frame = np.hstack([top_r, bird_r, p1_r])
        # BGR → RGB for PIL
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def main():
    rclpy.init()
    node = CameraViewer()
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    root = tk.Tk()
    root.title('Camera Viewer  (q: 종료)')
    label = tk.Label(root)
    label.pack()

    def update():
        frame_rgb = node.get_frame()
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        label.imgtk = imgtk
        label.configure(image=imgtk)
        root.after(33, update)  # ~30fps

    root.bind('<q>', lambda e: root.destroy())
    root.after(33, update)
    print("카메라 뷰어 시작 (q 또는 창 닫기: 종료)")
    root.mainloop()

    rclpy.shutdown()


if __name__ == '__main__':
    main()
