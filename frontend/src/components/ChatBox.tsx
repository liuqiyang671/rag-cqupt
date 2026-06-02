import { Button, Input, Space } from 'antd';
import { useState } from 'react';

interface ChatBoxProps {
  loading: boolean;
  onSend: (question: string) => Promise<void>;
}

export function ChatBox({ loading, onSend }: ChatBoxProps) {
  const [value, setValue] = useState('');

  async function handleSend() {
    const question = value.trim();
    if (!question) {
      return;
    }
    setValue('');
    await onSend(question);
  }

  return (
    <div className="chat-box">
      <Input.TextArea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onPressEnter={(event) => {
          if (!event.shiftKey) {
            event.preventDefault();
            void handleSend();
          }
        }}
        autoSize={{ minRows: 1, maxRows: 3 }}
        placeholder="输入校园服务问题，例如：校园卡怎么挂失？"
      />
      <Space className="chat-box-actions">
        <span className="hint">Shift + Enter 换行</span>
        <Button type="primary" loading={loading} onClick={() => void handleSend()}>
          发送
        </Button>
      </Space>
    </div>
  );
}
