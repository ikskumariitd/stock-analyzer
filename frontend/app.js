const { useState, useEffect } = React;

// ============================================
// Cache Control Component
// ============================================
function CacheControl() {
    const [clearing, setClearing] = useState(false);
    const [stats, setStats] = useState(null);
    const [showDetails, setShowDetails] = useState(false);

    const fetchStats = async () => {
        try {
            const res = await fetch('/api/cache/stats');
            if (res.ok) {
                const data = await res.json();
                setStats(data);
            }
        } catch (e) {
            console.error('Failed to fetch cache stats:', e);
        }
    };

    const clearCache = async () => {
        setClearing(true);
        try {
            const res = await fetch('/api/cache/clear', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                // Show success message
                alert(`✅ Cache cleared!\n\n${data.cleared_entries} entries removed.\nFresh data will be fetched on next load.`);
                fetchStats(); // Refresh stats
            }
        } catch (e) {
            alert('❌ Failed to clear cache. Please try again.');
            console.error('Cache clear error:', e);
        } finally {
            setClearing(false);
        }
    };

    useEffect(() => {
        fetchStats();
        // Refresh stats every 30 seconds
        const interval = setInterval(fetchStats, 30000);
        return () => clearInterval(interval);
    }, []);

    const buttonStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '8px 16px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        border: 'none',
        borderRadius: '8px',
        color: 'white',
        fontSize: '0.85rem',
        fontWeight: '600',
        cursor: clearing ? 'wait' : 'pointer',
        opacity: clearing ? 0.7 : 1,
        transition: 'all 0.2s ease',
        boxShadow: '0 2px 8px rgba(102, 126, 234, 0.3)'
    };

    const statsStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 12px',
        background: 'rgba(102, 126, 234, 0.1)',
        borderRadius: '8px',
        fontSize: '0.8rem',
        color: '#667eea',
        fontWeight: 500
    };

    const containerStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        flexWrap: 'wrap'
    };

    return (
        <div style={containerStyle}>
            {stats && stats.valid_entries > 0 && (
                <div style={statsStyle} title={`TTL: ${stats.ttl_hours} hour(s)\nOldest: ${stats.oldest_age_minutes} min`}>
                    <span style={{ fontSize: '1rem' }}>📦</span>
                    <span>{stats.valid_entries} cached</span>
                    {stats.oldest_age_minutes > 0 && (
                        <span style={{ color: '#999', fontSize: '0.75rem' }}>
                            ({stats.oldest_age_minutes}m ago)
                        </span>
                    )}
                </div>
            )}
            <button
                onClick={clearCache}
                disabled={clearing}
                style={buttonStyle}
                title="Clear all cached data to fetch fresh stock information"
            >
                {clearing ? (
                    <>
                        <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
                        <span>Clearing...</span>
                    </>
                ) : (
                    <>
                        <span>🗑️</span>
                        <span>Clear Cache</span>
                    </>
                )}
            </button>
        </div>
    );
}

// ============================================
// Request Queue for Concurrency Limiting
// ============================================
class RequestQueue {
    constructor(concurrency = 3) {
        this.concurrency = concurrency;
        this.running = 0;
        this.queue = [];
    }

    add(fn) {
        return new Promise((resolve, reject) => {
            this.queue.push({ fn, resolve, reject });
            this.processNext();
        });
    }

    async processNext() {
        if (this.running >= this.concurrency || this.queue.length === 0) return;

        this.running++;
        const { fn, resolve, reject } = this.queue.shift();

        try {
            const result = await fn();
            resolve(result);
        } catch (err) {
            reject(err);
        } finally {
            this.running--;
            this.processNext();
        }
    }
}

// Create a global queue instance limiting to 3 concurrent requests
const apiQueue = new RequestQueue(3);

