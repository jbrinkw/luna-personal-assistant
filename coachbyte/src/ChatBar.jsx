import React, { useState, useEffect, useRef } from 'react';

export default function ChatBar() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Load chat history from session storage on mount
  useEffect(() => {
    const savedMessages = sessionStorage.getItem('chatHistory');
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    }
  }, []);

  // Save chat history to session storage whenever messages change
  useEffect(() => {
    sessionStorage.setItem('chatHistory', JSON.stringify(messages));
  }, [messages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input.trim() })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();
      
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: data.response,
        timestamp: new Date().toLocaleTimeString()
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = async () => {
    try {
      // Clear database memory
      await fetch('/api/chat/memory', {
        method: 'DELETE'
      });
      
      // Clear local state and session storage
      setMessages([]);
      sessionStorage.removeItem('chatHistory');
    } catch (error) {
      console.error('Error clearing chat memory:', error);
      // Still clear local state even if server fails
      setMessages([]);
      sessionStorage.removeItem('chatHistory');
    }
  };

  // Styles
  const chatBarStyle = {
    position: 'fixed',
    right: isExpanded ? '0' : '-400px',
    top: '0',
    height: '100vh',
    width: '400px',
    backgroundColor: '#ffffff',
    borderLeft: '1px solid #e0e0e0',
    transition: 'right 0.3s ease',
    zIndex: 1000,
    display: 'flex',
    flexDirection: 'column',
    boxShadow: isExpanded ? '-2px 0 5px rgba(0,0,0,0.1)' : 'none'
  };

  const toggleButtonStyle = {
    position: 'fixed',
    right: isExpanded ? '400px' : '0',
    top: '50%',
    transform: 'translateY(-50%)',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: isExpanded ? '8px 0 0 8px' : '0 8px 8px 0',
    padding: '12px 6px',
    cursor: 'pointer',
    fontSize: '16px',
    transition: 'right 0.3s ease',
    zIndex: 1001,
    writingMode: 'vertical-lr',
    textOrientation: 'mixed',
    minWidth: '40px',
    height: '60px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  };

  const headerStyle = {
    padding: '15px',
    backgroundColor: '#f8f9fa',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const titleStyle = {
    margin: 0,
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#333'
  };

  const clearButtonStyle = {
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    padding: '4px 8px',
    fontSize: '12px',
    cursor: 'pointer'
  };

  const messagesContainerStyle = {
    flex: 1,
    overflowY: 'auto',
    padding: '10px',
    backgroundColor: '#f8f9fa'
  };

  const messageStyle = {
    marginBottom: '12px',
    padding: '8px 12px',
    borderRadius: '8px',
    maxWidth: '85%',
    wordBreak: 'break-word'
  };

  const userMessageStyle = {
    ...messageStyle,
    backgroundColor: '#007bff',
    color: 'white',
    marginLeft: 'auto',
    textAlign: 'right'
  };

  const aiMessageStyle = {
    ...messageStyle,
    backgroundColor: '#ffffff',
    color: '#333',
    border: '1px solid #e0e0e0'
  };

  const timestampStyle = {
    fontSize: '10px',
    opacity: 0.7,
    marginTop: '4px'
  };

  const inputContainerStyle = {
    padding: '15px',
    borderTop: '1px solid #e0e0e0',
    backgroundColor: '#ffffff'
  };

  const inputStyle = {
    width: '100%',
    padding: '10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    resize: 'none',
    outline: 'none',
    fontFamily: 'inherit'
  };

  const sendButtonStyle = {
    width: '100%',
    marginTop: '8px',
    padding: '8px',
    backgroundColor: isLoading ? '#ccc' : '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: isLoading ? 'not-allowed' : 'pointer',
    fontSize: '14px'
  };

  const loadingIndicatorStyle = {
    textAlign: 'center',
    padding: '10px',
    color: '#666',
    fontSize: '14px'
  };

  return (
    <>
      <button
        style={toggleButtonStyle}
        onClick={() => setIsExpanded(!isExpanded)}
        title={isExpanded ? 'Close Chat' : 'Open Chat'}
      >
        {isExpanded ? '✕' : '💬'}
      </button>

      <div style={chatBarStyle}>
        <div style={headerStyle}>
          <h3 style={titleStyle}>🤖 CoachByte Chat</h3>
          <button style={clearButtonStyle} onClick={clearChat}>
            Clear
          </button>
        </div>

        <div style={messagesContainerStyle}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: '#666', padding: '20px' }}>
              <p>👋 Hi! I'm CoachByte, your fitness assistant.</p>
              <p>Ask me about your workouts, create plans, or log exercises!</p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              style={message.type === 'user' ? userMessageStyle : aiMessageStyle}
            >
              <div>{message.content}</div>
              <div style={timestampStyle}>{message.timestamp}</div>
            </div>
          ))}

          {isLoading && (
            <div style={loadingIndicatorStyle}>
              <div>CoachByte is thinking...</div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div style={inputContainerStyle}>
          <textarea
            style={inputStyle}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about your workouts..."
            rows={3}
            disabled={isLoading}
          />
          <button
            style={sendButtonStyle}
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? 'Sending...' : 'Send Message'}
          </button>
        </div>
      </div>
    </>
  );
} 