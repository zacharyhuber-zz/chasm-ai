import { useEffect, useRef, useState } from 'react';
import { Send, MessageCircle, CheckCircle2, Loader2 } from 'lucide-react';
import {
    getInterviewSession,
    sendInterviewMessage,
    type InterviewMessage,
} from '../api';

interface InterviewProps {
    sessionId: string;
}

export default function Interview({ sessionId }: InterviewProps) {
    const [messages, setMessages] = useState<InterviewMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [initializing, setInitializing] = useState(true);
    const bottomRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Load session on mount + start interview
    useEffect(() => {
        (async () => {
            try {
                const session = await getInterviewSession(sessionId);
                if (session.status === 'completed') {
                    setMessages(session.messages);
                    setIsComplete(true);
                    setInitializing(false);
                    return;
                }
                if (session.messages.length > 0) {
                    // Resume existing session
                    setMessages(session.messages);
                    setInitializing(false);
                    return;
                }
                // Start the interview by sending an empty message to get the greeting
                const res = await sendInterviewMessage(sessionId, '');
                setMessages([{ role: 'assistant', content: res.content }]);
            } catch {
                setError('Could not load interview session. Please check the link.');
            } finally {
                setInitializing(false);
            }
        })();
    }, [sessionId]);

    const handleSend = async () => {
        const text = input.trim();
        if (!text || loading || isComplete) return;

        const userMsg: InterviewMessage = { role: 'user', content: text };
        setMessages((prev) => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await sendInterviewMessage(sessionId, text);
            setMessages((prev) => [...prev, { role: 'assistant', content: res.content }]);
            if (res.is_complete) {
                setIsComplete(true);
            }
        } catch {
            setError('Failed to send message. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    if (initializing) {
        return (
            <div style={styles.loadingContainer}>
                <Loader2 size={32} style={styles.spinner} />
                <p style={styles.loadingText}>Preparing your interview…</p>
            </div>
        );
    }

    if (error && messages.length === 0) {
        return (
            <div style={styles.loadingContainer}>
                <p style={{ color: '#f43f5e', fontSize: 16 }}>{error}</p>
            </div>
        );
    }

    return (
        <div style={styles.wrapper}>
            {/* Header */}
            <div style={styles.header}>
                <div style={styles.headerIcon}>
                    <MessageCircle size={20} />
                </div>
                <div>
                    <h1 style={styles.headerTitle}>Employee Feedback Interview</h1>
                    <p style={styles.headerSubtitle}>
                        Share your thoughts about our products — your feedback drives real change.
                    </p>
                </div>
            </div>

            {/* Messages */}
            <div style={styles.messagesContainer}>
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        style={{
                            ...styles.messageBubble,
                            ...(msg.role === 'user' ? styles.userBubble : styles.assistantBubble),
                            animationDelay: `${idx * 0.05}s`,
                        }}
                        className="fade-in"
                    >
                        <div style={styles.roleLabel}>
                            {msg.role === 'user' ? 'You' : 'Interviewer'}
                        </div>
                        <div style={styles.messageText}>{msg.content}</div>
                    </div>
                ))}

                {loading && (
                    <div style={{ ...styles.messageBubble, ...styles.assistantBubble }} className="fade-in">
                        <div style={styles.roleLabel}>Interviewer</div>
                        <div style={styles.typingIndicator}>
                            <span style={styles.dot} />
                            <span style={{ ...styles.dot, animationDelay: '0.2s' }} />
                            <span style={{ ...styles.dot, animationDelay: '0.4s' }} />
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Complete banner */}
            {isComplete && (
                <div style={styles.completeBanner} className="fade-in">
                    <CheckCircle2 size={20} style={{ color: '#10b981' }} />
                    <span>
                        Interview complete — thank you for your valuable feedback!
                        You can close this tab.
                    </span>
                </div>
            )}

            {/* Input */}
            {!isComplete && (
                <div style={styles.inputBar}>
                    <textarea
                        rows={1}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type your response…"
                        disabled={loading}
                        style={styles.textarea}
                    />
                    <button
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        style={{
                            ...styles.sendButton,
                            opacity: loading || !input.trim() ? 0.4 : 1,
                        }}
                    >
                        <Send size={18} />
                    </button>
                </div>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Styles (inline for single-component portability)
// ---------------------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
    wrapper: {
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        maxWidth: 720,
        margin: '0 auto',
        padding: '0 16px',
        background: 'var(--bg-primary)',
    },
    loadingContainer: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: 16,
    },
    spinner: {
        color: 'var(--accent-blue)',
        animation: 'spin 1s linear infinite',
    },
    loadingText: {
        color: 'var(--text-secondary)',
        fontSize: 14,
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: '24px 0 20px',
        borderBottom: '1px solid var(--border)',
    },
    headerIcon: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 44,
        height: 44,
        borderRadius: 12,
        background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
        color: '#fff',
        flexShrink: 0,
    },
    headerTitle: {
        fontSize: 20,
        fontWeight: 700,
        letterSpacing: '-0.02em',
        color: 'var(--text-primary)',
    },
    headerSubtitle: {
        fontSize: 13,
        color: 'var(--text-muted)',
        marginTop: 2,
    },
    messagesContainer: {
        flex: 1,
        overflowY: 'auto',
        padding: '20px 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
    },
    messageBubble: {
        maxWidth: '85%',
        padding: '14px 18px',
        borderRadius: 16,
        lineHeight: 1.6,
    },
    assistantBubble: {
        alignSelf: 'flex-start',
        background: 'linear-gradient(135deg, rgba(26, 31, 54, 0.9), rgba(17, 24, 39, 0.7))',
        border: '1px solid var(--border)',
        borderBottomLeftRadius: 4,
    },
    userBubble: {
        alignSelf: 'flex-end',
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.15))',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        borderBottomRightRadius: 4,
    },
    roleLabel: {
        fontSize: 11,
        fontWeight: 600,
        textTransform: 'uppercase' as const,
        letterSpacing: '0.05em',
        color: 'var(--text-muted)',
        marginBottom: 4,
    },
    messageText: {
        fontSize: 14,
        color: 'var(--text-primary)',
        whiteSpace: 'pre-wrap' as const,
    },
    typingIndicator: {
        display: 'flex',
        gap: 4,
        padding: '4px 0',
    },
    dot: {
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: 'var(--text-muted)',
        animation: 'pulse-glow 1.4s ease-in-out infinite',
    },
    completeBanner: {
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '14px 20px',
        borderRadius: 12,
        background: 'rgba(16, 185, 129, 0.1)',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        color: '#10b981',
        fontSize: 14,
        fontWeight: 500,
        margin: '0 0 16px',
    },
    inputBar: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: 10,
        padding: '16px 0 24px',
        borderTop: '1px solid var(--border)',
    },
    textarea: {
        flex: 1,
        resize: 'none' as const,
        padding: '12px 16px',
        borderRadius: 12,
        border: '1px solid var(--border)',
        background: 'rgba(26, 31, 54, 0.6)',
        color: 'var(--text-primary)',
        fontSize: 14,
        fontFamily: 'inherit',
        lineHeight: 1.5,
        outline: 'none',
        transition: 'border-color 0.2s',
    },
    sendButton: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 44,
        height: 44,
        borderRadius: 12,
        border: 'none',
        background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
        color: '#fff',
        cursor: 'pointer',
        transition: 'opacity 0.2s, transform 0.1s',
        flexShrink: 0,
    },
};