function SP100Page({ data = [], setData }) {
    const [stocks, setStocks] = useState(data); // Initialize with passed data
    const [loading, setLoading] = useState(data.length === 0); // Only load if no data
    const [filter, setFilter] = useState("");
    const [sortConfig, setSortConfig] = useState({ key: 'market_cap', direction: 'desc' });

    // Sync internal state with props when props change (e.g. if parent updates it)
    useEffect(() => {
        setStocks(data);
    }, [data]);

    useEffect(() => {
        // Only fetch if we don't have data
        if (data.length > 0) {
            setLoading(false);
            return;
        }

        setLoading(true);
        fetch('/api/sp100')
            .then(res => res.json())
            .then(fetchedData => {
                setStocks(fetchedData);
                if (setData) setData(fetchedData); // Persist up to App
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch S&P 100 data", err);
                setLoading(false);
            });
    }, []); // Empty dependency array means this runs on mount. The check inside handles the logic.

    const handleRefresh = () => {
        if (loading) return;
        setLoading(true);
        fetch('/api/sp100?refresh=true')
            .then(res => res.json())
            .then(fetchedData => {
                setStocks(fetchedData);
                if (setData) setData(fetchedData); // Persist up to App
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch S&P 100 data", err);
                setLoading(false);
            });
    };

    const handleSort = (key) => {
        let direction = 'desc';
        if (sortConfig.key === key && sortConfig.direction === 'desc') {
            direction = 'asc';
        }
        setSortConfig({ key, direction });
    };

    const sortedStocks = React.useMemo(() => {
        let sortable = [...stocks];
        if (filter) {
            const lowerFilter = filter.toLowerCase();
            sortable = sortable.filter(s =>
                s.symbol.toLowerCase().includes(lowerFilter)
            );
        }

        const getValue = (obj, path) => {
            return path.split('.').reduce((o, i) => (o ? o[i] : null), obj);
        };

        if (sortConfig.key) {
            sortable.sort((a, b) => {
                const valA = getValue(a, sortConfig.key);
                const valB = getValue(b, sortConfig.key);

                if (valA < valB) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (valA > valB) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortable;
    }, [stocks, filter, sortConfig]);

    const formatMarketCap = (num) => {
        if (!num) return "-";
        if (num >= 1e12) return (num / 1e12).toFixed(2) + "T";
        if (num >= 1e9) return (num / 1e9).toFixed(2) + "B";
        if (num >= 1e6) return (num / 1e6).toFixed(2) + "M";
        return num.toLocaleString();
    };

    return (
        <div className="sp100-container">
            <h2 style={{ marginBottom: '1rem' }}>🏆 S&P 100 Components</h2>

            <div className="sp100-controls">
                <input
                    type="text"
                    placeholder="Filter by symbol..."
                    className="sp100-search"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                />
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    style={{
                        padding: '8px 16px',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        border: 'none',
                        borderRadius: '8px',
                        color: 'white',
                        fontWeight: '600',
                        cursor: loading ? 'wait' : 'pointer',
                        opacity: loading ? 0.7 : 1,
                        marginLeft: '10px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }}
                >
                    {loading ? (
                        <>
                            <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
                            Refreshing...
                        </>
                    ) : (
                        <>
                            <span>🔄</span>
                            Refresh Data
                        </>
                    )}
                </button>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>Loading Market Data...</div>
            ) : (
                <div className="sp100-table-wrapper">
                    <table className="sp100-table">
                        <thead>
                            <tr>
                                <th onClick={() => handleSort('symbol')}>
                                    Symbol {sortConfig.key === 'symbol' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                                <th onClick={() => handleSort('name')}>
                                    Company {sortConfig.key === 'name' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                                <th onClick={() => handleSort('price')}>
                                    Price {sortConfig.key === 'price' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                                <th onClick={() => handleSort('change_1d_pct')}>
                                    Change % {sortConfig.key === 'change_1d_pct' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                                <th onClick={() => handleSort('market_cap')}>
                                    Market Cap {sortConfig.key === 'market_cap' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                                <th onClick={() => handleSort('indicators.RSI')}>
                                    RSI {sortConfig.key === 'indicators.RSI' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                                <th onClick={() => handleSort('sentiment.mood')}>
                                    Sentiment {sortConfig.key === 'sentiment.mood' && (sortConfig.direction === 'asc' ? '▲' : '▼')}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedStocks.map(stock => (
                                <tr key={stock.symbol}>
                                    <td style={{ fontWeight: 'bold' }}>{stock.symbol}</td>
                                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{stock.name || '-'}</td>
                                    <td>${stock.price}</td>
                                    <td className={stock.change_1d_pct >= 0 ? 'positive-change' : 'negative-change'}>
                                        {stock.change_1d_pct > 0 ? '+' : ''}{stock.change_1d_pct}%
                                    </td>
                                    <td>{formatMarketCap(stock.market_cap)}</td>
                                    <td>{stock.indicators?.RSI || '-'}</td>
                                    <td>{stock.sentiment?.mood || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

function App() {
    const [currentView, setCurrentView] = useState('home');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [addingStock, setAddingStock] = useState(false);
    const [loadingStock, setLoadingStock] = useState(null);
    const [watchlistVersion, setWatchlistVersion] = useState(0);
    const [watchlist, setWatchlist] = useState([]);

    // Persistent Data States (Lifted up to prevent refetching on navigation)
    const [sp100Data, setSp100Data] = useState([]);
    const [cspData, setCspData] = useState({}); // Cache for CSP Summary Table

    // Fetch watchlist from API
    const fetchWatchlist = () => {
        fetch('/api/watchlist')
            .then(res => res.json())
            .then(data => {
                setWatchlist(data.watchlist || []);
            })
            .catch(() => {
                // Fallback to static config
                fetch('/static/config.json')
                    .then(res => res.json())
                    .then(config => {
                        setWatchlist(config.defaultWatchlist || []);
                    })
                    .catch(() => {
                        setWatchlist(['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'AMZN']);
                    });
            });
    };

    // Fetch watchlist on mount
    useEffect(() => {
        fetchWatchlist();
    }, []);

    // Re-fetch watchlist when version changes
    useEffect(() => {
        if (watchlistVersion > 0) {
            fetchWatchlist();
        }
    }, [watchlistVersion]);

    // Called when a stock is added to watchlist (from Search component)
    const handleWatchlistChange = () => {
        setWatchlistVersion(v => v + 1);
    };

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

    const handleAddStock = async (symbol) => {
        // Check if stock already exists in data
        if (data && Array.isArray(data)) {
            const exists = data.some(s => s.symbol === symbol);
            if (exists) {
                // Stock already in list, just scroll to it
                const element = document.getElementById(`stock-${symbol}`);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
                return;
            }
        }

        setAddingStock(true);
        setLoadingStock(symbol);
        try {
            const response = await fetch('/api/analyze-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers: [symbol] })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch stock data');
            }

            const newStockData = await response.json();

            if (newStockData && newStockData.length > 0) {
                // Prepend new stock to existing data
                setData(prevData => {
                    if (prevData && Array.isArray(prevData)) {
                        return [newStockData[0], ...prevData];
                    }
                    return newStockData;
                });
            }
        } catch (err) {
            console.error('Error adding stock:', err);
        } finally {
            setAddingStock(false);
            setLoadingStock(null);
        }
    };

    // Remove a stock from results
    const handleRemoveStock = (symbol) => {
        setData(prevData => {
            if (prevData && Array.isArray(prevData)) {
                return prevData.filter(s => s.symbol !== symbol);
            }
            return prevData;
        });
    };

    // Analyze all stocks from a list (for "Analyze All" button)
    const handleAnalyzeAll = async (tickers) => {
        if (!tickers || tickers.length === 0) return;

        // Filter out already analyzed stocks
        const existingSymbols = data && Array.isArray(data) ? data.map(s => s.symbol) : [];
        const newTickers = tickers.filter(t => !existingSymbols.includes(t));

        if (newTickers.length === 0) return;

        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/analyze-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers: newTickers })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch stock data');
            }

            const newStockData = await response.json();

            if (newStockData && newStockData.length > 0) {
                setData(prevData => {
                    if (prevData && Array.isArray(prevData)) {
                        return [...newStockData, ...prevData];
                    }
                    return newStockData;
                });
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Refresh a single stock's data (force fresh fetch)
    const handleRefreshStock = async (symbol) => {
        setLoadingStock(symbol);
        try {
            const response = await fetch('/api/analyze-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers: [symbol], refresh: true })
            });

            if (!response.ok) {
                throw new Error('Failed to refresh stock data');
            }

            const newStockData = await response.json();

            if (newStockData && newStockData.length > 0) {
                // Replace the old stock data with fresh data
                setData(prevData => {
                    if (prevData && Array.isArray(prevData)) {
                        return prevData.map(s =>
                            s.symbol === symbol ? { ...newStockData[0], _lastRefreshed: Date.now() } : s
                        );
                    }
                    return newStockData;
                });
            }
        } catch (err) {
            console.error('Error refreshing stock:', err);
        } finally {
            setLoadingStock(null);
        }
    };

    // Get list of analyzed stock symbols for display
    const analyzedStocks = data && Array.isArray(data)
        ? data.filter(s => !s.error).map(s => s.symbol)
        : [];

    // Clear all analyzed stocks
    const handleClearAnalysis = () => {
        if (data && confirm('Are you sure you want to clear all analyzed stocks?')) {
            setData(null);
            setError(null);
        }
    };

    return (
        <div className="container">
            <header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h1>Stock Analyzer Pro</h1>
                    <p>Professional Technical Analysis & Sentiment</p>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <button
                        className={`nav-button ${currentView === 'home' ? 'active' : ''}`}
                        onClick={() => setCurrentView('home')}
                    >
                        🏠 Dashboard
                    </button>
                    <button
                        className={`nav-button ${currentView === 'sp100' ? 'active' : ''}`}
                        onClick={() => setCurrentView('sp100')}
                    >
                        🏆 S&P 100
                    </button>
                    <CacheControl />
                </div>
            </header>

            {currentView === 'home' ? (
                <>
                    <WatchlistTags
                        onAddStock={handleAddStock}
                        onAnalyzeAll={handleAnalyzeAll}
                        analyzedStocks={analyzedStocks}
                        disabled={loading || addingStock}
                        loadingStock={loadingStock}
                        refreshTrigger={watchlistVersion}
                    />

                    <Search
                        onSearch={handleSearch}
                        onAddStock={handleAddStock}
                        onRemoveStock={handleRemoveStock}
                        onWatchlistChange={handleWatchlistChange}
                        onClearAnalysis={handleClearAnalysis}
                        disabled={loading}
                        addingStock={addingStock}
                        analyzedStocks={analyzedStocks}
                        watchlist={watchlist}
                    />

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

                    {data && (
                        <Dashboard
                            data={data}
                            onRefreshStock={handleRefreshStock}
                            refreshingStock={loadingStock}
                            cspData={cspData}
                            setCspData={setCspData}
                        />
                    )}
                </>
            ) : (
                <SP100Page
                    data={sp100Data}
                    setData={setSp100Data}
                />
            )}
        </div>
    );
}



// Watchlist tags shown above search - click to add stock to analysis
// Hover over tag to show minus sign for removal from watchlist
function WatchlistTags({ onAddStock, onAnalyzeAll, analyzedStocks = [], disabled, loadingStock, refreshTrigger }) {
    const [watchlist, setWatchlist] = useState([]);
    const [hoveredStock, setHoveredStock] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isWritable, setIsWritable] = useState(false);
    const [removingSymbol, setRemovingSymbol] = useState(null);

    const fetchWatchlist = () => {
        fetch('/api/watchlist')
            .then(res => res.json())
            .then(data => {
                setWatchlist(data.watchlist || []);
                setIsWritable(data.is_writable || false);
                setLoading(false);
            })
            .catch(() => {
                // Fallback to static config
                fetch('/static/config.json')
                    .then(res => res.json())
                    .then(config => {
                        setWatchlist(config.defaultWatchlist || []);
                        setLoading(false);
                    })
                    .catch(() => {
                        setWatchlist(['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'AMZN']);
                        setLoading(false);
                    });
            });
    };

    useEffect(() => {
        fetchWatchlist();
    }, []);

    // Re-fetch when refreshTrigger changes (happens when stock added from search)
    useEffect(() => {
        if (refreshTrigger > 0) {
            fetchWatchlist();
        }
    }, [refreshTrigger]);



    const handleRemoveFromWatchlist = async (symbol) => {
        setRemovingSymbol(symbol);
        try {
            const res = await fetch(`/api/watchlist/${symbol}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                setWatchlist(data.watchlist);
            }
        } catch (err) {
            console.error('Failed to remove from watchlist:', err);
        } finally {
            setRemovingSymbol(null);
        }
    };

    const handleClearWatchlist = async () => {
        if (!confirm('Are you sure you want to remove all stocks from your watchlist?')) return;

        try {
            const res = await fetch('/api/watchlist', { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                setWatchlist([]);
            }
        } catch (err) {
            console.error('Failed to clear watchlist:', err);
        }
    };

    if (loading) {
        return null;
    }

    return (
        <div style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05))',
            borderRadius: '12px',
            border: '1px solid rgba(102, 126, 234, 0.1)'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    flex: 1
                }}>
                    <span style={{
                        fontSize: '0.8rem',
                        color: 'var(--text-secondary)',
                        marginRight: '0.25rem',
                        fontWeight: 500
                    }}>
                        📋 Watchlist:
                    </span>
                    {/* Analyze All button - show when there are unanalyzed stocks */}
                    {(() => {
                        const unanalyzedCount = watchlist.filter(s => !analyzedStocks.includes(s)).length;
                        if (unanalyzedCount > 0 && onAnalyzeAll && !disabled) {
                            return (
                                <>
                                    <button
                                        onClick={() => onAnalyzeAll(watchlist)}
                                        style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            padding: '0.2rem 0.6rem',
                                            background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                            borderRadius: '16px',
                                            fontSize: '0.75rem',
                                            fontWeight: 600,
                                            color: 'white',
                                            border: 'none',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s ease',
                                            boxShadow: '0 2px 6px rgba(102, 126, 234, 0.3)'
                                        }}
                                        title={`Analyze all ${unanalyzedCount} unanalyzed stocks`}
                                    >
                                        🚀 Analyze All ({unanalyzedCount})
                                    </button>
                                </>
                            );
                        }
                        return null;
                    })()}

                    {/* Remove All button - show when there are items in watchlist */}
                    {watchlist.length > 0 && !disabled && (
                        <button
                            onClick={handleClearWatchlist}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.2rem 0.6rem',
                                background: 'rgba(239, 83, 80, 0.1)',
                                borderRadius: '16px',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                color: '#ef5350',
                                border: '1px solid rgba(239, 83, 80, 0.2)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease'
                            }}
                            title="Remove all stocks from watchlist"
                        >
                            🗑️ Remove All
                        </button>
                    )}
                    {watchlist.map(symbol => {
                        const isAnalyzed = analyzedStocks.includes(symbol);
                        const isHovered = hoveredStock === symbol;
                        const isLoading = loadingStock === symbol;
                        const isRemoving = removingSymbol === symbol;

                        return (
                            <span
                                key={symbol}
                                onMouseEnter={() => setHoveredStock(symbol)}
                                onMouseLeave={() => setHoveredStock(null)}
                                onClick={() => {
                                    // Clicking on the tag itself adds to analysis (if not already analyzed)
                                    if (isRemoving || isLoading) return;
                                    if (!isAnalyzed && !disabled && onAddStock) {
                                        onAddStock(symbol);
                                    }
                                }}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    padding: '0.2rem 0.6rem',
                                    background: isRemoving
                                        ? 'linear-gradient(135deg, rgba(231, 76, 60, 0.2), rgba(192, 57, 43, 0.2))'
                                        : isLoading
                                            ? 'linear-gradient(135deg, rgba(243, 156, 18, 0.2), rgba(241, 196, 15, 0.2))'
                                            : isAnalyzed
                                                ? 'rgba(0, 0, 0, 0.05)'
                                                : 'white',
                                    borderRadius: '16px',
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    color: isRemoving
                                        ? '#e74c3c'
                                        : isLoading
                                            ? '#f39c12'
                                            : isAnalyzed
                                                ? '#999'
                                                : '#667eea',
                                    border: isRemoving
                                        ? '1px solid rgba(231, 76, 60, 0.3)'
                                        : isLoading
                                            ? '1px solid rgba(243, 156, 18, 0.3)'
                                            : isAnalyzed
                                                ? '1px solid rgba(0, 0, 0, 0.1)'
                                                : '1px solid rgba(102, 126, 234, 0.2)',
                                    cursor: isAnalyzed || isLoading ? 'default' : 'pointer',
                                    transition: 'all 0.2s ease',
                                    opacity: isAnalyzed ? 0.6 : 1
                                }}
                            >
                                {symbol}
                                {isRemoving && (
                                    <span style={{ fontSize: '0.7rem', animation: 'spin 1s linear infinite' }}>⏳</span>
                                )}
                                {isLoading && (
                                    <span style={{ fontSize: '0.7rem', animation: 'spin 1s linear infinite' }}>⏳</span>
                                )}
                                {/* Minus button - click to remove from watchlist */}
                                {!isRemoving && !isLoading && isHovered && isWritable && !isAnalyzed && (
                                    <span
                                        onClick={(e) => {
                                            e.stopPropagation(); // Prevent triggering parent click
                                            handleRemoveFromWatchlist(symbol);
                                        }}
                                        style={{
                                            fontSize: '0.75rem',
                                            fontWeight: 700,
                                            color: '#e74c3c',
                                            cursor: 'pointer',
                                            padding: '0 2px',
                                            marginLeft: '2px'
                                        }}
                                        title="Remove from watchlist"
                                    >−</span>
                                )}
                                {isAnalyzed && (
                                    <span style={{ fontSize: '0.65rem' }}>✓</span>
                                )}
                            </span>
                        );
                    })}
                </div>
            </div>
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

function Search({ onSearch, onAddStock, onRemoveStock, onWatchlistChange, onClearAnalysis, disabled, addingStock, analyzedStocks = [], watchlist = [] }) {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(true);
    const [searchResults, setSearchResults] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [searchLoading, setSearchLoading] = useState(false);
    const [hoveredStock, setHoveredStock] = useState(null);
    const debounceRef = React.useRef(null);
    const inputRef = React.useRef(null);

    // No longer auto-populate - watchlist is shown as clickable tags above
    useEffect(() => {
        setLoading(false);
    }, []);


    // Get the current word being typed (after the last comma)
    const getCurrentWord = (text) => {
        const parts = text.split(',');
        return parts[parts.length - 1].trim().toUpperCase();
    };

    // Search for stocks as user types
    const searchStocks = async (query) => {
        if (query.length < 1) {
            setSearchResults([]);
            setShowDropdown(false);
            return;
        }

        setSearchLoading(true);
        try {
            const res = await fetch(`/api/search-stocks/${encodeURIComponent(query)}`);
            if (res.ok) {
                const data = await res.json();
                setSearchResults(data.results || []);
                setShowDropdown(data.results && data.results.length > 0);
            }
        } catch (e) {
            console.error('Search error:', e);
            setSearchResults([]);
        } finally {
            setSearchLoading(false);
        }
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        setInput(value);

        // Get the current word being typed
        const currentWord = getCurrentWord(value);

        // Debounce search calls
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }
        debounceRef.current = setTimeout(() => {
            if (currentWord.length >= 1) {
                searchStocks(currentWord);
            } else {
                setSearchResults([]);
                setShowDropdown(false);
            }
        }, 250);
    };

    const handleSelect = async (stock) => {
        // Clear dropdown and the partial text typed
        setSearchResults([]);
        setShowDropdown(false);

        // Remove the partial word that was being typed
        const parts = input.split(',').map(s => s.trim()).filter(s => s.length > 0);
        if (parts.length > 0) {
            const lastWord = parts[parts.length - 1].toUpperCase();
            // If the last word looks like a partial match being typed, remove it
            if (stock.symbol.startsWith(lastWord) || lastWord.length < 4) {
                parts.pop();
                setInput(parts.length > 0 ? parts.join(', ') + ', ' : '');
            }
        }

        // Auto-add to watchlist and refresh watchlist display
        fetch(`/api/watchlist/${stock.symbol}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success && onWatchlistChange) {
                    onWatchlistChange();
                }
            })
            .catch(err => console.log('Watchlist add (optional):', err));

        // Immediately fetch and display the stock
        if (onAddStock) {
            onAddStock(stock.symbol);
        }

        // Focus back on input
        if (inputRef.current) {
            inputRef.current.focus();
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setShowDropdown(false);
        // Get tickers from input
        const inputTickers = input.trim()
            ? input.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0)
            : [];

        // Add new tickers to watchlist
        const newTickers = inputTickers.filter(t => !watchlist.includes(t));
        if (newTickers.length > 0) {
            try {
                // Add to backend in parallel
                await Promise.all(newTickers.map(t =>
                    fetch(`/api/watchlist/${t}`, { method: 'POST' })
                ));
                // Refresh watchlist UI
                if (onWatchlistChange) {
                    onWatchlistChange();
                }
            } catch (err) {
                console.error("Failed to auto-add to watchlist:", err);
            }
        }

        // Merge with watchlist, removing duplicates
        const allTickers = [...new Set([...inputTickers, ...watchlist])];
        if (allTickers.length > 0) {
            onSearch(allTickers.join(', '));
            setInput(''); // Clear input after search
        }
    };

    const handleBlur = () => {
        // Delay hiding dropdown to allow click on results
        setTimeout(() => setShowDropdown(false), 200);
    };

    const handleFocus = () => {
        const currentWord = getCurrentWord(input);
        if (currentWord.length >= 1 && searchResults.length > 0) {
            setShowDropdown(true);
        }
    };

    return (
        <div className="search-container">
            <form className="search-box" onSubmit={handleSubmit} style={{ position: 'relative' }}>
                <input
                    ref={inputRef}
                    type="text"
                    className="search-input"
                    placeholder={loading ? "Loading watchlist..." : "Type to search stocks (e.g., AAPL, NVDA)..."}
                    value={input}
                    onChange={handleInputChange}
                    onBlur={handleBlur}
                    onFocus={handleFocus}
                    disabled={disabled || loading}
                    autoComplete="off"
                />
                {searchLoading && (
                    <span style={{
                        position: 'absolute',
                        right: '140px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        fontSize: '0.8rem',
                        color: '#667eea'
                    }}>⏳</span>
                )}
                <button type="submit" className="search-button" disabled={disabled || loading}>
                    {disabled ? '...' : 'ANALYZE'}
                </button>

                {showDropdown && searchResults.length > 0 && (
                    <div style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        marginTop: '4px',
                        background: 'white',
                        borderRadius: '12px',
                        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
                        border: '1px solid rgba(0, 0, 0, 0.1)',
                        zIndex: 1000,
                        maxHeight: '300px',
                        overflowY: 'auto'
                    }}>
                        {searchResults.map((stock, idx) => (
                            <div
                                key={stock.symbol}
                                onClick={() => handleSelect(stock)}
                                style={{
                                    padding: '0.75rem 1rem',
                                    cursor: 'pointer',
                                    borderBottom: idx < searchResults.length - 1 ? '1px solid rgba(0, 0, 0, 0.05)' : 'none',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    transition: 'background 0.15s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(102, 126, 234, 0.08)'}
                                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                            >
                                <span style={{
                                    fontWeight: 700,
                                    color: '#667eea',
                                    minWidth: '60px'
                                }}>
                                    {stock.symbol}
                                </span>
                                <span style={{
                                    color: '#666',
                                    fontSize: '0.85rem',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap'
                                }}>
                                    {stock.name}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </form>

            {/* Display analyzed stocks as tags */}
            {analyzedStocks.length > 0 && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    marginTop: '0.75rem',
                    padding: '0 0.25rem'
                }}>
                    <span style={{
                        fontSize: '0.8rem',
                        color: 'var(--text-secondary)',
                        alignSelf: 'center',
                        marginRight: '0.25rem'
                    }}>
                        📊 Analyzing:
                    </span>
                    {onClearAnalysis && (
                        <button
                            onClick={onClearAnalysis}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.15rem 0.5rem',
                                background: 'rgba(239, 83, 80, 0.1)',
                                borderRadius: '12px',
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                color: '#ef5350',
                                border: '1px solid rgba(239, 83, 80, 0.2)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                marginRight: '0.5rem'
                            }}
                            title="Clear all analyzed stocks"
                        >
                            🗑️ Clear
                        </button>
                    )}
                    {analyzedStocks.map(symbol => (
                        <span
                            key={symbol}
                            onMouseEnter={() => setHoveredStock(symbol)}
                            onMouseLeave={() => setHoveredStock(null)}
                            onClick={() => onRemoveStock && onRemoveStock(symbol)}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.25rem 0.75rem',
                                background: hoveredStock === symbol
                                    ? 'linear-gradient(135deg, rgba(231, 76, 60, 0.2), rgba(192, 57, 43, 0.2))'
                                    : 'linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15))',
                                borderRadius: '20px',
                                fontSize: '0.85rem',
                                fontWeight: 600,
                                color: hoveredStock === symbol ? '#e74c3c' : '#667eea',
                                border: hoveredStock === symbol
                                    ? '1px solid rgba(231, 76, 60, 0.3)'
                                    : '1px solid rgba(102, 126, 234, 0.2)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            {symbol}
                            {hoveredStock === symbol && (
                                <span style={{
                                    fontSize: '0.75rem',
                                    fontWeight: 700,
                                    marginLeft: '2px'
                                }}>✕</span>
                            )}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}

// Quick Add Stock Component with Autocomplete
function QuickAddStock({ onAddStock, disabled }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const debounceRef = React.useRef(null);

    const searchStocks = async (searchQuery) => {
        if (searchQuery.length < 1) {
            setResults([]);
            setShowDropdown(false);
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`/api/search-stocks/${encodeURIComponent(searchQuery)}`);
            if (res.ok) {
                const data = await res.json();
                setResults(data.results || []);
                setShowDropdown(data.results && data.results.length > 0);
            }
        } catch (e) {
            console.error('Search error:', e);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        setQuery(value);

        // Debounce search calls
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }
        debounceRef.current = setTimeout(() => {
            searchStocks(value);
        }, 300);
    };

    const handleSelect = (stock) => {
        setQuery('');
        setResults([]);
        setShowDropdown(false);
        if (onAddStock) {
            onAddStock(stock.symbol);
        }
    };

    const handleBlur = () => {
        // Delay hiding dropdown to allow click on results
        setTimeout(() => setShowDropdown(false), 200);
    };

    return (
        <div style={{
            position: 'relative',
            marginBottom: '1rem',
            maxWidth: '400px'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1))',
                borderRadius: '12px',
                border: '1px solid rgba(102, 126, 234, 0.2)'
            }}>
                <span style={{ fontSize: '1.2rem' }}>➕</span>
                <input
                    type="text"
                    value={query}
                    onChange={handleInputChange}
                    onFocus={() => query.length > 0 && results.length > 0 && setShowDropdown(true)}
                    onBlur={handleBlur}
                    placeholder="Quick add stock..."
                    disabled={disabled}
                    style={{
                        flex: 1,
                        border: 'none',
                        background: 'transparent',
                        fontSize: '0.95rem',
                        color: 'var(--text-primary)',
                        outline: 'none'
                    }}
                />
                {loading && <span style={{ fontSize: '0.8rem', color: '#667eea' }}>⏳</span>}
            </div>

            {showDropdown && results.length > 0 && (
                <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    marginTop: '4px',
                    background: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
                    border: '1px solid rgba(0, 0, 0, 0.1)',
                    zIndex: 1000,
                    maxHeight: '300px',
                    overflowY: 'auto'
                }}>
                    {results.map((stock, idx) => (
                        <div
                            key={stock.symbol}
                            onClick={() => handleSelect(stock)}
                            style={{
                                padding: '0.75rem 1rem',
                                cursor: 'pointer',
                                borderBottom: idx < results.length - 1 ? '1px solid rgba(0, 0, 0, 0.05)' : 'none',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                transition: 'background 0.15s ease'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(102, 126, 234, 0.08)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                            <span style={{
                                fontWeight: 700,
                                color: '#667eea',
                                minWidth: '60px'
                            }}>
                                {stock.symbol}
                            </span>
                            <span style={{
                                color: 'var(--text-secondary)',
                                fontSize: '0.85rem',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                            }}>
                                {stock.name}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}


function Dashboard({ data, onRefreshStock, refreshingStock, cspData, setCspData }) {
    const stocks = Array.isArray(data) ? data : [data];
    return (
        <div>
            <CSPSummaryTable
                stocks={stocks}
                cachedData={cspData}
                setCachedData={setCspData}
            />
            <div className="stock-grid">
                {stocks.map((stock, idx) => (
                    <StockAnalysis
                        key={stock.symbol || idx}
                        data={stock}
                        onRefresh={onRefreshStock}
                        isRefreshing={refreshingStock === stock.symbol}
                    />
                ))}
            </div>
        </div>
    );
}

function CSPSummaryTable({ stocks, cachedData = {}, setCachedData }) {
    const [cspData, setCspData] = useState(cachedData);
    const [loading, setLoading] = useState(false);
    const [emailStatus, setEmailStatus] = useState(null);

    // Sorting state
    const [sortColumn, setSortColumn] = useState('rank');
    const [sortDirection, setSortDirection] = useState('desc');

    // Filtering state
    const [filterRating, setFilterRating] = useState('all');
    const [filterRSI, setFilterRSI] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');

    // Sync from cache prop if it updates
    useEffect(() => {
        setCspData(cachedData);
    }, [cachedData]);

    useEffect(() => {
        const fetchNeededData = async () => {
            // Filter valid stocks
            const validStocks = stocks.filter(stock => !stock.error && stock.symbol);

            // Identify which stocks are missing from cache
            const missingStocks = validStocks.filter(stock => !cachedData[stock.symbol]);

            if (missingStocks.length === 0) {
                // All data is already cached!
                setLoading(false);
                return;
            }

            // Only show loading if we actually need to fetch something
            setLoading(true);

            // Fetch MISSING stocks in parallel
            const fetchPromises = missingStocks.map(async (stock) => {
                try {
                    // Fetch both volatility and CSP metrics in parallel
                    const [volRes, metricsRes] = await Promise.all([
                        fetch(`/api/volatility/${stock.symbol}`),
                        fetch(`/api/csp-metrics/${stock.symbol}`)
                    ]);

                    const volData = volRes.ok ? await volRes.json() : {};
                    const metricsData = metricsRes.ok ? await metricsRes.json() : {};

                    return {
                        symbol: stock.symbol,
                        data: { ...volData, ...metricsData }
                    };
                } catch (e) {
                    console.error(`Failed to fetch CSP data for ${stock.symbol}`);
                    return { symbol: stock.symbol, data: {} };
                }
            });

            // Wait for new fetches
            const newResults = await Promise.all(fetchPromises);

            // Update cache with new data
            if (setCachedData) {
                setCachedData(prevCache => {
                    const newCache = { ...prevCache };
                    newResults.forEach(({ symbol, data }) => {
                        newCache[symbol] = data;
                    });
                    return newCache;
                });
            } else {
                // Fallback if no cache setter provided (local state only)
                const newLocalData = { ...cspData };
                newResults.forEach(({ symbol, data }) => {
                    newLocalData[symbol] = data;
                });
                setCspData(newLocalData);
            }

            setLoading(false);
        };

        if (stocks && stocks.length > 0) {
            fetchNeededData();
        }
    }, [stocks]); // Dependency on stocks: if list changes, check if we need new data

    // Determine CSP suitability rating
    const getCSPRating = (volData) => {
        if (!volData) return { text: 'N/A', color: 'var(--text-secondary)', icon: '⚪', rank: null, sortOrder: 0 };

        const rank = volData.iv_rank !== null ? volData.iv_rank : volData.hv_rank;
        if (rank === null) return { text: 'N/A', color: 'var(--text-secondary)', icon: '⚪', rank: null, sortOrder: 0 };

        if (rank >= 75) {
            return { text: 'Excellent', color: '#9b59b6', icon: '🟣', rank, sortOrder: 4 };
        } else if (rank >= 50) {
            return { text: 'Good', color: 'var(--success)', icon: '🟢', rank, sortOrder: 3 };
        } else if (rank >= 25) {
            return { text: 'Moderate', color: '#f39c12', icon: '🟡', rank, sortOrder: 2 };
        } else {
            return { text: 'Poor', color: 'var(--danger)', icon: '🔴', rank, sortOrder: 1 };
        }
    };

    // Handle column sort
    const handleSort = (column) => {
        if (sortColumn === column) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortDirection(column === 'symbol' ? 'asc' : 'desc');
        }
    };

    // Get sort value for a stock
    const getSortValue = (stock, column) => {
        const volData = cspData[stock.symbol];
        const rating = getCSPRating(volData);

        switch (column) {
            case 'symbol': return stock.symbol || '';
            case 'company': return stock.name || '';
            case 'price': return stock.price || 0;
            case 'change': return stock.change_1d_pct || 0;
            case 'rsi': return stock.indicators?.RSI || 0;
            case 'low52': return volData?.week52_low || 0;
            case 'high52': return volData?.week52_high || 0;
            case 'rank': return rating.rank || 0;
            case 'rating': return rating.sortOrder || 0;
            default: return 0;
        }
    };

    // Filter and sort stocks
    const filteredAndSortedStocks = [...stocks]
        .filter(s => !s.error && s.symbol)
        .filter(stock => {
            // Search filter
            if (searchTerm && !stock.symbol.toLowerCase().includes(searchTerm.toLowerCase())) {
                return false;
            }

            // Rating filter
            if (filterRating !== 'all') {
                const rating = getCSPRating(cspData[stock.symbol]);
                if (rating.text.toLowerCase() !== filterRating) return false;
            }

            // RSI filter
            if (filterRSI !== 'all') {
                const rsi = stock.indicators?.RSI;
                if (rsi === null || rsi === undefined) return false;
                switch (filterRSI) {
                    case 'oversold': if (rsi >= 30) return false; break;
                    case 'neutral': if (rsi < 30 || rsi > 70) return false; break;
                    case 'overbought': if (rsi <= 70) return false; break;
                }
            }

            return true;
        })
        .sort((a, b) => {
            const valA = getSortValue(a, sortColumn);
            const valB = getSortValue(b, sortColumn);

            if (sortColumn === 'symbol') {
                return sortDirection === 'asc'
                    ? valA.localeCompare(valB)
                    : valB.localeCompare(valA);
            }

            return sortDirection === 'asc' ? valA - valB : valB - valA;
        });

    // Reset filters
    const resetFilters = () => {
        setFilterRating('all');
        setFilterRSI('all');
        setSearchTerm('');
        setSortColumn('rank');
        setSortDirection('desc');
    };

    // Check if any filters are active
    const hasActiveFilters = filterRating !== 'all' || filterRSI !== 'all' || searchTerm !== '';

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

            {/* Filter Bar */}
            {!loading && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.75rem',
                    marginBottom: '1rem',
                    padding: '0.75rem',
                    background: 'rgba(0, 0, 0, 0.02)',
                    borderRadius: '8px',
                    alignItems: 'center'
                }}>
                    {/* Search */}
                    <div style={{ flex: '1', minWidth: '150px' }}>
                        <input
                            type="text"
                            placeholder="🔍 Search symbol..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.5rem 0.75rem',
                                border: '1px solid rgba(0, 0, 0, 0.1)',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                                outline: 'none'
                            }}
                        />
                    </div>

                    {/* Rating Filter */}
                    <select
                        value={filterRating}
                        onChange={(e) => setFilterRating(e.target.value)}
                        style={{
                            padding: '0.5rem 0.75rem',
                            border: '1px solid rgba(0, 0, 0, 0.1)',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            background: 'white',
                            cursor: 'pointer'
                        }}
                    >
                        <option value="all">All Ratings</option>
                        <option value="excellent">🟣 Excellent</option>
                        <option value="good">🟢 Good</option>
                        <option value="moderate">🟡 Moderate</option>
                        <option value="poor">🔴 Poor</option>
                    </select>

                    {/* RSI Filter */}
                    <select
                        value={filterRSI}
                        onChange={(e) => setFilterRSI(e.target.value)}
                        style={{
                            padding: '0.5rem 0.75rem',
                            border: '1px solid rgba(0, 0, 0, 0.1)',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            background: 'white',
                            cursor: 'pointer'
                        }}
                    >
                        <option value="all">All RSI</option>
                        <option value="oversold">📉 Oversold (&lt;30)</option>
                        <option value="neutral">➖ Neutral (30-70)</option>
                        <option value="overbought">📈 Overbought (&gt;70)</option>
                    </select>

                    {/* Reset Button */}
                    {hasActiveFilters && (
                        <button
                            onClick={resetFilters}
                            style={{
                                padding: '0.5rem 0.75rem',
                                border: '1px solid rgba(0, 0, 0, 0.1)',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                                background: 'white',
                                cursor: 'pointer',
                                color: '#e74c3c',
                                fontWeight: 500
                            }}
                        >
                            ✕ Reset
                        </button>
                    )}

                    {/* Results Count */}
                    <span style={{
                        fontSize: '0.8rem',
                        color: 'var(--text-secondary)',
                        marginLeft: 'auto'
                    }}>
                        Showing {filteredAndSortedStocks.length} of {stocks.filter(s => !s.error && s.symbol).length}
                    </span>
                </div>
            )}

            {loading ? (
                <div style={{
                    textAlign: 'center',
                    padding: '1rem',
                    color: 'var(--text-secondary)'
                }}>
                    Analyzing volatility data...
                </div>
            ) : (
                <div style={{
                    overflowX: 'auto',
                    WebkitOverflowScrolling: 'touch',
                    marginLeft: '-0.5rem',
                    marginRight: '-0.5rem',
                    paddingLeft: '0.5rem',
                    paddingRight: '0.5rem'
                }}>
                    <table style={{
                        width: '100%',
                        minWidth: '700px',
                        borderCollapse: 'collapse',
                        fontSize: '0.85rem'
                    }}>
                        <thead>
                            <tr style={{
                                borderBottom: '2px solid rgba(0, 0, 0, 0.1)'
                            }}>
                                {[
                                    { key: 'symbol', label: 'Symbol' },
                                    { key: 'company', label: 'Company' },
                                    { key: 'price', label: 'Price' },
                                    { key: 'change', label: '1D Chg' },
                                    { key: 'rsi', label: 'RSI' },
                                    { key: 'low52', label: '52L' },
                                    { key: 'high52', label: '52H' },
                                    { key: 'rank', label: 'Rank' },
                                    { key: 'rating', label: 'Rating' }
                                ].map(({ key, label }) => (
                                    <th
                                        key={key}
                                        onClick={() => handleSort(key)}
                                        style={{
                                            textAlign: 'left',
                                            padding: '0.5rem 0.5rem',
                                            color: sortColumn === key ? '#667eea' : '#555',
                                            fontWeight: 600,
                                            fontSize: '0.75rem',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.3px',
                                            cursor: 'pointer',
                                            userSelect: 'none',
                                            transition: 'color 0.2s ease',
                                            whiteSpace: 'nowrap'
                                        }}
                                    >
                                        {label}
                                        <span style={{
                                            marginLeft: '2px',
                                            opacity: sortColumn === key ? 1 : 0.3,
                                            fontSize: '0.65rem'
                                        }}>
                                            {sortColumn === key
                                                ? (sortDirection === 'asc' ? '▲' : '▼')
                                                : '⇅'
                                            }
                                        </span>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filteredAndSortedStocks.length === 0 ? (
                                <tr>
                                    <td colSpan="9" style={{
                                        textAlign: 'center',
                                        padding: '2rem',
                                        color: 'var(--text-secondary)'
                                    }}>
                                        No stocks match your filters. Try adjusting your criteria.
                                    </td>
                                </tr>
                            ) : filteredAndSortedStocks.map((stock, idx) => {
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
                                            padding: '0.5rem',
                                            fontWeight: 700,
                                            fontSize: '0.9rem',
                                            color: '#1a1a2e'
                                        }}>
                                            {stock.symbol}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem',
                                            fontSize: '0.8rem',
                                            color: '#555',
                                            maxWidth: '150px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap'
                                        }} title={stock.name}>
                                            {stock.name || '-'}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem',
                                            fontWeight: 600,
                                            color: '#2e7d32',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            ${stock.price?.toFixed(2) || 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem',
                                            fontWeight: 600,
                                            color: stock.change_1d >= 0 ? '#27ae60' : '#e74c3c',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            {stock.change_1d !== null && stock.change_1d !== undefined ? (
                                                <>
                                                    {stock.change_1d_pct >= 0 ? '+' : ''}{stock.change_1d_pct?.toFixed(1)}%
                                                </>
                                            ) : 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem'
                                        }}>
                                            {(() => {
                                                const rsi = stock.indicators?.RSI;
                                                if (rsi === null || rsi === undefined) {
                                                    return <span style={{ color: '#999' }}>N/A</span>;
                                                }
                                                let rsiColor = '#666';
                                                if (rsi > 70) rsiColor = '#e74c3c';
                                                else if (rsi < 30) rsiColor = '#27ae60';
                                                return (
                                                    <span style={{ fontWeight: 600, color: rsiColor }}>
                                                        {rsi.toFixed(0)}
                                                    </span>
                                                );
                                            })()}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem',
                                            fontWeight: 500,
                                            color: '#27ae60',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            {volData?.week52_low ? `$${volData.week52_low.toFixed(0)}` : 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem',
                                            fontWeight: 500,
                                            color: '#e74c3c',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            {volData?.week52_high ? `$${volData.week52_high.toFixed(0)}` : 'N/A'}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            {rank !== null && rank !== undefined ? (
                                                <span style={{ fontWeight: 600, color: rating.color }}>
                                                    {rank.toFixed(0)}%
                                                </span>
                                            ) : (
                                                <span style={{ color: 'var(--text-secondary)' }}>N/A</span>
                                            )}
                                        </td>
                                        <td style={{
                                            padding: '0.5rem'
                                        }}>
                                            <span style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.25rem',
                                                padding: '0.2rem 0.5rem',
                                                borderRadius: '12px',
                                                fontWeight: 600,
                                                fontSize: '0.7rem',
                                                color: rating.color,
                                                background: `${rating.color}15`,
                                                whiteSpace: 'nowrap'
                                            }}>
                                                {rating.icon} {rating.text}
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table >
                </div >
            )
            }
        </div >
    );
}

function StockAnalysis({ data, onRefresh, isRefreshing }) {
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
                <div className="price-display" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span>${data.price.toFixed(2)}</span>
                    {onRefresh && (
                        <button
                            onClick={() => onRefresh(data.symbol)}
                            disabled={isRefreshing}
                            style={{
                                background: 'rgba(102, 126, 234, 0.1)',
                                border: 'none',
                                color: '#667eea',
                                borderRadius: '50%',
                                width: '32px',
                                height: '32px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: isRefreshing ? 'default' : 'pointer',
                                opacity: isRefreshing ? 0.7 : 1,
                                padding: 0,
                                transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => !isRefreshing && (e.target.style.background = 'rgba(102, 126, 234, 0.2)')}
                            onMouseLeave={(e) => !isRefreshing && (e.target.style.background = 'rgba(102, 126, 234, 0.1)')}
                            title="Refresh Data"
                        >
                            <span style={{
                                animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
                                display: 'inline-block',
                                fontSize: '1.2rem',
                                lineHeight: 1,
                                fontWeight: 'bold'
                            }}>
                                ↻
                            </span>
                        </button>
                    )}
                </div>
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

                <VolatilityCard key={`vol-${data.symbol}-${data._lastRefreshed || 0}`} symbol={data.symbol} />

                <MysticPulseCard key={`pulse-${data.symbol}-${data._lastRefreshed || 0}`} symbol={data.symbol} />

                <CSPMetricsCard key={`csp-${data.symbol}-${data._lastRefreshed || 0}`} symbol={data.symbol} />

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

        apiQueue.add(() => fetch(`/api/volatility/${symbol}`).then(res => {
            if (!res.ok) throw new Error('Failed to fetch volatility data');
            return res.json();
        }))
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

        apiQueue.add(() => fetch(`/api/csp-metrics/${symbol}`).then(res => {
            if (!res.ok) throw new Error('Failed to fetch CSP metrics');
            return res.json();
        }))
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

        // Handle resize with ResizeObserver
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        const resizeObserver = new ResizeObserver(entries => {
            window.requestAnimationFrame(() => handleResize());
        });
        resizeObserver.observe(chartContainerRef.current);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
        };
    }, []);

    useEffect(() => {
        if (!chartRef.current) return;

        setLoading(true);
        setError(null);

        apiQueue.add(() => fetch(`/api/history/${symbol}?period=${period}`).then(res => {
            if (!res.ok) throw new Error('Failed to fetch history');
            return res.json();
        }))
            .then(data => {
                if (!data.history || data.history.length === 0) {
                    throw new Error('No data');
                }

                // Remove old series
                if (seriesRef.current) {
                    chartRef.current.removeSeries(seriesRef.current);
                    seriesRef.current = null;
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




// ============================================
// Mystic Pulse v2.0 Indicator Component with Price + Histogram Chart
// ============================================
function MysticPulseCard({ symbol }) {
    const [pulseData, setPulseData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Refs for price chart (top)
    const priceChartContainerRef = React.useRef(null);
    const priceChartRef = React.useRef(null);

    // Refs for histogram chart (bottom)
    const histogramContainerRef = React.useRef(null);
    const histogramChartRef = React.useRef(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        apiQueue.add(() => fetch(`/api/mystic-pulse/${symbol}?period=1y`).then(res => {
            if (!res.ok) throw new Error('Failed to fetch Mystic Pulse data');
            return res.json();
        }))
            .then(data => {
                setPulseData(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [symbol]);

    // Create charts when data is loaded
    useEffect(() => {
        if (!pulseData || !pulseData.data || !priceChartContainerRef.current || !histogramContainerRef.current) return;

        // Clean up existing charts
        if (priceChartRef.current) {
            priceChartRef.current.remove();
            priceChartRef.current = null;
        }
        if (histogramChartRef.current) {
            histogramChartRef.current.remove();
            histogramChartRef.current = null;
        }

        // === PRICE CHART (Top) ===
        const priceChart = LightweightCharts.createChart(priceChartContainerRef.current, {
            width: priceChartContainerRef.current.clientWidth,
            height: 200,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#9ca3af',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
        });

        priceChartRef.current = priceChart;

        // Add candlestick series with custom colors based on Mystic Pulse
        const candleSeries = priceChart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });

        // Prepare candlestick data with colors based on Mystic Pulse direction
        const candleData = pulseData.data.map(item => {
            const direction = item.dominant_direction;
            const intensity = direction > 0 ? (item.positive_intensity || 0.5) : (item.negative_intensity || 0.5);

            let upColor, downColor, wickColor;
            if (direction > 0) {
                // Bullish - use green shades
                const g = Math.round(90 + 165 * intensity);
                const b = Math.round(102 * intensity);
                upColor = `rgb(0, ${g}, ${b})`;
                downColor = `rgb(0, ${Math.max(60, g - 50)}, ${Math.max(0, b - 30)})`;
                wickColor = upColor;
            } else if (direction < 0) {
                // Bearish - use red shades
                const r = Math.round(122 + 133 * intensity);
                const g = Math.round(26 * intensity);
                upColor = `rgb(${Math.max(100, r - 50)}, ${g}, ${g})`;
                downColor = `rgb(${r}, ${g}, ${g})`;
                wickColor = downColor;
            } else {
                // Neutral - gray
                upColor = '#6B7280';
                downColor = '#4B5563';
                wickColor = '#6B7280';
            }

            return {
                time: item.date,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
                color: item.close >= item.open ? upColor : downColor,
                borderColor: item.close >= item.open ? upColor : downColor,
                wickColor: wickColor,
            };
        });

        candleSeries.setData(candleData);

        // === HISTOGRAM CHART (Bottom) ===
        const histogramChart = LightweightCharts.createChart(histogramContainerRef.current, {
            width: histogramContainerRef.current.clientWidth,
            height: 80,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#9ca3af',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                scaleMargins: { top: 0.1, bottom: 0.1 },
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                visible: false, // Hide time scale on histogram (synced with price chart)
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
        });

        histogramChartRef.current = histogramChart;

        // Add histogram series
        const histSeries = histogramChart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });

        // Prepare histogram data
        const histData = pulseData.data.map(item => {
            const direction = item.dominant_direction;
            const intensity = direction > 0 ? (item.positive_intensity || 0) : (item.negative_intensity || 0);
            const value = direction > 0 ? intensity * 20 : (direction < 0 ? -intensity * 20 : 0);

            let color;
            if (direction > 0) {
                const g = Math.round(90 + 165 * intensity);
                const b = Math.round(102 * intensity);
                color = `rgba(0, ${g}, ${b}, 0.9)`;
            } else if (direction < 0) {
                const r = Math.round(122 + 133 * intensity);
                color = `rgba(${r}, ${Math.round(26 * intensity)}, ${Math.round(26 * intensity)}, 0.9)`;
            } else {
                color = 'rgba(107, 114, 128, 0.5)';
            }

            return { time: item.date, value: value, color: color };
        });

        histSeries.setData(histData);

        // Sync time scales
        priceChart.timeScale().fitContent();
        histogramChart.timeScale().fitContent();

        // Sync visible range
        priceChart.timeScale().subscribeVisibleTimeRangeChange((range) => {
            if (range && histogramChartRef.current) {
                histogramChartRef.current.timeScale().setVisibleRange(range);
            }
        });

        // Handle resize
        const handleResize = () => {
            if (priceChartContainerRef.current && priceChartRef.current) {
                priceChartRef.current.applyOptions({ width: priceChartContainerRef.current.clientWidth });
            }
            if (histogramContainerRef.current && histogramChartRef.current) {
                histogramChartRef.current.applyOptions({ width: histogramContainerRef.current.clientWidth });
            }
        };

        const resizeObserver = new ResizeObserver(entries => {
            // Wrap in requestAnimationFrame to avoid "ResizeObserver loop limit exceeded"
            window.requestAnimationFrame(() => {
                handleResize();
            });
        });

        if (priceChartContainerRef.current) {
            resizeObserver.observe(priceChartContainerRef.current);
        }

        return () => {
            resizeObserver.disconnect();
            if (priceChartRef.current) {
                priceChartRef.current.remove();
                priceChartRef.current = null;
            }
            if (histogramChartRef.current) {
                histogramChartRef.current.remove();
                histogramChartRef.current = null;
            }
        };
    }, [pulseData]);

    if (loading) {
        return (
            <Card title="🔮 Mystic Pulse v2.0">
                <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    Analyzing directional momentum...
                </div>
            </Card>
        );
    }

    if (error || !pulseData || !pulseData.summary) {
        return (
            <Card title="🔮 Mystic Pulse v2.0">
                <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    Indicator unavailable
                </div>
            </Card>
        );
    }

    const summary = pulseData.summary;

    // Get trend colors
    const getTrendColor = (trend, strength) => {
        if (trend === 'bullish') {
            const intensity = Math.min(strength, 1);
            return `rgb(${Math.round(0)}, ${Math.round(90 + 165 * intensity)}, ${Math.round(0 + 102 * intensity)})`;
        } else if (trend === 'bearish') {
            const intensity = Math.min(strength, 1);
            return `rgb(${Math.round(122 + 133 * intensity)}, ${Math.round(0 + 26 * intensity)}, ${Math.round(0 + 26 * intensity)})`;
        }
        return 'rgb(128, 128, 128)';
    };

    const trendColor = getTrendColor(summary.trend, summary.strength);
    const trendEmoji = summary.trend === 'bullish' ? '🟢' : summary.trend === 'bearish' ? '🔴' : '⚪';

    return (
        <Card title="🔮 Mystic Pulse v2.0">
            {/* Price Candlestick Chart (Top) */}
            <div
                ref={priceChartContainerRef}
                style={{
                    width: '100%',
                    height: '200px',
                    borderRadius: '8px 8px 0 0',
                    overflow: 'hidden'
                }}
            />

            {/* Histogram Chart (Bottom) */}
            <div
                ref={histogramContainerRef}
                style={{
                    width: '100%',
                    height: '80px',
                    borderRadius: '0 0 8px 8px',
                    overflow: 'hidden',
                    borderTop: '1px solid rgba(255,255,255,0.05)'
                }}
            />

            {/* Trend Summary Row */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem',
                marginTop: '0.75rem',
                background: `linear-gradient(135deg, ${trendColor}22, ${trendColor}11)`,
                border: `1px solid ${trendColor}44`,
                borderRadius: '8px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>{trendEmoji}</span>
                    <div>
                        <div style={{
                            fontSize: '1rem',
                            fontWeight: 700,
                            color: trendColor,
                            textTransform: 'capitalize'
                        }}>
                            {summary.trend}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {summary.momentum === 'strengthening' ? '📈' : summary.momentum === 'weakening' ? '📉' : '➡️'} {summary.momentum}
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>+DI</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#00FF66' }}>{summary.di_plus}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>-DI</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#FF1A1A' }}>{summary.di_minus}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: trendColor }}>
                            {(summary.strength * 100).toFixed(0)}%
                        </div>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>Strength</div>
                    </div>
                </div>
            </div>
        </Card>
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
