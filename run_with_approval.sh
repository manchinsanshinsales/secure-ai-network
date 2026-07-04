#!/bin/bash

# ==============================================================================
# Mail Approval Flow CLI Wrapper
# 
# 承認メールを送信し、返信が得られた場合のみコマンドを実行する自動化フローのラッパー。
# 承認者はデフォルトで makoto.insidesales@gmail.com に設定されています。
# ==============================================================================

# 引数チェック
TASK_NAME=$1
COMMAND_TO_RUN=$2
APPROVER="makoto.insidesales@gmail.com"
EXTRA_ARGS=""

if [ -z "$TASK_NAME" ] || [ -z "$COMMAND_TO_RUN" ]; then
    echo "Usage: ./run_with_approval.sh \"<Task Name>\" \"<Command to Run>\" [extra_arguments...]"
    echo ""
    echo "Examples:"
    echo "  # 本物のメール送信を行う場合（.env に認証情報が必要）"
    echo "  ./run_with_approval.sh \"Terraform Apply Azure\" \"terraform -chdir=terraform/azure apply -auto-approve\""
    echo ""
    echo "  # シミュレーションモード（メール送信を行わず、コンソール上で承認操作をテスト）"
    echo "  ./run_with_approval.sh \"Demo Task\" \"echo 'Success'\" --simulate"
    exit 1
fi

# 3つ目以降の引数を残して、Pythonスクリプトに直接安全に引き渡す
shift 2

# venvのpythonがある場合はそれを優先的に使用
if [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
elif [ -f "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

echo "[*] Using Python: $PYTHON_CMD"
echo "[*] Approver: $APPROVER"
echo "[*] Task: $TASK_NAME"
echo "[*] Command: $COMMAND_TO_RUN"
echo ""

# 承認フロースクリプトを実行
$PYTHON_CMD app/approval_flow.py --task "$TASK_NAME" --command "$COMMAND_TO_RUN" --approver "$APPROVER" "$@"
