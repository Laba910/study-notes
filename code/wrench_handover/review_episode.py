#!/usr/bin/env python3
"""
에피소드 녹화 검토 뷰어 - MCAP 직접 읽기 방식
사용법: python3 review_episode.py [에피소드번호]
        python3 review_episode.py        ← 마지막 에피소드
키: q 종료 / space 일시정지 / 좌우 방향키 ±5초
"""
import os
import sys
import glob
import time
import rclpy.serialization
import numpy as np
import cv2
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import CompressedImage, JointState
from rosidl_runtime_py.utilities import get_message

sys.path.insert(0, os.path.dirname(__file__))
from homography_utils import load_homography, apply_homography

BAG_DIR = os.path.join(os.path.dirname(__file__), 'raw_bags')
_H, _H_SIZE = load_homography(os.path.join(os.path.dirname(__file__), 'homography.json'))

IMG_TOPICS = {
    '/cam_top/image_raw/compressed': 'cam_top',
    '/pair1/cam/image_raw/compressed': 'pair1',
    '/pair2/cam/image_raw/compressed': 'pair2',
}
JOINT_TOPIC = '/pair1/follower/joint_states'


def find_bag(episode_num=None):
    bags = sorted(glob.glob(os.path.join(BAG_DIR, 'episode_[0-9][0-9][0-9]')))
    if not bags:
        return None, None
    if episode_num is None:
        path = bags[-1]
    else:
        tag = f'episode_{int(episode_num):03d}'
        matched = [b for b in bags if os.path.basename(b) == tag]
        path = matched[0] if matched else None
    if path is None:
        return None, None
    return path, os.path.basename(path)


def decode_image(raw_bytes):
    arr = np.frombuffer(raw_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def load_bag(bag_path):
    """MCAP에서 모든 메시지를 타임스탬프 순으로 읽어 반환."""
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=bag_path, storage_id='mcap'),
        ConverterOptions('', '')
    )

    type_map = {t.name: t.type for t in reader.get_all_topics_and_types()}
    frames = []  # (timestamp_ns, topic, msg)

    while reader.has_next():
        topic, data, ts = reader.read_next()
        if topic not in IMG_TOPICS and topic != JOINT_TOPIC:
            continue
        msg_type = get_message(type_map[topic])
        msg = deserialize_message(data, msg_type)
        frames.append((ts, topic, msg))

    frames.sort(key=lambda x: x[0])
    return frames


def render(state, paused, elapsed_s, total_s):
    H, W = 360, 480
    black = np.zeros((H, W, 3), dtype=np.uint8)
    panels = []

    top = state['cam_top']
    if top is not None:
        full = cv2.resize(top, (W, H))
        cv2.putText(full, 'cam_top FULL', (6, 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        bird_src = apply_homography(top, _H, _H_SIZE) if _H is not None else top
        bird = cv2.resize(bird_src, (W, H))
        cv2.putText(bird, 'cam_top BIRD', (6, 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 128), 1)
        panels += [full, bird]
    else:
        panels += [black.copy(), black.copy()]

    for key, label, color in [
        ('pair1', 'pair1/cam', (255, 200, 0)),
        ('pair2', 'pair2/cam', (255, 100, 100)),
    ]:
        f = state[key]
        if f is not None:
            img = cv2.resize(f, (W, H))
            cv2.putText(img, label, (6, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
            panels.append(img)
        else:
            panels.append(black.copy())

    # joint state 오버레이
    if state['joints'] and len(panels) >= 3:
        y = 50
        for name, val in state['joints']:
            cv2.putText(panels[2], f'{name}: {val:.3f}', (6, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 255, 200), 1)
            y += 18

    # 진행 바
    bar_w = int((W * 2) * min(elapsed_s / max(total_s, 1), 1.0))
    row1 = np.hstack(panels[:2])
    cv2.rectangle(row1, (0, H - 6), (bar_w, H), (0, 200, 100), -1)
    cv2.putText(row1, f'{elapsed_s:.1f}s / {total_s:.1f}s', (6, H - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    if paused:
        cv2.putText(row1, 'PAUSED', (W - 80, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    row2 = np.hstack(panels[2:])
    cv2.imshow('Episode Review  q:종료  space:일시정지', np.vstack([row1, row2]))


def main():
    episode_num = int(sys.argv[1]) if len(sys.argv) > 1 else None
    bag_path, bag_name = find_bag(episode_num)
    if bag_path is None:
        print('에피소드를 찾을 수 없습니다.')
        sys.exit(1)

    print(f'로딩: {bag_name} ...')
    frames = load_bag(bag_path)
    if not frames:
        print('메시지 없음.')
        sys.exit(1)

    t0_ns = frames[0][0]
    total_s = (frames[-1][0] - t0_ns) / 1e9
    print(f'총 {len(frames)}개 메시지  {total_s:.1f}초  재생 시작 (q:종료 / space:일시정지)', flush=True)

    WINDOW = 'Episode Review  q:종료  space:일시정지'
    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)

    state = {'cam_top': None, 'pair1': None, 'pair2': None, 'joints': []}
    idx = 0
    paused = False
    play_start = time.monotonic()
    bag_offset = 0.0  # 재생 위치 (초)

    while idx < len(frames):
        if paused:
            elapsed_s = bag_offset
        else:
            elapsed_s = time.monotonic() - play_start
            # 현재 재생 시각까지의 메시지 소진
            while idx < len(frames):
                ts, topic, msg = frames[idx]
                msg_time_s = (ts - t0_ns) / 1e9
                if msg_time_s > elapsed_s:
                    break
                if topic in IMG_TOPICS:
                    img = decode_image(bytes(msg.data))
                    if img is not None:
                        state[IMG_TOPICS[topic]] = img
                elif topic == JOINT_TOPIC:
                    state['joints'] = list(zip(msg.name, msg.position))
                idx += 1

        render(state, paused, elapsed_s, total_s)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            if paused:
                play_start = time.monotonic() - bag_offset
            else:
                bag_offset = elapsed_s
            paused = not paused
        time.sleep(0.033)  # ~30fps 페이스 유지 (waitKey 대체)

    cv2.destroyAllWindows()
    print('재생 완료')


if __name__ == '__main__':
    main()
