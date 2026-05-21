# Wrench Handover IL Pipeline

OMX 2쌍 텔레오퍼레이션으로 수집한 렌치 전달 시연 데이터를 ACT 학습 형식으로 변환하는 파이프라인.

## 환경

- ROS2 Jazzy + MCAP bag
- OMX (Open Manipulator X) × 4 (pair1/pair2 leader/follower)
- 카메라 3대: cam_top (버드아이뷰용), pair1/cam, pair2/cam
- LeRobot v0.4.4, ACT 정책

## 파일 구성

| 파일 | 설명 |
|------|------|
| `record_episode.sh` | 에피소드 녹화 (번호 자동증가, Enter 조기종료) |
| `review_episode.py` | 녹화 검토 뷰어 (4패널, 공백=일시정지) |
| `view_cameras.py` | 실시간 카메라 모니터 |
| `homography_utils.py` | 버드아이뷰 호모그래피 변환 |
| `calibrate_homography.py` | 호모그래피 캘리브레이션 |
| `lerobot_utils.py` | MCAP 읽기 + 타임스탬프 동기화 |
| `convert_to_lerobot.py` | MCAP → LeRobot 데이터셋 변환 |

## 사용법

```bash
# 1. 에피소드 녹화
source /home/laba/ros2_ws/install/setup.bash
./record_episode.sh

# 2. 녹화 검토
source /opt/ros/jazzy/setup.bash
python3 review_episode.py 5     # 5번 에피소드
python3 review_episode.py       # 마지막 에피소드

# 3. LeRobot 변환
python3 convert_to_lerobot.py
# 출력: /home/laba/datasets/lerobot_dataset/wrench_handover/

# 4. ACT 학습
cd /home/laba/il_ws
PYTHONPATH=src/lerobot/src python3 src/lerobot/src/lerobot/scripts/lerobot_train.py \
  --policy.type=act \
  --dataset.repo_id=local/wrench_handover \
  --dataset.root=/home/laba/datasets/lerobot_dataset/wrench_handover \
  --batch_size=16 --steps=50000 --output_dir=outputs/wrench_act
```

## 데이터 현황 (2026-05-21 기준)

- 에피소드: 55개
- 프레임: 15,567 (10fps)
- 원본 MCAP: 8.4GB (`/home/laba/datasets/wrench_handover/raw_bags/`)
- 변환 데이터셋: 64MB (MP4 AV1)
