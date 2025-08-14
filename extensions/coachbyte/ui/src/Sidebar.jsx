import React, { useState } from 'react';
import './styles.css';

export default function Sidebar() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);

  const sendMessage = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages([...messages, input]);
    setInput('');
  };

  return (
    <>
      <button className="sidebar-toggle" onClick={() => setOpen(!open)}>
        {open ? 'Close' : 'Chat'}
      </button>
      <div className={`sidebar ${open ? 'open' : ''}`}>
        <form onSubmit={sendMessage}>
          <input
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message"
          />
        </form>
        <div className="chat-history">
          {messages.map((m, i) => (
            <div key={i} className="chat-message">{m}</div>
          ))}
        </div>
      </div>
    </>
  );
}

