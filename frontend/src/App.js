import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Terminal-style icons
const Icons = {
  Send: () => <span className="text-lg">▶</span>,
  Folder: () => <span>📁</span>,
  File: () => <span>📄</span>,
  Tool: () => <span>🔧</span>,
  Check: () => <span>✓</span>,
  X: () => <span>✕</span>,
  Terminal: () => <span>⌘</span>,
  Settings: () => <span>⚙</span>,
  Trash: () => <span>🗑</span>,
  Plus: () => <span>+</span>,
  Menu: () => <span>≡</span>,
};

// Tool Approval Modal
function ToolApprovalModal({ toolCall, onApprove, onReject }) {
  if (!toolCall) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" data-testid="tool-approval-modal">
      <div className="bg-gray-900 border border-cyan-500 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-auto">
        <div className="p-4 border-b border-cyan-500/30">
          <h3 className="text-cyan-400 font-mono text-lg flex items-center gap-2">
            <Icons.Tool /> Tool Execution Request
          </h3>
        </div>
        <div className="p-4">
          <div className="mb-4">
            <span className="text-gray-400 font-mono text-sm">Tool:</span>
            <div className="text-yellow-400 font-mono text-lg mt-1">{toolCall.tool}</div>
          </div>
          <div className="mb-4">
            <span className="text-gray-400 font-mono text-sm">Arguments:</span>
            <pre className="bg-black/50 p-3 rounded mt-1 text-green-400 font-mono text-sm overflow-auto max-h-60">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          <div className="flex gap-3 mt-6">
            <button
              onClick={onApprove}
              className="flex-1 bg-green-600 hover:bg-green-500 text-white font-mono py-2 px-4 rounded flex items-center justify-center gap-2 transition-colors"
              data-testid="approve-tool-btn"
            >
              <Icons.Check /> APPROVE
            </button>
            <button
              onClick={onReject}
              className="flex-1 bg-red-600 hover:bg-red-500 text-white font-mono py-2 px-4 rounded flex items-center justify-center gap-2 transition-colors"
              data-testid="reject-tool-btn"
            >
              <Icons.X /> REJECT
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Chat Message Component
function ChatMessage({ message, onToolApprove }) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isTool = message.role === 'tool';

  return (
    <div className={`mb-4 ${isUser ? 'text-right' : ''}`} data-testid="chat-message">
      <div className={`inline-block max-w-[85%] p-3 rounded-lg font-mono text-sm ${
        isUser 
          ? 'bg-cyan-900/50 text-cyan-100 border border-cyan-500/30' 
          : isTool
            ? 'bg-purple-900/50 text-purple-100 border border-purple-500/30'
            : isSystem
              ? 'bg-gray-800/50 text-gray-300 border border-gray-600/30'
              : 'bg-gray-800 text-gray-100 border border-gray-600/30'
      }`}>
        <div className="text-xs text-gray-500 mb-1">
          {isUser ? 'USER' : isTool ? 'TOOL RESULT' : isSystem ? 'SYSTEM' : 'KCLI'} 
          {message.timestamp && <span className="ml-2">{new Date(message.timestamp).toLocaleTimeString()}</span>}
        </div>
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
        
        {/* Tool calls in AI response */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-600/30">
            <div className="text-yellow-400 text-xs mb-2">PENDING TOOL CALLS:</div>
            {message.tool_calls.map((call, idx) => (
              <div key={idx} className="bg-black/30 p-2 rounded mb-2">
                <div className="text-yellow-300">{call.tool}</div>
                <pre className="text-xs text-gray-400 mt-1 overflow-auto">
                  {JSON.stringify(call.args, null, 2)}
                </pre>
                {onToolApprove && (
                  <button
                    onClick={() => onToolApprove(call)}
                    className="mt-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs py-1 px-3 rounded"
                    data-testid="execute-tool-btn"
                  >
                    Execute
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// File Browser Component
function FileBrowser({ onFileSelect, onClose }) {
  const [files, setFiles] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [loading, setLoading] = useState(false);

  const loadFiles = useCallback(async (path = '') => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/files`, { params: { path } });
      setFiles(response.data.items || []);
      setCurrentPath(path);
    } catch (error) {
      console.error('Failed to load files:', error);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const handleNavigate = (item) => {
    if (item.is_dir) {
      loadFiles(item.path);
    } else {
      onFileSelect(item);
    }
  };

  const goUp = () => {
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    loadFiles(parts.join('/'));
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" data-testid="file-browser">
      <div className="bg-gray-900 border border-cyan-500 rounded-lg w-full max-w-lg max-h-[70vh] overflow-hidden flex flex-col">
        <div className="p-3 border-b border-cyan-500/30 flex justify-between items-center">
          <div className="text-cyan-400 font-mono flex items-center gap-2">
            <Icons.Folder /> /{currentPath || 'workspace'}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <Icons.X />
          </button>
        </div>
        <div className="flex-1 overflow-auto p-2">
          {currentPath && (
            <div
              onClick={goUp}
              className="flex items-center gap-2 p-2 hover:bg-gray-800 rounded cursor-pointer text-gray-400"
            >
              <span>📂</span> ..
            </div>
          )}
          {loading ? (
            <div className="text-gray-500 p-4 text-center font-mono">Loading...</div>
          ) : files.length === 0 ? (
            <div className="text-gray-500 p-4 text-center font-mono">Empty directory</div>
          ) : (
            files.map((item, idx) => (
              <div
                key={idx}
                onClick={() => handleNavigate(item)}
                className="flex items-center gap-2 p-2 hover:bg-gray-800 rounded cursor-pointer text-gray-200 font-mono text-sm"
              >
                {item.is_dir ? <Icons.Folder /> : <Icons.File />}
                <span className="flex-1 truncate">{item.name}</span>
                {item.size && <span className="text-gray-500 text-xs">{(item.size / 1024).toFixed(1)}KB</span>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// Main App
function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState(null);
  const [pendingTool, setPendingTool] = useState(null);
  const [showFiles, setShowFiles] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load config on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await axios.get(`${API}/config`);
        setConfig(response.data);
      } catch (error) {
        console.error('Failed to load config:', error);
      }
    };
    loadConfig();
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const response = await axios.get(`${API}/conversations`);
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const createConversation = async () => {
    try {
      const response = await axios.post(`${API}/conversations`, { title: 'New Chat' });
      setCurrentConvId(response.data.id);
      setMessages([]);
      loadConversations();
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const selectConversation = async (convId) => {
    try {
      const response = await axios.get(`${API}/conversations/${convId}`);
      setCurrentConvId(convId);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const deleteConversation = async (convId) => {
    try {
      await axios.delete(`${API}/conversations/${convId}`);
      if (currentConvId === convId) {
        setCurrentConvId(null);
        setMessages([]);
      }
      loadConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Send message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input.trim(), timestamp: new Date().toISOString() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    // Save to conversation if exists
    if (currentConvId) {
      try {
        await axios.put(`${API}/conversations/${currentConvId}/messages`, userMessage);
      } catch (error) {
        console.error('Failed to save message:', error);
      }
    }

    try {
      const response = await axios.post(`${API}/chat`, {
        messages: newMessages.map(m => ({ role: m.role, content: m.content }))
      });

      const aiMessage = {
        role: 'assistant',
        content: response.data.response,
        tool_calls: response.data.tool_calls,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, aiMessage]);

      // Save AI response to conversation
      if (currentConvId) {
        try {
          await axios.put(`${API}/conversations/${currentConvId}/messages`, aiMessage);
        } catch (error) {
          console.error('Failed to save AI message:', error);
        }
      }

      // If there are tool calls, show first one for approval
      if (response.data.tool_calls && response.data.tool_calls.length > 0) {
        setPendingTool(response.data.tool_calls[0]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      }]);
    }

    setLoading(false);
    inputRef.current?.focus();
  };

  // Execute tool
  const executeTool = async (toolCall) => {
    setPendingTool(null);
    setLoading(true);

    try {
      const response = await axios.post(`${API}/tools/execute`, {
        tool: toolCall.tool,
        args: toolCall.args,
        approved: true
      });

      const toolMessage = {
        role: 'tool',
        content: response.data.success 
          ? `✓ ${toolCall.tool} executed:\n${response.data.result}`
          : `✗ ${toolCall.tool} failed:\n${response.data.result}`,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, toolMessage]);

      // Save to conversation
      if (currentConvId) {
        try {
          await axios.put(`${API}/conversations/${currentConvId}/messages`, toolMessage);
        } catch (error) {
          console.error('Failed to save tool message:', error);
        }
      }
    } catch (error) {
      console.error('Tool execution error:', error);
      setMessages(prev => [...prev, {
        role: 'tool',
        content: `✗ Tool execution failed: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      }]);
    }

    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileSelect = (file) => {
    setShowFiles(false);
    setInput(prev => prev + `read_file("${file.path}")`);
    inputRef.current?.focus();
  };

  return (
    <div className="h-screen bg-gray-950 text-gray-100 flex" data-testid="kcli-app">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-gray-900 border-r border-gray-800 flex flex-col transition-all duration-300 overflow-hidden`}>
        <div className="p-4 border-b border-gray-800">
          <div className="text-cyan-400 font-mono text-xl font-bold flex items-center gap-2">
            <Icons.Terminal /> KCLI
          </div>
          <div className="text-gray-500 text-xs font-mono mt-1">Desktop Commander</div>
        </div>
        
        <div className="p-2">
          <button
            onClick={createConversation}
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-mono py-2 px-3 rounded flex items-center justify-center gap-2 transition-colors"
            data-testid="new-chat-btn"
          >
            <Icons.Plus /> New Chat
          </button>
        </div>

        <div className="flex-1 overflow-auto p-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`p-2 rounded cursor-pointer flex items-center justify-between group ${
                currentConvId === conv.id ? 'bg-cyan-900/30 text-cyan-400' : 'hover:bg-gray-800 text-gray-400'
              }`}
              onClick={() => selectConversation(conv.id)}
            >
              <span className="font-mono text-sm truncate flex-1">{conv.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 ml-2"
              >
                <Icons.Trash />
              </button>
            </div>
          ))}
        </div>

        <div className="p-3 border-t border-gray-800">
          <button
            onClick={() => setShowFiles(true)}
            className="w-full bg-gray-800 hover:bg-gray-700 text-gray-300 font-mono py-2 px-3 rounded flex items-center justify-center gap-2 transition-colors"
            data-testid="browse-files-btn"
          >
            <Icons.Folder /> Browse Files
          </button>
        </div>

        {config && (
          <div className="p-3 border-t border-gray-800 text-xs font-mono text-gray-500">
            <div className="flex items-center gap-1">
              <Icons.Settings /> Model:
            </div>
            <div className="text-cyan-400 truncate mt-1" title={config.model}>
              {config.model.split('/').pop()}
            </div>
            <div className={`mt-2 ${config.api_configured ? 'text-green-400' : 'text-red-400'}`}>
              {config.api_configured ? '● Connected' : '○ Not configured'}
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gray-900 border-b border-gray-800 p-3 flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-400 hover:text-white p-1"
            data-testid="toggle-sidebar-btn"
          >
            <Icons.Menu />
          </button>
          <div className="font-mono text-cyan-400">
            {currentConvId ? 'Active Session' : 'KCLI Terminal'}
          </div>
          <div className="flex-1" />
          <div className="text-xs font-mono text-gray-500">
            Type a message or ask KCLI to perform actions
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-4 bg-gradient-to-b from-gray-950 to-gray-900">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="text-6xl mb-4">⌘</div>
                <h2 className="text-2xl font-mono text-cyan-400 mb-2">KCLI Desktop Commander</h2>
                <p className="text-gray-500 font-mono text-sm mb-6">
                  Your AI-powered terminal assistant with file management,<br />
                  code editing, and command execution capabilities.
                </p>
                <div className="text-left bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-gray-400 text-xs font-mono mb-2">Try asking:</div>
                  <div className="space-y-2 font-mono text-sm">
                    <div className="text-cyan-400">"List all files in the workspace"</div>
                    <div className="text-cyan-400">"Create a new Python script that prints hello world"</div>
                    <div className="text-cyan-400">"Search for TODO comments in my code"</div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <ChatMessage
                  key={idx}
                  message={msg}
                  onToolApprove={msg.tool_calls?.length > 0 ? executeTool : null}
                />
              ))}
              {loading && (
                <div className="text-cyan-400 font-mono animate-pulse">
                  <span className="inline-block">Processing</span>
                  <span className="inline-block animate-bounce">...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="bg-gray-900 border-t border-gray-800 p-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <div className="absolute left-3 top-3 text-cyan-500 font-mono">❯</div>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Enter command or ask KCLI..."
                className="w-full bg-gray-800 border border-gray-700 focus:border-cyan-500 rounded-lg py-3 pl-8 pr-4 text-gray-100 font-mono text-sm resize-none focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-colors"
                rows={2}
                disabled={loading}
                data-testid="chat-input"
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-mono py-3 px-6 rounded-lg flex items-center gap-2 transition-colors"
              data-testid="send-btn"
            >
              <Icons.Send /> SEND
            </button>
          </div>
          <div className="mt-2 text-xs font-mono text-gray-600 flex gap-4">
            <span>Enter to send</span>
            <span>Shift+Enter for new line</span>
            <span>Tools require approval</span>
          </div>
        </div>
      </div>

      {/* Tool Approval Modal */}
      <ToolApprovalModal
        toolCall={pendingTool}
        onApprove={() => executeTool(pendingTool)}
        onReject={() => setPendingTool(null)}
      />

      {/* File Browser */}
      {showFiles && (
        <FileBrowser
          onFileSelect={handleFileSelect}
          onClose={() => setShowFiles(false)}
        />
      )}
    </div>
  );
}

export default App;
