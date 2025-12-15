const { useState, useEffect } = React;

function App() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSearch = async (query) => {
        setLoading(true);
        setError(null);
        setData(null);

        try {
            const tickers = query.split(',').map(s => s.trim()).filter(s => s.length > 0);

            // Fetch from our local API
            const response = await fetch('/api/analyze-batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ tickers })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to fetch data');
            }
            const result = await response.json();
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container">
            <header className="header">
                <h1>Stock Analyzer Pro</h1>
                <p>Professional Technical Analysis & Sentiment</p>
            </header>

            <Search onSearch={handleSearch} disabled={loading} />

            <YouTubeStocks />

            {loading && (
                <div style={{ textAlign: 'center', margin: '2rem' }}>
                    <div style={{ fontSize: '1.5rem', color: 'var(--accent-color)' }}>Analyzing Market Data...</div>
                </div>
            )}

            {error && (
                <div style={{ textAlign: 'center', color: 'var(--danger)', margin: '2rem', fontSize: '1.2rem' }}>
                    Error: {error}
                </div>
            )}

            {data && <Dashboard data={data} />}
        </div>
    );
}

function MarketNews() {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        fetch('/api/market-news')
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch news');
                return res.json();
            })
            .then(data => {
                setNews(data.news || []);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    const getSentimentStyle = (sentiment) => {
        switch (sentiment) {
            case 'bullish':
                return { color: '#2ecc71', icon: '📈', bg: 'rgba(46, 204, 113, 0.1)' };
            case 'bearish':
                return { color: '#e74c3c', icon: '📉', bg: 'rgba(231, 76, 60, 0.1)' };
            default:
                return { color: '#95a5a6', icon: '📊', bg: 'rgba(149, 165, 166, 0.1)' };
        }
    };

    const displayedNews = expanded ? news : news.slice(0, 5);

    return (
        <div style={{
            background: 'linear-gradient(135deg, #1a1c2e, #252a40)',
            borderRadius: '16px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>📰</span>
                    <h3 style={{
                        margin: 0,
                        fontSize: '1.2rem',
                        fontWeight: 700,
                        background: 'linear-gradient(135deg, #f39c12, #e74c3c)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent'
                    }}>
                        Top Market News
                    </h3>
                </div>
                {news.length > 5 && (
                    <button
                        onClick={() => setExpanded(!expanded)}
                        style={{
                            background: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            borderRadius: '20px',
                            padding: '0.4rem 1rem',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.1)'}
                        onMouseLeave={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.05)'}
                    >
                        {expanded ? 'Show Less' : `Show All (${news.length})`}
                    </button>
                )}
            </div>

            {loading && (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    Fetching latest market news...
                </div>
            )}

            {error && (
                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-secondary)' }}>
                    Unable to load news
                </div>
            )}

            {!loading && !error && news.length === 0 && (
                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-secondary)' }}>
                    No news available
                </div>
            )}

            {!loading && !error && news.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {displayedNews.map((item, idx) => {
                        const sentimentStyle = getSentimentStyle(item.sentiment);
                        return (
                            <a
                                key={idx}
                                href={item.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '0.75rem',
                                    padding: '0.75rem',
                                    background: 'rgba(255, 255, 255, 0.02)',
                                    borderRadius: '10px',
                                    textDecoration: 'none',
                                    color: 'inherit',
                                    transition: 'all 0.2s ease',
                                    border: '1px solid transparent'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                                    e.currentTarget.style.borderColor = 'transparent';
                                }}
                            >
                                <span style={{
                                    fontSize: '1.2rem',
                                    lineHeight: 1,
                                    marginTop: '2px'
                                }}>
                                    {sentimentStyle.icon}
                                </span>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{
                                        fontSize: '0.9rem',
                                        fontWeight: 500,
                                        lineHeight: 1.4,
                                        marginBottom: '0.35rem',
                                        color: '#fff',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        display: '-webkit-box',
                                        WebkitLineClamp: 2,
                                        WebkitBoxOrient: 'vertical'
                                    }}>
                                        {item.title}
                                    </div>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        fontSize: '0.75rem',
                                        color: 'var(--text-secondary)'
                                    }}>
                                        <span>{item.publisher}</span>
                                        <span>•</span>
                                        <span>{item.published}</span>
                                        {item.related_ticker && (
                                            <>
                                                <span>•</span>
                                                <span style={{
                                                    padding: '0.15rem 0.4rem',
                                                    background: 'rgba(102, 126, 234, 0.2)',
                                                    borderRadius: '4px',
                                                    fontWeight: 600,
                                                    color: '#667eea'
                                                }}>
                                                    {item.related_ticker}
                                                </span>
                                            </>
                                        )}
                                        <span style={{
                                            padding: '0.15rem 0.4rem',
                                            background: sentimentStyle.bg,
                                            borderRadius: '4px',
                                            fontWeight: 500,
                                            color: sentimentStyle.color,
                                            textTransform: 'capitalize'
                                        }}>
                                            {item.sentiment}
                                        </span>
                                    </div>
                                </div>
                            </a>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

function YouTubeStocks() {
    const [recommendations, setRecommendations] = useState([]);
    const [videoList, setVideoList] = useState([]);
    const [loading, setLoading] = useState(false);
    const [listLoading, setListLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastFetched, setLastFetched] = useState(null);
    const [viewMode, setViewMode] = useState('recommendations'); // 'recommendations' or 'list'

    const fetchRecommendations = async () => {
        setLoading(true);
        setError(null);
        setViewMode('recommendations');
        try {
            const res = await fetch('/api/youtube-stocks');
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to fetch');
            }
            const data = await res.json();
            setRecommendations(data.recommendations || []);
            setLastFetched(new Date().toLocaleTimeString());
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const fetchVideoList = async () => {
        setListLoading(true);
        setError(null);
        setViewMode('list');
        try {
            const res = await fetch('/api/youtube-video-list');
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to fetch videos');
            }
            const data = await res.json();
            setVideoList(data.videos || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setListLoading(false);
        }
    };

    const getSentimentStyle = (sentiment) => {
        switch (sentiment?.toUpperCase()) {
            case 'BULLISH':
                return { color: '#2ecc71', bg: 'rgba(46, 204, 113, 0.15)', icon: '🟢' };
            case 'BEARISH':
                return { color: '#e74c3c', bg: 'rgba(231, 76, 60, 0.15)', icon: '🔴' };
            default:
                return { color: '#f39c12', bg: 'rgba(243, 156, 18, 0.15)', icon: '🟡' };
        }
    };

    return (
        <div style={{
            background: 'linear-gradient(135deg, #1a1c2e, #252a40)',
            borderRadius: '16px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem',
                flexWrap: 'wrap',
                gap: '1rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>🎬</span>
                    <h3 style={{
                        margin: 0,
                        fontSize: '1.1rem',
                        fontWeight: 700,
                        color: '#fff'
                    }}>
                        YouTube Stock Picks
                    </h3>
                    <span style={{
                        fontSize: '0.75rem',
                        padding: '0.25rem 0.5rem',
                        background: 'rgba(102, 126, 234, 0.2)',
                        borderRadius: '4px',
                        color: '#667eea'
                    }}>
                        AI-Powered
                    </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        onClick={fetchVideoList}
                        disabled={loading || listLoading}
                        style={{
                            padding: '0.5rem 1rem',
                            background: listLoading ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            color: 'white',
                            borderRadius: '8px',
                            cursor: (loading || listLoading) ? 'not-allowed' : 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => !listLoading && (e.target.style.background = 'rgba(255, 255, 255, 0.1)')}
                        onMouseLeave={(e) => !listLoading && (e.target.style.background = 'rgba(255, 255, 255, 0.05)')}
                    >
                        {listLoading ? '⏳ Fetching...' : '📺 Latest Videos'}
                    </button>
                    <button
                        onClick={fetchRecommendations}
                        disabled={loading || listLoading}
                        style={{
                            padding: '0.5rem 1rem',
                            background: loading ? 'rgba(102, 126, 234, 0.5)' : 'linear-gradient(135deg, #667eea, #764ba2)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: (loading || listLoading) ? 'not-allowed' : 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
                        }}
                    >
                        {loading ? '⏳ Scanning...' : '🔍 AI Scan Latest'}
                    </button>
                </div>
            </div>

            {error && (
                <div style={{ color: '#e74c3c', padding: '0.5rem', marginBottom: '1rem' }}>
                    Error: {error}
                </div>
            )}

            {!loading && !listLoading && recommendations.length === 0 && videoList.length === 0 && !error && (
                <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                    Select an option to fetch YouTube content
                </div>
            )}

            {loading && (
                <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                    <div>🎬 Fetching latest videos...</div>
                    <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>📝 Extracting transcripts & analyzing with Gemini AI</div>
                </div>
            )}

            {listLoading && (
                <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                    <div>📺 Fetching video list...</div>
                </div>
            )}

            {/* Video List View */}
            {!listLoading && viewMode === 'list' && videoList.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        Latest Uploads (Raw List)
                    </div>
                    {videoList.map((video, idx) => (
                        <a
                            key={idx}
                            href={video.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '1rem',
                                background: 'rgba(255, 255, 255, 0.03)',
                                borderRadius: '12px',
                                padding: '1rem',
                                border: '1px solid rgba(255, 255, 255, 0.08)',
                                textDecoration: 'none',
                                color: 'inherit',
                                transition: 'background 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                        >
                            <span style={{ fontSize: '1.5rem' }}>▶️</span>
                            <div>
                                <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: '#fff' }}>{video.title}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    {video.published} • {video.channel}
                                </div>
                            </div>
                        </a>
                    ))}
                </div>
            )}

            {/* Recommendations View */}
            {!loading && viewMode === 'recommendations' && recommendations.length > 0 && (
                <>
                    {lastFetched && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                            Last updated: {lastFetched}
                        </div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {recommendations.map((rec, idx) => {
                            const sentimentStyle = getSentimentStyle(rec.sentiment);
                            return (
                                <div
                                    key={idx}
                                    style={{
                                        background: 'rgba(255, 255, 255, 0.03)',
                                        borderRadius: '12px',
                                        padding: '1rem',
                                        border: '1px solid rgba(255, 255, 255, 0.08)'
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <span style={{
                                                fontSize: '1.1rem',
                                                fontWeight: 700,
                                                color: '#fff',
                                                padding: '0.25rem 0.5rem',
                                                background: 'rgba(102, 126, 234, 0.2)',
                                                borderRadius: '6px'
                                            }}>
                                                {rec.ticker}
                                            </span>
                                            <span style={{
                                                padding: '0.2rem 0.5rem',
                                                background: sentimentStyle.bg,
                                                borderRadius: '4px',
                                                fontSize: '0.75rem',
                                                fontWeight: 600,
                                                color: sentimentStyle.color
                                            }}>
                                                {sentimentStyle.icon} {rec.sentiment}
                                            </span>
                                            {rec.mentions > 1 && (
                                                <span style={{
                                                    padding: '0.15rem 0.4rem',
                                                    background: 'rgba(243, 156, 18, 0.2)',
                                                    borderRadius: '4px',
                                                    fontSize: '0.7rem',
                                                    color: '#f39c12'
                                                }}>
                                                    🔥 {rec.mentions}x mentioned
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {rec.sources && rec.sources.map((src, srcIdx) => (
                                        <div key={srcIdx} style={{
                                            fontSize: '0.8rem',
                                            color: 'var(--text-secondary)',
                                            marginTop: '0.5rem',
                                            paddingLeft: '0.5rem',
                                            borderLeft: '2px solid rgba(102, 126, 234, 0.3)'
                                        }}>
                                            <a href={src.url} target="_blank" rel="noopener noreferrer" style={{
                                                color: '#667eea',
                                                textDecoration: 'none'
                                            }}>
                                                📺 {src.video}
                                            </a>
                                            {src.published && (
                                                <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', color: '#888' }}>
                                                    📅 {src.published}
                                                </span>
                                            )}
                                            {src.reason && (
                                                <div style={{ marginTop: '0.25rem', color: '#aaa' }}>
                                                    💡 {src.reason}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            );
                        })}
                    </div>
                </>
            )}
        </div>
    );
}

function Search({ onSearch, disabled }) {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(true);

    // Load watchlist from config.json on mount
    useEffect(() => {
        fetch('/static/config.json')
            .then(res => res.json())
            .then(config => {
                setInput(config.defaultWatchlist.join(', '));
                setLoading(false);
            })
            .catch(() => {
                setInput('AAPL, NVDA, TSLA'); // Fallback
                setLoading(false);
            });
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim()) {
            onSearch(input.trim());
        }
    };

    return (
        <div className="search-container">
            <form className="search-box" onSubmit={handleSubmit}>
                <input
                    type="text"
                    className="search-input"
                    placeholder={loading ? "Loading watchlist..." : "Enter Symbols (e.g., AAPL, NVDA)..."}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={disabled || loading}
                />
                <button type="submit" className="search-button" disabled={disabled || loading}>
                    {disabled ? '...' : 'ANALYZE'}
                </button>
            </form>
        </div>
    );
}


function Dashboard({ data }) {
    const stocks = Array.isArray(data) ? data : [data];
    return (
        <div>
            <CSPSummaryTable stocks={stocks} />
            <div className="stock-grid">
                {stocks.map((stock, idx) => (
                    <StockAnalysis key={stock.symbol || idx} data={stock} />
                ))}
            </div>
        </div>
    );
}

function CSPSummaryTable({ stocks }) {
    const [cspData, setCspData] = useState({});
    const [loading, setLoading] = useState(true);
    const [emailStatus, setEmailStatus] = useState(null); // null, 'sending', 'sent', 'error'

    useEffect(() => {
        const fetchAllCSPData = async () => {
            setLoading(true);
            const results = {};

            for (const stock of stocks) {
                if (stock.error || !stock.symbol) continue;
                try {
                    // Fetch both volatility and CSP metrics in parallel
                    const [volRes, metricsRes] = await Promise.all([
                        fetch(`/api/volatility/${stock.symbol}`),
                        fetch(`/api/csp-metrics/${stock.symbol}`)
                    ]);

                    const volData = volRes.ok ? await volRes.json() : {};
                    const metricsData = metricsRes.ok ? await metricsRes.json() : {};

                    results[stock.symbol] = { ...volData, ...metricsData };
                } catch (e) {
                    console.error(`Failed to fetch CSP data for ${stock.symbol}`);
                }
            }

            setCspData(results);
            setLoading(false);
        };

        if (stocks && stocks.length > 0) {
            fetchAllCSPData();
        }
    }, [stocks]);

    // Determine CSP suitability rating
    const getCSPRating = (volData) => {
        if (!volData) return { text: 'N/A', color: 'var(--text-secondary)', icon: '⚪' };

        const rank = volData.iv_rank !== null ? volData.iv_rank : volData.hv_rank;
        if (rank === null) return { text: 'N/A', color: 'var(--text-secondary)', icon: '⚪' };

        if (rank >= 75) {
            return { text: 'Excellent', color: '#9b59b6', icon: '🟣', rank };
        } else if (rank >= 50) {
            return { text: 'Good', color: 'var(--success)', icon: '🟢', rank };
        } else if (rank >= 25) {
            return { text: 'Moderate', color: '#f39c12', icon: '🟡', rank };
        } else {
            return { text: 'Poor', color: 'var(--danger)', icon: '🔴', rank };
        }
    };

    // Sort stocks by CSP suitability (best first)
    const sortedStocks = [...stocks].filter(s => !s.error && s.symbol).sort((a, b) => {
        const rankA = getCSPRating(cspData[a.symbol]).rank || 0;
        const rankB = getCSPRating(cspData[b.symbol]).rank || 0;
        return rankB - rankA;
    });

    // Send email handler
    const handleSendEmail = async () => {
        setEmailStatus('sending');
        try {
            const response = await fetch('/api/send-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stocks: stocks,
                    csp_data: cspData
                })
            });

            if (response.ok) {
                setEmailStatus('sent');
                setTimeout(() => setEmailStatus(null), 3000);
            } else {
                const err = await response.json();
                console.error('Email error:', err);
                setEmailStatus('error');
                setTimeout(() => setEmailStatus(null), 3000);
            }
        } catch (e) {
            console.error('Email error:', e);
            setEmailStatus('error');
            setTimeout(() => setEmailStatus(null), 3000);
        }
    };

    return (
        <div style={{
            background: 'linear-gradient(135deg, #ffffff, #f8f9fc)',
            borderRadius: '16px',
            padding: '1.25rem',
            marginBottom: '2rem',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>📊</span>
                    <h3 style={{
                        margin: 0,
                        fontSize: '1.2rem',
                        fontWeight: 700,
                        background: 'linear-gradient(135deg, #667eea, #764ba2)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent'
                    }}>
                        CSP Opportunity Summary
                    </h3>
                </div>
                <button
                    onClick={handleSendEmail}
                    disabled={loading || emailStatus === 'sending'}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 1rem',
                        background: emailStatus === 'sent' ? '#27ae60' :
                            emailStatus === 'error' ? '#e74c3c' :
                                'linear-gradient(135deg, #667eea, #764ba2)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: loading || emailStatus === 'sending' ? 'not-allowed' : 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        opacity: loading || emailStatus === 'sending' ? 0.7 : 1,
                        transition: 'all 0.2s ease'
                    }}
                >
                    {emailStatus === 'sending' ? (
                        <>⏳ Sending...</>
                    ) : emailStatus === 'sent' ? (
                        <>✅ Sent!</>
                    ) : emailStatus === 'error' ? (
                        <>❌ Failed</>
                    ) : (
                        <>📧 Email Report</>
                    )}
                </button>
            </div>

            {loading ? (
                <div style={{
                    textAlign: 'center',
                    padding: '1rem',
                    color: 'var(--text-secondary)'
                }}>
                    Analyzing volatility data...
                </div>
            ) : (
                <div style={{ overflowX: 'auto' }}>
                    <table style={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        fontSize: '0.9rem'
                    }}>
                        <thead>
                            <tr style={{
                                borderBottom: '2px solid rgba(0, 0, 0, 0.1)'
                            }}>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    Symbol
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    Price
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    1D Change
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    RSI
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    52W Low
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    52W High
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    IV/HV Rank
                                </th>
                                <th style={{
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    color: '#555',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    CSP Rating
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedStocks.map((stock, idx) => {
                                const volData = cspData[stock.symbol];
                                const rating = getCSPRating(volData);
                                const rank = volData?.iv_rank ?? volData?.hv_rank;

                                return (
                                    <tr
                                        key={stock.symbol}
                                        style={{
                                            borderBottom: '1px solid rgba(0, 0, 0, 0.06)',
                                            transition: 'background 0.2s ease',
                                            cursor: 'pointer',
                                            background: idx === 0 && rating.text === 'Excellent'
                                                ? 'rgba(155, 89, 182, 0.08)'
                                                : 'transparent'
                                        }}
                                        onClick={() => {
                                            const element = document.getElementById(`stock-${stock.symbol}`);
                                            if (element) {
                                                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                            }
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.03)'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = idx === 0 && rating.text === 'Excellent' ? 'rgba(155, 89, 182, 0.08)' : 'transparent'}
                                    >
                                        <td style={{
                                            padding: '0.75rem 1rem',
                                            fontWeight: 700,
                                            fontSize: '1rem',
                                            color: '#1a1a2e'
                                        }}>
                                            {stock.symbol}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem',
                                            fontWeight: 600,
                                            color: '#2e7d32'
                                        }}>
                                            ${stock.price?.toFixed(2) || 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem',
                                            fontWeight: 600,
                                            color: stock.change_1d >= 0 ? '#27ae60' : '#e74c3c'
                                        }}>
                                            {stock.change_1d !== null && stock.change_1d !== undefined ? (
                                                <>
                                                    {stock.change_1d >= 0 ? '+' : ''}{stock.change_1d.toFixed(2)}
                                                    <span style={{ fontSize: '0.8rem', marginLeft: '4px', opacity: 0.8 }}>
                                                        ({stock.change_1d_pct >= 0 ? '+' : ''}{stock.change_1d_pct?.toFixed(2)}%)
                                                    </span>
                                                </>
                                            ) : 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem'
                                        }}>
                                            {(() => {
                                                const rsi = stock.indicators?.RSI;
                                                if (rsi === null || rsi === undefined) {
                                                    return <span style={{ color: '#999' }}>N/A</span>;
                                                }
                                                let rsiColor = '#666';
                                                let rsiLabel = '';
                                                if (rsi > 70) {
                                                    rsiColor = '#e74c3c';
                                                    rsiLabel = 'OB';
                                                } else if (rsi < 30) {
                                                    rsiColor = '#27ae60';
                                                    rsiLabel = 'OS';
                                                }
                                                return (
                                                    <span style={{
                                                        fontWeight: 600,
                                                        color: rsiColor
                                                    }}>
                                                        {rsi.toFixed(1)}
                                                        {rsiLabel && <span style={{ fontSize: '0.7rem', marginLeft: '4px' }}>({rsiLabel})</span>}
                                                    </span>
                                                );
                                            })()}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem',
                                            fontWeight: 500,
                                            color: '#27ae60'
                                        }}>
                                            {volData?.week52_low ? `$${volData.week52_low.toFixed(2)}` : 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem',
                                            fontWeight: 500,
                                            color: '#e74c3c'
                                        }}>
                                            {volData?.week52_high ? `$${volData.week52_high.toFixed(2)}` : 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem'
                                        }}>
                                            {rank !== null && rank !== undefined ? (
                                                <div style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem'
                                                }}>
                                                    <div style={{
                                                        width: '60px',
                                                        height: '6px',
                                                        background: 'rgba(255, 255, 255, 0.1)',
                                                        borderRadius: '3px',
                                                        overflow: 'hidden'
                                                    }}>
                                                        <div style={{
                                                            width: `${rank}%`,
                                                            height: '100%',
                                                            background: rating.color,
                                                            borderRadius: '3px'
                                                        }} />
                                                    </div>
                                                    <span style={{ fontWeight: 500 }}>{rank.toFixed(0)}%</span>
                                                </div>
                                            ) : (
                                                <span style={{ color: 'var(--text-secondary)' }}>N/A</span>
                                            )}
                                        </td>
                                        <td style={{
                                            padding: '0.75rem 1rem'
                                        }}>
                                            <span style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                padding: '0.35rem 0.75rem',
                                                borderRadius: '20px',
                                                fontWeight: 600,
                                                fontSize: '0.8rem',
                                                color: rating.color,
                                                background: `${rating.color}15`,
                                                border: `1px solid ${rating.color}30`
                                            }}>
                                                {rating.icon} {rating.text}
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

function StockAnalysis({ data }) {
    if (data.error) {
        return (
            <div className="stock-grid-item" style={{ borderColor: 'var(--danger)' }}>
                <div className="header-row">
                    <h2 style={{ color: 'var(--danger)', margin: 0 }}>{data.symbol}</h2>
                    <span style={{ color: 'var(--danger)' }}>Error</span>
                </div>
                <p style={{ color: 'var(--text-secondary)' }}>{data.error}</p>
            </div>
        );
    }

    return (
        <div className="stock-grid-item" id={`stock-${data.symbol}`}>
            <div className="header-row">
                <div>
                    <h2 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>{data.symbol}</h2>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Real-time Analysis</div>
                </div>
                <div className="price-display" style={{ margin: 0 }}>${data.price.toFixed(2)}</div>
            </div>

            <div className="dashboard" style={{ gridTemplateColumns: '1fr', gap: '1rem', animation: 'none' }}>
                <Card title="Sentiment">
                    <div className="indicator-row" style={{ border: 'none', padding: 0, marginBottom: 0 }}>
                        <span style={{ fontSize: '1.1rem', fontWeight: 600 }}
                            className={data.sentiment.mood === 'Bullish' ? 'text-bullish' : data.sentiment.mood === 'Bearish' ? 'text-bearish' : 'text-neutral'}>
                            {data.sentiment.mood}
                        </span>
                    </div>
                </Card>

                <VolatilityCard symbol={data.symbol} />

                <CSPMetricsCard symbol={data.symbol} />

                <Card title="Key Indicators">
                    <RSIVisualizer value={data.indicators.RSI} />
                    <BollingerVisualizer
                        price={data.price}
                        upper={data.indicators.BB_Upper}
                        lower={data.indicators.BB_Lower}
                    />
                    <IndicatorRow label="SMA (200)" value={data.indicators.SMA_200} />
                </Card>

                <Card title="3-Year Price History">
                    <PriceChart symbol={data.symbol} />
                </Card>

                <Card title="Summary">
                    <p className="summary-text" style={{ fontSize: '0.9rem' }}>{data.summary}</p>
                </Card>
            </div>
        </div>
    );
}

function VolatilityCard({ symbol }) {
    const [volData, setVolData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        fetch(`/api/volatility/${symbol}`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch volatility data');
                return res.json();
            })
            .then(data => {
                setVolData(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [symbol]);

    if (loading) {
        return (
            <Card title="Volatility Analysis (CSP)">
                <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    Loading volatility data...
                </div>
            </Card>
        );
    }

    if (error || !volData) {
        return (
            <Card title="Volatility Analysis (CSP)">
                <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    Volatility data unavailable
                </div>
            </Card>
        );
    }

    return (
        <Card title="Volatility Analysis (CSP)">
            <IVRankGauge
                ivRank={volData.iv_rank}
                hvRank={volData.hv_rank}
                currentIV={volData.current_iv}
                hv30={volData.hv_30}
                ivHvRatio={volData.iv_hv_ratio}
            />
            <div style={{
                marginTop: '0.75rem',
                padding: '0.75rem',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
                fontSize: '0.85rem',
                lineHeight: '1.4'
            }}>
                {volData.recommendation}
            </div>
        </Card>
    );
}

function IVRankGauge({ ivRank, hvRank, currentIV, hv30, ivHvRatio }) {
    // Use IV Rank if available, otherwise use HV Rank
    const rank = ivRank !== null ? ivRank : hvRank;
    const rankLabel = ivRank !== null ? 'IV Rank' : 'HV Rank';

    if (rank === null) {
        return <div style={{ color: 'var(--text-secondary)' }}>Insufficient data</div>;
    }

    // Color based on rank level
    let gaugeColor = 'var(--text-secondary)';
    let rankLevel = 'Neutral';

    if (rank >= 75) {
        gaugeColor = '#9b59b6'; // Purple - excellent
        rankLevel = 'Very High';
    } else if (rank >= 50) {
        gaugeColor = 'var(--success)'; // Green - good
        rankLevel = 'Above Avg';
    } else if (rank >= 25) {
        gaugeColor = '#f39c12'; // Yellow - moderate
        rankLevel = 'Below Avg';
    } else {
        gaugeColor = 'var(--danger)'; // Red - poor
        rankLevel = 'Low';
    }

    return (
        <div>
            {/* IV Rank Gauge */}
            <div style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{rankLabel}</span>
                    <span style={{ fontWeight: 700, color: gaugeColor }}>{rank.toFixed(0)}% ({rankLevel})</span>
                </div>
                <div style={{
                    height: '10px',
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: '5px',
                    position: 'relative',
                    overflow: 'hidden'
                }}>
                    {/* Background zones */}
                    <div style={{
                        position: 'absolute',
                        left: 0,
                        width: '25%',
                        height: '100%',
                        background: 'rgba(231, 76, 60, 0.2)'
                    }} />
                    <div style={{
                        position: 'absolute',
                        left: '25%',
                        width: '25%',
                        height: '100%',
                        background: 'rgba(243, 156, 18, 0.2)'
                    }} />
                    <div style={{
                        position: 'absolute',
                        left: '50%',
                        width: '25%',
                        height: '100%',
                        background: 'rgba(46, 204, 113, 0.2)'
                    }} />
                    <div style={{
                        position: 'absolute',
                        left: '75%',
                        width: '25%',
                        height: '100%',
                        background: 'rgba(155, 89, 182, 0.2)'
                    }} />
                    {/* Actual gauge fill */}
                    <div style={{
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        width: `${Math.min(rank, 100)}%`,
                        height: '100%',
                        background: gaugeColor,
                        borderRadius: '5px',
                        transition: 'width 0.5s ease'
                    }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                    <span>0</span>
                    <span>25</span>
                    <span>50</span>
                    <span>75</span>
                    <span>100</span>
                </div>
            </div>

            {/* Metrics Row */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.5rem',
                marginTop: '0.5rem'
            }}>
                <div style={{ textAlign: 'center', padding: '0.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>Current IV</div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{currentIV !== null ? `${currentIV}%` : 'N/A'}</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>HV (30d)</div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{hv30 !== null ? `${hv30}%` : 'N/A'}</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>IV/HV</div>
                    <div style={{
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        color: ivHvRatio > 1.2 ? 'var(--success)' : ivHvRatio < 0.8 ? 'var(--danger)' : 'inherit'
                    }}>
                        {ivHvRatio !== null ? ivHvRatio.toFixed(2) : 'N/A'}
                    </div>
                </div>
            </div>
        </div>
    );
}

function CSPMetricsCard({ symbol }) {
    const [cspData, setCspData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        fetch(`/api/csp-metrics/${symbol}`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch CSP metrics');
                return res.json();
            })
            .then(data => {
                setCspData(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [symbol]);

    if (loading) {
        return (
            <Card title="Strike Selection Guide">
                <div style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    Loading CSP metrics...
                </div>
            </Card>
        );
    }

    if (error || !cspData) {
        return (
            <Card title="Strike Selection Guide">
                <div style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    CSP metrics unavailable
                </div>
            </Card>
        );
    }

    return (
        <>
            {/* Earnings Warning - Show separately if warning */}
            {cspData.earnings_warning && (
                <div style={{
                    background: 'linear-gradient(135deg, rgba(231, 76, 60, 0.2), rgba(192, 57, 43, 0.2))',
                    border: '1px solid rgba(231, 76, 60, 0.5)',
                    borderRadius: '12px',
                    padding: '1rem',
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                }}>
                    <span style={{ fontSize: '1.5rem' }}>⚠️</span>
                    <div>
                        <div style={{ fontWeight: 700, color: 'var(--danger)' }}>
                            Earnings in {cspData.days_to_earnings} days
                        </div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            {cspData.next_earnings} - Consider waiting or shorter DTE
                        </div>
                    </div>
                </div>
            )}

            <Card title="Strike Selection Guide">
                {/* 52-Week Range */}
                <Week52RangeGauge
                    currentPrice={cspData.current_price}
                    high={cspData.week52_high}
                    low={cspData.week52_low}
                    position={cspData.price_position}
                />

                {/* ATR-based Strikes */}
                <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        ATR-Based Strikes <span style={{ opacity: 0.6 }}>(ATR: ${cspData.atr_14} | {cspData.atr_percent}%)</span>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {cspData.suggested_strikes && cspData.suggested_strikes.map((strike, idx) => (
                            <div key={idx} style={{
                                background: idx === 0 ? 'rgba(46, 204, 113, 0.15)' : 'rgba(255,255,255,0.05)',
                                border: idx === 0 ? '1px solid rgba(46, 204, 113, 0.3)' : '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '8px',
                                padding: '0.5rem 0.75rem',
                                textAlign: 'center',
                                flex: '1',
                                minWidth: '80px'
                            }}>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                                    {idx + 1} ATR
                                </div>
                                <div style={{ fontWeight: 600, color: idx === 0 ? 'var(--success)' : 'inherit' }}>
                                    ${strike}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Support Levels */}
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        Support Levels
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {cspData.support_levels && cspData.support_levels.map((level, idx) => (
                            <div key={idx} style={{
                                background: 'rgba(52, 152, 219, 0.1)',
                                border: '1px solid rgba(52, 152, 219, 0.3)',
                                borderRadius: '6px',
                                padding: '0.35rem 0.6rem',
                                fontSize: '0.85rem',
                                fontWeight: 500
                            }}>
                                ${level}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Resistance Levels */}
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        Resistance Levels
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {cspData.resistance_levels && cspData.resistance_levels.map((level, idx) => (
                            <div key={idx} style={{
                                background: 'rgba(231, 76, 60, 0.1)',
                                border: '1px solid rgba(231, 76, 60, 0.3)',
                                borderRadius: '6px',
                                padding: '0.35rem 0.6rem',
                                fontSize: '0.85rem',
                                fontWeight: 500
                            }}>
                                ${level}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Earnings Info (non-warning) */}
                {!cspData.earnings_warning && cspData.next_earnings && (
                    <div style={{
                        marginTop: '0.75rem',
                        paddingTop: '0.75rem',
                        borderTop: '1px solid rgba(255,255,255,0.05)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '0.85rem'
                    }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Next Earnings</span>
                        <span>
                            {cspData.next_earnings}
                            <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                                ({cspData.days_to_earnings} days)
                            </span>
                        </span>
                    </div>
                )}
            </Card>
        </>
    );
}

function Week52RangeGauge({ currentPrice, high, low, position }) {
    if (!high || !low) return null;

    const clampedPosition = Math.min(Math.max(position || 50, 0), 100);

    // Color based on position
    let positionColor = 'var(--text-secondary)';
    let positionLabel = 'Mid-Range';

    if (clampedPosition >= 80) {
        positionColor = 'var(--success)';
        positionLabel = 'Near High';
    } else if (clampedPosition >= 60) {
        positionColor = '#3498db';
        positionLabel = 'Upper Range';
    } else if (clampedPosition <= 20) {
        positionColor = 'var(--danger)';
        positionLabel = 'Near Low';
    } else if (clampedPosition <= 40) {
        positionColor = '#f39c12';
        positionLabel = 'Lower Range';
    }

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>52-Week Range</span>
                <span style={{ fontWeight: 600, color: positionColor }}>{clampedPosition.toFixed(0)}% ({positionLabel})</span>
            </div>
            <div style={{
                height: '10px',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: '5px',
                position: 'relative',
                overflow: 'hidden'
            }}>
                {/* Gradient background */}
                <div style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(90deg, rgba(231, 76, 60, 0.3), rgba(243, 156, 18, 0.3), rgba(52, 152, 219, 0.3), rgba(46, 204, 113, 0.3))',
                    borderRadius: '5px'
                }} />
                {/* Price indicator */}
                <div style={{
                    position: 'absolute',
                    left: `${clampedPosition}%`,
                    top: '-2px',
                    transform: 'translateX(-50%)',
                    width: '4px',
                    height: '14px',
                    background: '#fff',
                    borderRadius: '2px',
                    boxShadow: '0 0 4px rgba(0,0,0,0.5)'
                }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>${low}</span>
                <span style={{ fontWeight: 600 }}>${currentPrice}</span>
                <span style={{ color: 'var(--text-secondary)' }}>${high}</span>
            </div>
        </div>
    );
}


// Recharts components from global
const { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } = Recharts;

function PriceChart({ symbol }) {
    const chartContainerRef = React.useRef(null);
    const chartRef = React.useRef(null);
    const seriesRef = React.useRef(null);
    const bbUpperRef = React.useRef(null);
    const bbMiddleRef = React.useRef(null);
    const bbLowerRef = React.useRef(null);
    const [period, setPeriod] = useState('3y');
    const [chartType, setChartType] = useState('area'); // 'area' or 'candlestick'
    const [showBB, setShowBB] = useState(false); // Show Bollinger Bands
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const periods = [
        { label: '1W', value: '5d' },
        { label: '1M', value: '1mo' },
        { label: '3M', value: '3mo' },
        { label: '6M', value: '6mo' },
        { label: '1Y', value: '1y' },
        { label: '3Y', value: '3y' },
        { label: '5Y', value: '5y' },
    ];

    useEffect(() => {
        if (!chartContainerRef.current) return;

        // Create chart
        const chart = LightweightCharts.createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: 300,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#9ca3af',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
            handleScroll: {
                vertTouchDrag: false,
            },
        });

        chartRef.current = chart;

        // Handle resize
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    useEffect(() => {
        if (!chartRef.current) return;

        setLoading(true);
        setError(null);

        fetch(`/api/history/${symbol}?period=${period}`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch history');
                return res.json();
            })
            .then(data => {
                if (!data.history || data.history.length === 0) {
                    throw new Error('No data');
                }

                // Remove old series
                if (seriesRef.current) {
                    chartRef.current.removeSeries(seriesRef.current);
                }
                // Remove old BB series
                if (bbUpperRef.current) {
                    chartRef.current.removeSeries(bbUpperRef.current);
                    bbUpperRef.current = null;
                }
                if (bbMiddleRef.current) {
                    chartRef.current.removeSeries(bbMiddleRef.current);
                    bbMiddleRef.current = null;
                }
                if (bbLowerRef.current) {
                    chartRef.current.removeSeries(bbLowerRef.current);
                    bbLowerRef.current = null;
                }

                // Calculate if up or down
                const firstPrice = data.history[0]?.close || 0;
                const lastPrice = data.history[data.history.length - 1]?.close || 0;
                const isUp = lastPrice >= firstPrice;

                if (chartType === 'candlestick') {
                    // Candlestick chart
                    const candlestickSeries = chartRef.current.addCandlestickSeries({
                        upColor: '#26a69a',
                        downColor: '#ef5350',
                        borderVisible: false,
                        wickUpColor: '#26a69a',
                        wickDownColor: '#ef5350',
                    });

                    const candleData = data.history.map(item => ({
                        time: item.date,
                        open: item.open,
                        high: item.high,
                        low: item.low,
                        close: item.close,
                    }));

                    candlestickSeries.setData(candleData);
                    seriesRef.current = candlestickSeries;
                } else {
                    // Area chart
                    const areaSeries = chartRef.current.addAreaSeries({
                        lineColor: isUp ? '#26a69a' : '#ef5350',
                        topColor: isUp ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
                        bottomColor: isUp ? 'rgba(38, 166, 154, 0.0)' : 'rgba(239, 83, 80, 0.0)',
                        lineWidth: 2,
                    });

                    const areaData = data.history.map(item => ({
                        time: item.date,
                        value: item.close,
                    }));

                    areaSeries.setData(areaData);
                    seriesRef.current = areaSeries;
                }

                // Add Bollinger Bands if enabled
                if (showBB) {
                    const bbDataWithValues = data.history.filter(item =>
                        item.bb_upper !== null && item.bb_middle !== null && item.bb_lower !== null
                    );

                    if (bbDataWithValues.length > 0) {
                        // Upper band (red/orange)
                        const upperSeries = chartRef.current.addLineSeries({
                            color: 'rgba(239, 83, 80, 0.6)',
                            lineWidth: 1,
                            lineStyle: 2, // dashed
                        });
                        upperSeries.setData(bbDataWithValues.map(item => ({
                            time: item.date,
                            value: item.bb_upper,
                        })));
                        bbUpperRef.current = upperSeries;

                        // Middle band (SMA - yellow)
                        const middleSeries = chartRef.current.addLineSeries({
                            color: 'rgba(255, 193, 7, 0.8)',
                            lineWidth: 1,
                        });
                        middleSeries.setData(bbDataWithValues.map(item => ({
                            time: item.date,
                            value: item.bb_middle,
                        })));
                        bbMiddleRef.current = middleSeries;

                        // Lower band (green)
                        const lowerSeries = chartRef.current.addLineSeries({
                            color: 'rgba(38, 166, 154, 0.6)',
                            lineWidth: 1,
                            lineStyle: 2, // dashed
                        });
                        lowerSeries.setData(bbDataWithValues.map(item => ({
                            time: item.date,
                            value: item.bb_lower,
                        })));
                        bbLowerRef.current = lowerSeries;
                    }
                }

                chartRef.current.timeScale().fitContent();
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [symbol, period, chartType, showBB]);

    return (
        <div>
            {/* Controls */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.75rem',
                flexWrap: 'wrap',
                gap: '0.5rem'
            }}>
                {/* Timeline buttons */}
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                    {periods.map(p => (
                        <button
                            key={p.value}
                            onClick={() => setPeriod(p.value)}
                            style={{
                                padding: '0.3rem 0.6rem',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                border: 'none',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                background: period === p.value
                                    ? 'linear-gradient(135deg, #667eea, #764ba2)'
                                    : 'rgba(255, 255, 255, 0.05)',
                                color: period === p.value ? '#fff' : 'var(--text-secondary)',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            {p.label}
                        </button>
                    ))}
                </div>

                {/* Chart type toggle */}
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button
                        onClick={() => setChartType('area')}
                        style={{
                            padding: '0.3rem 0.6rem',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            background: chartType === 'area'
                                ? 'rgba(38, 166, 154, 0.2)'
                                : 'rgba(255, 255, 255, 0.05)',
                            color: chartType === 'area' ? '#26a69a' : 'var(--text-secondary)',
                        }}
                    >
                        📈 Area
                    </button>
                    <button
                        onClick={() => setChartType('candlestick')}
                        style={{
                            padding: '0.3rem 0.6rem',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            background: chartType === 'candlestick'
                                ? 'rgba(38, 166, 154, 0.2)'
                                : 'rgba(255, 255, 255, 0.05)',
                            color: chartType === 'candlestick' ? '#26a69a' : 'var(--text-secondary)',
                        }}
                    >
                        🕯️ Candles
                    </button>
                    <button
                        onClick={() => setShowBB(!showBB)}
                        style={{
                            padding: '0.3rem 0.6rem',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            background: showBB
                                ? 'rgba(255, 193, 7, 0.2)'
                                : 'rgba(255, 255, 255, 0.05)',
                            color: showBB ? '#ffc107' : 'var(--text-secondary)',
                        }}
                    >
                        📊 BB
                    </button>
                </div>
            </div>

            {/* Chart container */}
            <div style={{ position: 'relative' }}>
                <div
                    ref={chartContainerRef}
                    style={{
                        width: '100%',
                        height: '300px',
                        borderRadius: '8px',
                        overflow: 'hidden'
                    }}
                />
                {loading && (
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(0,0,0,0.5)',
                        color: 'var(--text-secondary)',
                        borderRadius: '8px'
                    }}>
                        Loading chart...
                    </div>
                )}
                {error && (
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(0,0,0,0.5)',
                        color: 'var(--danger)',
                        borderRadius: '8px'
                    }}>
                        Chart unavailable
                    </div>
                )}
            </div>

            {/* Instructions */}
            <div style={{
                marginTop: '0.5rem',
                fontSize: '0.7rem',
                color: 'var(--text-secondary)',
                textAlign: 'center'
            }}>
                🖱️ Scroll to zoom • Drag to pan • Double-click to reset
            </div>
        </div>
    );
}

function BollingerVisualizer({ price, upper, lower }) {
    if (!upper || !lower || upper === lower) return null;

    // Calculate percentage position (0% = lower, 100% = upper)
    let percent = ((price - lower) / (upper - lower)) * 100;
    percent = Math.min(Math.max(percent, 0), 100); // Clamp 0-100

    let statusText = "Neutral";
    let barColor = "var(--text-secondary)";

    if (percent > 80) {
        statusText = "Near Upper Band";
        barColor = "var(--success)";
    } else if (percent < 20) {
        statusText = "Near Lower Band";
        barColor = "var(--danger)";
    }

    return (
        <div style={{ marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span className="indicator-label">BB Position</span>
                <span className="indicator-value" style={{ color: barColor, fontSize: '0.9rem' }}>{statusText}</span>
            </div>
            <div style={{
                height: '8px',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: '4px',
                position: 'relative',
                overflow: 'hidden'
            }}>
                <div style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    width: `${percent}%`,
                    height: '100%',
                    background: barColor,
                    borderRadius: '4px',
                    transition: 'width 0.5s ease, background 0.3s ease'
                }}></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span>{lower.toFixed(2)}</span>
                <span>{upper.toFixed(2)}</span>
            </div>
        </div>
    );
}

function RSIVisualizer({ value }) {
    // Clamp value 0-100
    let percent = Math.min(Math.max(value, 0), 100);

    let statusText = "Neutral";
    let barColor = "var(--text-secondary)";

    if (value > 70) {
        statusText = "Overbought";
        barColor = "var(--success)";
    } else if (value < 35) {
        statusText = "Oversold";
        barColor = "var(--danger)";
    }

    return (
        <div style={{ marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span className="indicator-label">RSI (14)</span>
                <span className="indicator-value" style={{ color: barColor, fontSize: '0.9rem' }}>{value} ({statusText})</span>
            </div>
            <div style={{
                height: '8px',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: '4px',
                position: 'relative',
                overflow: 'hidden'
            }}>
                <div style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    width: `${percent}%`,
                    height: '100%',
                    background: barColor,
                    borderRadius: '4px',
                    transition: 'width 0.5s ease, background 0.3s ease'
                }}></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span>0</span>
                <span>100</span>
            </div>
        </div>
    );
}




function Card({ title, children, style }) {
    return (
        <div className="card" style={style}>
            <div className="card-header">
                <div className="card-title">{title}</div>
            </div>
            <div className="card-content">
                {children}
            </div>
        </div>
    );
}

function IndicatorRow({ label, value, warning }) {
    return (
        <div className="indicator-row">
            <span className="indicator-label">{label}</span>
            <span className="indicator-value" style={warning ? { color: 'var(--danger)', fontWeight: '700' } : {}}>{value}</span>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
