#!/usr/bin/env bash
# 5분 홈페이지 만들기 — 사장님용 홈페이지 제작 체험 데모
# 사용법: bash run.sh   →   http://localhost:5005
set -euo pipefail

cd "$(dirname "$0")"

if ! python3 -c "import flask" >/dev/null 2>&1; then
  echo "Flask를 설치합니다..."
  pip3 install --quiet flask
fi

# 포트 5005가 사용 중이면 자동으로 다음 빈 포트로 전환
PORT=5005
PORT=$(python3 - "$PORT" <<'EOF'
import socket, sys
p = int(sys.argv[1])
while True:
    s = socket.socket()
    try:
        s.bind(("0.0.0.0", p))
        s.close()
        print(p); break
    except OSError:
        p += 1
EOF
)

echo "==============================================="
echo "  5분 홈페이지 만들기"
echo "  접속: http://localhost:${PORT}"
echo "  내 홈페이지 관리: http://localhost:${PORT}/manage"
echo "  (5005가 사용 중이면 자동으로 다음 빈 포트로 켜집니다)"
echo "  (종료: Ctrl+C)"
echo "==============================================="
PORT="$PORT" exec python3 app.py
