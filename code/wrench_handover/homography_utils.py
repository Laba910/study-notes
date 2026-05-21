"""
호모그래피 유틸리티 - 버드아이뷰 변환 핵심 함수 모음
다른 스크립트에서 import해서 사용
"""
import cv2
import numpy as np
import json
import os

DEFAULT_OUTPUT_SIZE = (640, 640)


def load_homography(path):
    """JSON 파일에서 호모그래피 행렬 로드. 파일 없으면 None 반환."""
    if not os.path.exists(path):
        return None, None
    with open(path, 'r') as f:
        data = json.load(f)
    H = np.array(data['H'], dtype=np.float64)
    output_size = tuple(data.get('output_size', DEFAULT_OUTPUT_SIZE))
    return H, output_size


def save_homography(H, src_points, output_size, path):
    """호모그래피 행렬과 메타데이터를 JSON으로 저장."""
    data = {
        'H': H.tolist(),
        'output_size': list(output_size),
        'src_points': [list(map(float, p)) for p in src_points]
    }
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def compute_homography(src_points, output_size=DEFAULT_OUTPUT_SIZE):
    """
    4개 꼭짓점(src_points)으로 호모그래피 행렬 계산.
    src_points: [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] - 좌상/우상/우하/좌하 순
    output_size: (width, height)
    """
    w, h = output_size
    dst_points = np.array([
        [0,   0  ],
        [w-1, 0  ],
        [w-1, h-1],
        [0,   h-1],
    ], dtype=np.float32)
    src = np.array(src_points, dtype=np.float32)
    H, _ = cv2.findHomography(src, dst_points)
    return H


def apply_homography(img, H, output_size=DEFAULT_OUTPUT_SIZE):
    """이미지에 호모그래피 변환 적용 후 반환."""
    w, h = output_size
    return cv2.warpPerspective(img, H, (w, h))


def draw_grid(img, mat_mm=(600, 400), output_size=(640, 640),
              interval_mm=50, color=(60, 60, 60), alpha=0.55):
    """
    버드아이뷰 이미지에 실치수(mm) 기준 격자 오버레이.
    mat_mm: 매트 실물 크기 (가로mm, 세로mm)
    output_size: 버드아이뷰 출력 크기 (px)
    interval_mm: 격자 간격 (mm)
    """
    vis = img.copy()
    grid = img.copy()
    ow, oh = output_size
    mw, mh = mat_mm

    px_per_mm_x = ow / mw  # 가로 스케일
    px_per_mm_y = oh / mh  # 세로 스케일
    step_x = px_per_mm_x * interval_mm
    step_y = px_per_mm_y * interval_mm

    # 세로선 (X축)
    x = 0.0
    mm_x = 0
    while x <= ow:
        xi = int(round(x))
        cv2.line(grid, (xi, 0), (xi, oh), color, 1)
        if mm_x % (interval_mm * 2) == 0:  # 짝수 눈금만 라벨
            cv2.putText(grid, f'{mm_x}', (xi + 2, 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, (180, 180, 180), 1)
        x += step_x
        mm_x += interval_mm

    # 가로선 (Y축)
    y = 0.0
    mm_y = 0
    while y <= oh:
        yi = int(round(y))
        cv2.line(grid, (0, yi), (ow, yi), color, 1)
        if mm_y % (interval_mm * 2) == 0:
            cv2.putText(grid, f'{mm_y}', (2, yi + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, (180, 180, 180), 1)
        y += step_y
        mm_y += interval_mm

    return cv2.addWeighted(grid, alpha, vis, 1 - alpha, 0)


def draw_points(img, points):
    """
    클릭된 꼭짓점을 이미지에 시각화.
    points: [(x,y), ...] 리스트 (최대 4개)
    """
    labels = ['1:LT', '2:RT', '3:RB', '4:LB']
    colors = [(0,255,0), (0,200,255), (0,100,255), (255,100,0)]
    vis = img.copy()
    for i, (x, y) in enumerate(points):
        color = colors[i]
        cv2.circle(vis, (int(x), int(y)), 8, color, -1)
        cv2.circle(vis, (int(x), int(y)), 10, (255,255,255), 2)
        cv2.putText(vis, labels[i], (int(x)+12, int(y)+5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    # 4개 다 찍혔으면 사각형 연결선 표시
    if len(points) == 4:
        pts = np.array(points, dtype=np.int32)
        cv2.polylines(vis, [pts], isClosed=True, color=(0,255,0), thickness=2)
    return vis
