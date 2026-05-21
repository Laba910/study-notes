#!/bin/bash
# 렌치 집어서 사람 손에 전달 - 에피소드 녹화 스크립트
# 사용법: ./record_episode.sh
# 조작: 녹화 중 Enter → 조기 종료 / 에피소드 간 q+Enter → 전체 종료

DATASET_DIR="$(cd "$(dirname "$0")" && pwd)"
BAG_DIR="$DATASET_DIR/raw_bags"
DURATION=60

source /home/laba/ros2_ws/install/setup.bash

record_one_episode() {
    # 다음 에피소드 번호 자동 계산
    local LAST
    LAST=$(ls -d "$BAG_DIR"/episode_[0-9][0-9][0-9] 2>/dev/null | grep -oP '[0-9]+$' | sort -n | tail -1)
    local EPISODE
    EPISODE=$(printf "%03d" $(( 10#${LAST:-0} + 1 )))
    local BAG_PATH="$BAG_DIR/episode_${EPISODE}"
    local TOTAL
    TOTAL=$(ls -d "$BAG_DIR"/episode_[0-9][0-9][0-9] 2>/dev/null | wc -l)

    echo ""
    echo "========================================"
    echo " 에피소드 ${EPISODE} / 050  (현재 ${TOTAL}개 완료)"
    echo " 저장 경로: $BAG_PATH"
    echo "========================================"
    echo " 준비되면 Enter (Ctrl+C: 전체 중단)"
    read -r

    echo "3..."; sleep 1
    echo "2..."; sleep 1
    echo "1..."; sleep 1
    echo "★ 녹화 시작! (최대 ${DURATION}초 / Enter: 조기종료)"

    ros2 bag record \
      --output "$BAG_PATH" \
      /pair1/follower/joint_states \
      /pair1/leader/joint_states \
      /pair2/follower/joint_states \
      /pair2/leader/joint_states \
      /cam_top/image_raw/compressed \
      /pair1/cam/image_raw/compressed \
      /pair2/cam/image_raw/compressed \
      > /dev/null 2>&1 &

    local BAG_PID=$!

    # Enter 또는 타임아웃 중 먼저 오는 것으로 종료
    read -t "$DURATION" -r
    local READ_EXIT=$?

    kill "$BAG_PID" 2>/dev/null
    wait "$BAG_PID" 2>/dev/null

    local SIZE
    SIZE=$(du -sh "$BAG_PATH" 2>/dev/null | cut -f1)
    if [ $READ_EXIT -ne 0 ]; then
        echo "◆ ${DURATION}초 경과 → 자동 종료"
    else
        echo "◆ 조기 종료"
    fi
    echo "✓ 에피소드 ${EPISODE} 완료  크기: ${SIZE}"
}

echo "========================================"
echo " 렌치 전달 데이터 녹화 시작"
echo " 목표: 50 에피소드 / 최대 ${DURATION}초"
echo "========================================"

while true; do
    record_one_episode

    echo ""
    echo " 다음 에피소드 준비됐으면 Enter"
    echo " 종료하려면 q + Enter"
    read -r CHOICE
    if [[ "$CHOICE" == "q" ]]; then
        break
    fi
done

TOTAL=$(ls -d "$BAG_DIR"/episode_[0-9][0-9][0-9] 2>/dev/null | wc -l)
echo ""
echo "========================================"
echo " 녹화 종료  총 ${TOTAL} / 50 에피소드 완료"
echo "========================================"
