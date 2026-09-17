import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  loadConversations,
  saveConversations,
  loadActiveConvId,
  saveActiveConvId,
  loadSettings,
  saveSettings,
  createNewConversation,
} from './utils/storage';
import {
  Conversation,
  Message,
  ModelMode,
  CanvasArtifact,
  UserSettings,
  Attachment,
} from './types';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { PromptInput } from './components/PromptInput';
import { StarterCards } from './components/StarterCards';
import { ArtifactCanvas } from './components/ArtifactCanvas';
import { SettingsModal } from './components/SettingsModal';

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations());
  const [activeId, setActiveId] = useState<string | null>(() => {
    const saved = loadActiveConvId();
    return saved || null;
  });
  const [settings, setSettings] = useState<UserSettings>(() => loadSettings());
  const [modelMode, setModelMode] = useState<ModelMode>('nova');
  const [webSearch, setWebSearch] = useState<boolean>(settings.webSearchDefault);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => window.innerWidth >= 1024);
  const [activeArtifact, setActiveArtifact] = useState<CanvasArtifact | null>(null);
  const [canvasOpen, setCanvasOpen] = useState<boolean>(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  };

  // Sync active conversation
  const activeConversation = useMemo(() => {
    return conversations.find((c) => c.id === activeId) || null;
  }, [conversations, activeId]);

  // Persist conversations
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // Persist active ID
  useEffect(() => {
    saveActiveConvId(activeId);
  }, [activeId]);

  // Keyboard shortcut listener (Cmd/Ctrl + N for new chat, Cmd/Ctrl + K to focus search)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        handleNewChat();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [modelMode]);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollToBottom(false);
  }, [activeConversation?.messages.length]);

  const handleNewChat = (mode: ModelMode = modelMode) => {
    if (isGenerating && abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsGenerating(false);
    }
    const newConv = createNewConversation(mode);
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
    setModelMode(mode);
    setActiveArtifact(null);
    setCanvasOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    setActiveId(id);
    const conv = conversations.find((c) => c.id === id);
    if (conv?.modelMode) {
      setModelMode(conv.modelMode);
    }
  };

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => {
      const updated = prev.filter((c) => c.id !== id);
      if (activeId === id) {
        const next = updated[0]?.id || null;
        setActiveId(next);
      }
      return updated;
    });
  };

  const handleRenameConversation = (id: string, newTitle: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: newTitle, updatedAt: Date.now() } : c))
    );
  };

  const handleTogglePinConversation = (id: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, pinned: !c.pinned } : c))
    );
  };

  const handleClearAllConversations = () => {
    setConversations([]);
    setActiveId(null);
    setActiveArtifact(null);
    setCanvasOpen(false);
  };

  const handleExportAll = () => {
    const json = JSON.stringify(conversations, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `polaris-chats-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Trigger title generation for conversation
  const generateTitle = async (convId: string, promptText: string) => {
    try {
      const res = await fetch('/api/title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText }),
      });
      const data = await res.json();
      if (data.title) {
        setConversations((prev) =>
          prev.map((c) => (c.id === convId ? { ...c, title: data.title } : c))
        );
      }
    } catch (e) {
      console.error('Title generation failed', e);
    }
  };

  // Inspect model response for code artifacts to automatically populate canvas
  const detectArtifact = (fullText: string) => {
    const htmlMatch = fullText.match(/```(?:html|htm)\s*([\s\S]*?)```/i);
    if (htmlMatch && htmlMatch[1]) {
      return {
        id: 'art_' + Date.now(),
        title: 'HTML & Web Preview',
        language: 'html',
        code: htmlMatch[1].trim(),
        type: 'html' as const,
      };
    }
    const svgMatch = fullText.match(/```(?:svg)\s*([\s\S]*?)```/i) || fullText.match(/(<svg[\s\S]*?<\/svg>)/i);
    if (svgMatch && svgMatch[1]) {
      return {
        id: 'art_' + Date.now(),
        title: 'Vector SVG Graphic',
        language: 'svg',
        code: svgMatch[1].trim(),
        type: 'svg' as const,
      };
    }
    return null;
  };

  // Send message
  const handleSendMessage = async (
    text: string,
    attachments: Attachment[] = [],
    customMode?: ModelMode,
    customSearch?: boolean
  ) => {
    const effectiveMode = customMode || modelMode;
    const effectiveSearch = customSearch !== undefined ? customSearch : webSearch;

    let targetConv = activeConversation;

    if (!targetConv) {
      targetConv = createNewConversation(effectiveMode);
      setConversations((prev) => [targetConv!, ...prev]);
      setActiveId(targetConv.id);
    }

    const currentConvId = targetConv.id;

    const userMessage: Message = {
      id: 'msg_' + Date.now(),
      role: 'user',
      text,
      timestamp: Date.now(),
      attachments,
    };

    const assistantPlaceholderId = 'msg_' + (Date.now() + 1);
    const assistantMessage: Message = {
      id: assistantPlaceholderId,
      role: 'assistant',
      text: '',
      timestamp: Date.now(),
      isStreaming: true,
    };

    const updatedMessages = [...targetConv.messages, userMessage, assistantMessage];

    // Update conversation with user message and placeholder
    setConversations((prev) =>
      prev.map((c) =>
        c.id === currentConvId
          ? {
              ...c,
              messages: updatedMessages,
              updatedAt: Date.now(),
              modelMode: effectiveMode,
            }
          : c
      )
    );

    // If first user message, trigger title generation
    if (targetConv.messages.length === 0) {
      generateTitle(currentConvId, text);
    }

    // Set up SSE stream
    setIsGenerating(true);
    abortControllerRef.current = new AbortController();

    try {
      // Send previous messages + new user message
      const historyToSend = [...targetConv.messages, userMessage];

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          messages: historyToSend,
          modelMode: effectiveMode,
          webSearch: effectiveSearch,
          customInstruction: settings.customInstruction,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = '';
      let buffer = '';

      if (!reader) throw new Error('Failed to read stream');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            const rawData = line.replace('data:', '').trim();
            if (!rawData) continue;

            try {
              const data = JSON.parse(rawData);

              if (currentEvent === 'chunk' && data.text) {
                accumulatedText += data.text;
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== currentConvId) return c;
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantPlaceholderId
                          ? { ...m, text: accumulatedText, isStreaming: true }
                          : m
                      ),
                    };
                  })
                );
              } else if (currentEvent === 'grounding') {
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== currentConvId) return c;
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantPlaceholderId
                          ? {
                              ...m,
                              sources: data.sources || [],
                              searchQueries: data.queries || [],
                            }
                          : m
                      ),
                    };
                  })
                );
              } else if (currentEvent === 'error') {
                accumulatedText += `\n\n**Error:** ${data.message || 'An error occurred'}`;
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== currentConvId) return c;
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantPlaceholderId
                          ? { ...m, text: accumulatedText, isStreaming: false, error: data.message }
                          : m
                      ),
                    };
                  })
                );
              } else if (currentEvent === 'done') {
                // Done event
              }
            } catch (err) {
              console.error('Error parsing SSE data line', err);
            }
          }
        }
      }

      // Finalize message
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== currentConvId) return c;
          return {
            ...c,
            messages: c.messages.map((m) =>
              m.id === assistantPlaceholderId
                ? { ...m, isStreaming: false }
                : m
            ),
          };
        })
      );

      // Check if text has code artifact and set it
      const artifact = detectArtifact(accumulatedText);
      if (artifact) {
        setActiveArtifact(artifact);
        // If in architect mode, automatically open canvas for seamless experience
        if (effectiveMode === 'architect') {
          setCanvasOpen(true);
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User aborted intentionally
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== currentConvId) return c;
            return {
              ...c,
              messages: c.messages.map((m) =>
                m.id === assistantPlaceholderId
                  ? { ...m, isStreaming: false }
                  : m
              ),
            };
          })
        );
      } else {
        console.error('Chat stream error:', err);
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== currentConvId) return c;
            return {
              ...c,
              messages: c.messages.map((m) =>
                m.id === assistantPlaceholderId
                  ? {
                      ...m,
                      text: m.text ? m.text + '\n\n*(Generation interrupted)*' : 'Failed to connect to Polaris AI.',
                      isStreaming: false,
                    }
                  : m
              ),
            };
          })
        );
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsGenerating(false);
  };

  const handleRegenerateLast = () => {
    if (!activeConversation || activeConversation.messages.length === 0) return;
    const msgs = [...activeConversation.messages];
    // Find last user message
    let lastUserIndex = -1;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        lastUserIndex = i;
        break;
      }
    }

    if (lastUserIndex === -1) return;

    const userMsg = msgs[lastUserIndex];
    // Trim conversation up to before this user message
    const trimmed = msgs.slice(0, lastUserIndex);

    setConversations((prev) =>
      prev.map((c) => (c.id === activeId ? { ...c, messages: trimmed } : c))
    );

    handleSendMessage(userMsg.text, userMsg.attachments || []);
  };

  const handleEditUserMessage = (editedText: string) => {
    handleSendMessage(editedText);
  };

  const handleOpenArtifactInCanvas = (artifact: CanvasArtifact) => {
    setActiveArtifact(artifact);
    setCanvasOpen(true);
  };

  const messages = activeConversation?.messages || [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0c0f17] text-slate-100 font-sans">
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations}
        activeId={activeId}
        onSelectConversation={handleSelectConversation}
        onNewChat={() => handleNewChat()}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        onTogglePinConversation={handleTogglePinConversation}
        onExportAll={handleExportAll}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative">
        {/* Header */}
        <Header
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          modelMode={modelMode}
          onSelectModelMode={(mode) => {
            setModelMode(mode);
            if (activeConversation) {
              setConversations((prev) =>
                prev.map((c) => (c.id === activeId ? { ...c, modelMode: mode } : c))
              );
            }
          }}
          hasArtifact={Boolean(activeArtifact)}
          canvasOpen={canvasOpen}
          onToggleCanvas={() => setCanvasOpen(!canvasOpen)}
          onNewChat={() => handleNewChat()}
          onOpenSettings={() => setSettingsModalOpen(true)}
          webSearch={webSearch}
        />

        {/* Chat / Canvas Split View Container */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* Messages & Prompt Area */}
          <div className="flex-1 flex flex-col h-full min-w-0 relative">
            {messages.length === 0 ? (
              <div className="flex-1 overflow-y-auto flex items-center justify-center">
                <StarterCards
                  onSelectPrompt={(prompt, mode, search) => {
                    handleSendMessage(prompt, [], mode, search);
                  }}
                />
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800">
                <div className="py-4">
                  {messages.map((msg, idx) => (
                    <ChatMessage
                      key={msg.id}
                      message={msg}
                      isLast={idx === messages.length - 1}
                      onRegenerate={handleRegenerateLast}
                      onEditUserMessage={handleEditUserMessage}
                      onOpenInCanvas={handleOpenArtifactInCanvas}
                    />
                  ))}
                  <div ref={messagesEndRef} className="h-4" />
                </div>
              </div>
            )}

            {/* Floating Prompt Bar */}
            <div className="shrink-0">
              <PromptInput
                onSend={handleSendMessage}
                onStop={handleStopGenerating}
                isGenerating={isGenerating}
                webSearch={webSearch}
                onToggleWebSearch={() => setWebSearch(!webSearch)}
              />
            </div>
          </div>

          {/* Interactive Artifact Canvas (Split Screen) */}
          {canvasOpen && activeArtifact && (
            <ArtifactCanvas
              artifact={activeArtifact}
              onClose={() => setCanvasOpen(false)}
            />
          )}
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        open={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        settings={settings}
        onSaveSettings={(newSettings) => {
          setSettings(newSettings);
          saveSettings(newSettings);
        }}
        onClearAllConversations={handleClearAllConversations}
      />
    </div>
  );
}
