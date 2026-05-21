"""
MCAP → LeRobot 변환 유틸리티
"""
import numpy as np
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

JOINT_ORDER = ['gripper_joint_1', 'joint1', 'joint2', 'joint3', 'joint4', 'joint5']

IMG_TOPICS = {
    '/cam_top/image_raw/compressed': 'cam_top',
    '/pair1/cam/image_raw/compressed': 'pair1_cam',
}
FOLLOWER_TOPIC = '/pair1/follower/joint_states'
LEADER_TOPIC   = '/pair1/leader/joint_states'


def read_bag(bag_path):
    """MCAP에서 모든 메시지를 타임스탬프 순으로 읽어 반환."""
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=str(bag_path), storage_id='mcap'),
        ConverterOptions('', '')
    )
    type_map = {t.name: t.type for t in reader.get_all_topics_and_types()}
    msgs = []
    want = set(IMG_TOPICS) | {FOLLOWER_TOPIC, LEADER_TOPIC}
    while reader.has_next():
        topic, data, ts = reader.read_next()
        if topic not in want:
            continue
        msg_type = get_message(type_map[topic])
        msg = deserialize_message(data, msg_type)
        msgs.append((ts, topic, msg))
    msgs.sort(key=lambda x: x[0])
    return msgs


def extract_joint_pos(msg):
    """JointState 메시지에서 JOINT_ORDER 순으로 위치 배열 반환."""
    name_to_pos = dict(zip(msg.name, msg.position))
    return np.array([name_to_pos.get(j, 0.0) for j in JOINT_ORDER], dtype=np.float32)


def nearest_before(index_list, ts):
    """timestamps(ns) 리스트에서 ts 이하인 것 중 가장 가까운 인덱스 반환."""
    lo, hi = 0, len(index_list) - 1
    result = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if index_list[mid] <= ts:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return result


def build_sync_frames(msgs, target_fps=10):
    """
    타임스탬프 동기화 후 target_fps 단위 프레임 리스트 반환.
    반환: list of dict {
        't': float (초),
        'state': np.array(6,),
        'action': np.array(6,),
        'cam_top_ts': int (ns),
        'pair1_cam_ts': int (ns),
    }
    """
    # 토픽별 분리
    follower, leader = [], []
    images = {k: [] for k in IMG_TOPICS.values()}

    for ts, topic, msg in msgs:
        if topic == FOLLOWER_TOPIC:
            follower.append((ts, msg))
        elif topic == LEADER_TOPIC:
            leader.append((ts, msg))
        elif topic in IMG_TOPICS:
            images[IMG_TOPICS[topic]].append((ts, msg))

    if not follower or not leader:
        return []

    t0 = follower[0][0]
    t_end = follower[-1][0]
    step_ns = int(1e9 / target_fps)

    follower_ts = [f[0] for f in follower]
    leader_ts   = [l[0] for l in leader]
    img_ts = {k: [x[0] for x in v] for k, v in images.items()}

    frames = []
    ts = t0
    while ts <= t_end:
        fi = nearest_before(follower_ts, ts)
        li = nearest_before(leader_ts, ts)

        state  = extract_joint_pos(follower[fi][1])
        action = extract_joint_pos(leader[li][1])

        img_refs = {}
        for k in images:
            if not img_ts[k]:
                img_refs[k] = None
            else:
                img_refs[k] = nearest_before(img_ts[k], ts)

        frames.append({
            't': (ts - t0) / 1e9,
            'state': state,
            'action': action,
            'img_refs': img_refs,
            'images': images,
        })
        ts += step_ns

    return frames
