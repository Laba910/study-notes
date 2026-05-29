#!/usr/bin/env python3
"""
MCAP raw_bags → LeRobot 데이터셋 변환 v3
변경: cam_top_raw (원본 탑뷰) 추가 — 손 위치 인식 개선

실행: source /opt/ros/jazzy/setup.bash && python3 convert_to_lerobot_v2.py
출력: /home/laba/datasets/lerobot_dataset/wrench_handover_v3/
"""
import sys, os, argparse, glob
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/home/laba/il_ws/src/lerobot/src')

from lerobot_utils import read_bag, build_sync_frames, IMG_TOPICS, JOINT_ORDER
from homography_utils import load_homography, apply_homography
from lerobot.datasets.lerobot_dataset import LeRobotDataset

DATASET_DIR  = os.path.dirname(__file__)
BAG_DIR      = os.path.join(DATASET_DIR, 'raw_bags')
OUTPUT_ROOT  = '/home/laba/datasets/lerobot_dataset/wrench_handover_v3'
REPO_ID      = 'local/wrench_handover_v3'
TASK_DESC    = 'pick up wrench and hand to human'
IMG_SIZE     = 224


def decode_img(msg):
    arr = np.frombuffer(bytes(msg.data), np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def to_rgb224(img):
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def find_bags(max_episodes=None):
    bags = sorted(glob.glob(os.path.join(BAG_DIR, 'episode_[0-9][0-9][0-9]')))
    if max_episodes:
        bags = bags[:max_episodes]
    return bags


def make_dataset(fps):
    features = {
        'observation.state': {
            'dtype': 'float32',
            'shape': (6,),
            'names': JOINT_ORDER,
        },
        'action': {
            'dtype': 'float32',
            'shape': (6,),
            'names': JOINT_ORDER,
        },
        'observation.images.cam_top_raw': {   # 추가: 원본 탑뷰 (손 위치 인식용)
            'dtype': 'video',
            'shape': (IMG_SIZE, IMG_SIZE, 3),
            'names': ['height', 'width', 'channels'],
        },
        'observation.images.cam_top_bird': {
            'dtype': 'video',
            'shape': (IMG_SIZE, IMG_SIZE, 3),
            'names': ['height', 'width', 'channels'],
        },
        'observation.images.pair1_cam': {
            'dtype': 'video',
            'shape': (IMG_SIZE, IMG_SIZE, 3),
            'names': ['height', 'width', 'channels'],
        },
    }
    return LeRobotDataset.create(
        repo_id=REPO_ID,
        fps=fps,
        features=features,
        root=OUTPUT_ROOT,
        robot_type='manipulator',
        use_videos=True,
    )


def extract_cam_top_raw(images, img_refs):
    """원본 탑뷰 이미지 추출 (호모그래피 미적용)"""
    top_idx = img_refs.get('cam_top')
    if top_idx is not None and images['cam_top']:
        raw = decode_img(images['cam_top'][top_idx][1])
        if raw is not None:
            return to_rgb224(raw)
    return np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)


def extract_cam_top_bird(images, img_refs, H, H_SIZE):
    """버드아이뷰 이미지 추출 (호모그래피 적용)"""
    top_idx = img_refs.get('cam_top')
    if top_idx is not None and images['cam_top']:
        raw = decode_img(images['cam_top'][top_idx][1])
        if raw is not None:
            bird = apply_homography(raw, H, H_SIZE) if H is not None else raw
            return to_rgb224(bird)
    return np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)


def extract_pair1_cam(images, img_refs):
    """pair1 손목 카메라 이미지 추출"""
    p1_idx = img_refs.get('pair1_cam')
    if p1_idx is not None and images['pair1_cam']:
        raw = decode_img(images['pair1_cam'][p1_idx][1])
        if raw is not None:
            return to_rgb224(raw)
    return np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)


def convert_episode(ds, bag_path, H, H_SIZE, fps):
    print(f'  읽는 중...')
    msgs = read_bag(bag_path)
    frames = build_sync_frames(msgs, target_fps=fps)
    if not frames:
        print(f'  ⚠ 프레임 없음, 건너뜀')
        return 0

    for frame in frames:
        images  = frame['images']
        img_refs = frame['img_refs']

        ds.add_frame({
            'task':                              TASK_DESC,
            'observation.state':                 frame['state'],
            'action':                            frame['action'],
            'observation.images.cam_top_raw':    extract_cam_top_raw(images, img_refs),
            'observation.images.cam_top_bird':   extract_cam_top_bird(images, img_refs, H, H_SIZE),
            'observation.images.pair1_cam':      extract_pair1_cam(images, img_refs),
        })

    ds.save_episode()
    print(f'  ✓ {len(frames)} 프레임 저장')
    return len(frames)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=int, default=None, help='변환할 에피소드 수 (기본: 전체)')
    parser.add_argument('--fps',      type=int, default=10,   help='목표 fps (기본: 10)')
    args = parser.parse_args()

    H, H_SIZE = load_homography(os.path.join(DATASET_DIR, 'homography.json'))

    bags = find_bags(args.episodes)
    print(f'변환 대상: {len(bags)}개 에피소드 / fps={args.fps}')
    print(f'출력 경로: {OUTPUT_ROOT}')

    if os.path.exists(OUTPUT_ROOT):
        print(f'\n⚠ 출력 경로가 이미 존재합니다: {OUTPUT_ROOT}')
        ans = input('덮어쓰시겠습니까? (y/N): ').strip().lower()
        if ans != 'y':
            print('취소됨.')
            return
        import shutil
        shutil.rmtree(OUTPUT_ROOT)

    ds = make_dataset(args.fps)
    total_frames = 0

    for i, bag_path in enumerate(bags):
        ep_name = os.path.basename(bag_path)
        print(f'\n[{i+1}/{len(bags)}] {ep_name}')
        total_frames += convert_episode(ds, bag_path, H, H_SIZE, args.fps)

    print(f'\n변환 완료: {len(bags)}개 에피소드 / {total_frames}개 프레임')
    print(f'저장 위치: {OUTPUT_ROOT}')


if __name__ == '__main__':
    main()
