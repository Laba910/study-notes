#!/bin/bash
# 변환 → ACT 학습 → Diffusion Policy 학습 순차 실행
# RTX 4070 Laptop 8GB VRAM 기준 (동시 학습 불가, 순차 실행)

set -e  # 오류 발생 시 중단

DATASET_ROOT="/home/laba/datasets/lerobot_dataset/wrench_handover_v3"
TRAIN_SCRIPT="/home/laba/il_ws/src/lerobot/src/lerobot/scripts/lerobot_train.py"
OUTPUT_BASE="/home/laba/il_ws/outputs"

echo "========================================"
echo " 1단계: 데이터셋 변환"
echo "========================================"
source /opt/ros/jazzy/setup.bash
cd /home/laba/datasets/wrench_handover
python3 convert_to_lerobot_v3.py
echo "변환 완료"

echo ""
echo "========================================"
echo " 2단계: ACT 학습"
echo "========================================"
cd /home/laba/il_ws/src/lerobot/src
/home/laba/venv/il/bin/python3 lerobot/scripts/lerobot_train.py \
  --policy.type=act \
  --dataset.repo_id=local/wrench_handover_v3 \
  --dataset.root=$DATASET_ROOT \
  --batch_size=32 \
  --steps=100000 \
  --output_dir=$OUTPUT_BASE/wrench_act_v3
echo "ACT 학습 완료"

echo ""
echo "========================================"
echo " 3단계: Diffusion Policy 학습"
echo "========================================"
/home/laba/venv/il/bin/python3 lerobot/scripts/lerobot_train.py \
  --policy.type=diffusion \
  --dataset.repo_id=local/wrench_handover_v3 \
  --dataset.root=$DATASET_ROOT \
  --batch_size=32 \
  --steps=100000 \
  --output_dir=$OUTPUT_BASE/wrench_diffusion_v1
echo "Diffusion Policy 학습 완료"

echo ""
echo "========================================"
echo " 전체 파이프라인 완료"
echo " ACT:       $OUTPUT_BASE/wrench_act_v3"
echo " Diffusion: $OUTPUT_BASE/wrench_diffusion_v1"
echo "========================================"
