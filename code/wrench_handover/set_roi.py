#!/usr/bin/env python3
"""
ROI 설정 도구 - cam_top 화면에서 마우스로 드래그해서 매트 영역 선택
실행: python3 set_roi.py
사용: 왼쪽 창에서 마우스 드래그 → Enter/Space 확정
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2, numpy as np, json, time, os

ROI_CONFIG = os.path.join(os.path.dirname(__file__), 'roi_config.json')

rclpy.init()
node = Node('roi_setter')
bridge = CvBridge()
latest = [None]

node.create_subscription(Image, '/cam_top/image_raw',
    lambda msg: latest.__setitem__(0, bridge.imgmsg_to_cv2(msg, 'bgr8')), 1)

print("cam_top 이미지 수신 중...")
start = time.time()
while latest[0] is None and time.time() - start < 5:
    rclpy.spin_once(node, timeout_sec=0.1)

if latest[0] is None:
    print("카메라 신호 없음. launch가 실행 중인지 확인하세요.")
    rclpy.shutdown()
    exit(1)

img = latest[0].copy()
print(f"이미지 크기: {img.shape[1]}x{img.shape[0]}")
print("→ 검정 매트 영역을 마우스로 드래그하세요.")
print("→ Space 또는 Enter: 확정 / c: 취소")

r = cv2.selectROI('ROI 선택: 매트 영역 드래그 후 Enter', img, False, False)
cv2.destroyAllWindows()

if r[2] > 0 and r[3] > 0:
    x1, y1, w, h = int(r[0]), int(r[1]), int(r[2]), int(r[3])
    x2, y2 = x1 + w, y1 + h

    # 결과 미리보기
    preview = img.copy()
    cv2.rectangle(preview, (x1,y1), (x2,y2), (0,255,0), 2)
    outside = preview.copy()
    inside = np.zeros_like(preview)
    inside[y1:y2, x1:x2] = preview[y1:y2, x1:x2]
    blended = cv2.addWeighted(outside, 0.25, inside, 0.75, 0)
    cv2.rectangle(blended, (x1,y1), (x2,y2), (0,255,0), 2)
    cv2.putText(blended, f'ROI: ({x1},{y1})~({x2},{y2})  {w}x{h}px',
                (x1, max(y1-6, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    cv2.putText(blended, 'Hand zone', (4, img.shape[0]//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,180,255), 2)

    cv2.imshow('ROI 확인 (아무 키나 누르면 저장)', blended)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # roi_config.json 업데이트
    with open(ROI_CONFIG, 'r') as f:
        config = json.load(f)

    config['cam_top']['roi_crop']['x1'] = x1
    config['cam_top']['roi_crop']['y1'] = y1
    config['cam_top']['roi_crop']['x2'] = x2
    config['cam_top']['roi_crop']['y2'] = y2

    with open(ROI_CONFIG, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n저장 완료: ROI = ({x1},{y1}) ~ ({x2},{y2})")
    print(f"크기: {w}x{h} → 학습시 224x224로 리사이즈")
else:
    print("ROI 선택 취소됨.")

rclpy.shutdown()
