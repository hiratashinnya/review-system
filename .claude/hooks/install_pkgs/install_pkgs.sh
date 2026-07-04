#!/bin/bash

if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

# RTKのインストール
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
rtk gain
rtk init -g --auto-patch

# Python LSPのインストール
claude plugin install pyright-lsp@claude-plugins-official


exit 0