#!/usr/bin/env python3
"""
호모그래피 캘리브레이션 도구
매트 4개 꼭짓점을 마우스로 클릭해서 버드아이뷰 변환 행렬 생성

실행: python3 calibrate_homography.py
조작:
  좌클릭         - 꼭짓점 추가 (좌상→우상→우하→좌하 순)
  우클릭         - 마지막 점 취소
  r              - 전체 초기화
  Enter / Space  - 4점 완료 후 확정 및 저장
  q              - 종료
"""
import os
import sys
import time
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

sys.path.insert(0, os.path.dirname(__file__))
from homography_utils import (
    compute_homography, save_homography, apply_homography, draw_points
)

HOMOGRAPHY_PATH = os.path.join(os.path.dirname(__file__), 'homography.json')
OUTPUT_SIZE = (640, 640)
WINDOW = 'Homography Calibration'


def capture_frame():
    """cam_top에서 프레임 1장 캡처."""
    rclpy.init()
    node = Node('homo_calib')
    bridge = CvBridge()
    result = [None]

    node.create_subscription(
        Image, '/cam_top/image_raw',
        lambda msg: result.__setitem__(0, bridge.imgmsg_to_cv2(msg, 'bgr8')), 1
    )
    start = time.time()
    while result[0] is None and time.time() - start < 5:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()
    return result[0]


def show_guide(img):
    """안내 텍스트를 이미지에 오버레이."""
    vis = img.copy()
    lines = [
        '좌클릭: 점 추가  |  우클릭: 마지막 점 취소  |  r: 초기화  |  Enter: 확정  |  q: 종료',
        '순서: 1.좌상단  2.우상단  3.우하단  4.좌하단',
    ]
    for i, line in enumerate(lines):
        cv2.putText(vis, line, (8, 18 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 255, 255), 1, cv2.LINE_AA)
    return vis


def run_calibration(img):
    """
    마우스 클릭으로 4개 꼭짓점 선택.
    반환: src_points (4개) 또는 None (취소)
    """
    points = []

    def on_mouse(event, x, y, flags, _):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)

    while True:
        vis = show_guide(img)
        vis = draw_points(vis, points)

        remaining = 4 - len(points)
        if remaining > 0:
            cv2.putText(vis, f'남은 점: {remaining}개', (8, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)
        else:
            cv2.putText(vis, 'Enter로 확정하세요', (8, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow(WINDOW, vis)
        key = cv2.waitKey(30) & 0xFF

        if key == ord('q'):
            cv2.destroyAllWindows()
            return None
        elif key == ord('r'):
            points.clear()
        elif key in (13, 32) and len(points) == 4:  # Enter or Space
            cv2.destroyAllWindows()
            return points

    return None


def show_result(img, H, src_points):
    """보정 전/후 비교 화면 표시. 아무 키나 누르면 닫힘."""
    warped = apply_homography(img, H, OUTPUT_SIZE)
    orig_resized = cv2.resize(img, OUTPUT_SIZE)

    # 원본에 선택 점 표시
    orig_vis = draw_points(orig_resized.copy(),
                           [(p[0] * OUTPUT_SIZE[0] / img.shape[1],
                             p[1] * OUTPUT_SIZE[1] / img.shape[0])
                            for p in src_points])

    cv2.putText(orig_vis, 'BEFORE', (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
    cv2.putText(warped, 'AFTER (Bird Eye View)', (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    compare = np.hstack([orig_vis, warped])
    cv2.imshow('Result (any key to save & close)', compare)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    print('cam_top 이미지 수신 중...')
    img = capture_frame()
    if img is None:
        print('카메라 신호 없음. launch가 실행 중인지 확인하세요.')
        return

    print(f'이미지 수신 완료: {img.shape[1]}x{img.shape[0]}')
    print('창에서 매트 꼭짓점을 순서대로 클릭하세요.')

    src_points = run_calibration(img)
    if src_points is None:
        print('취소됨.')
        return

    H = compute_homography(src_points, OUTPUT_SIZE)
    show_result(img, H, src_points)

    save_homography(H, src_points, OUTPUT_SIZE, HOMOGRAPHY_PATH)
    print(f'저장 완료: {HOMOGRAPHY_PATH}')
    print(f'출력 크기: {OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]} (버드아이뷰)')


if __name__ == '__main__':
    main()
