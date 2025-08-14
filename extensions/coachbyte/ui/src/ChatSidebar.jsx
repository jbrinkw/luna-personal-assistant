import React, { useState } from 'react';

export default function ChatSidebar() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages([...messages, input]);
    setInput('');
  };

  return (
    <div className="sidebar">
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
        />
      </form>
      <div className="chat-history">
        {messages.map((m, i) => (
          <div key={i} className="chat-message">{m}</div>
        ))}
      </div>
    </div>
  );
}
