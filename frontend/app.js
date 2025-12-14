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
        <div className="stock-grid">
            {stocks.map((stock, idx) => (
                <StockAnalysis key={stock.symbol || idx} data={stock} />
            ))}
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
        <div className="stock-grid-item">
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

// Recharts components from global
const { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } = Recharts;

function PriceChart({ symbol }) {
    const [historyData, setHistoryData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        fetch(`/api/history/${symbol}?period=3y`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch history');
                return res.json();
            })
            .then(data => {
                setHistoryData(data.history);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [symbol]);

    if (loading) {
        return (
            <div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Loading chart...
            </div>
        );
    }

    if (error || !historyData || historyData.length === 0) {
        return (
            <div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Chart unavailable
            </div>
        );
    }

    // Calculate if price is up or down overall
    const firstPrice = historyData[0]?.close || 0;
    const lastPrice = historyData[historyData.length - 1]?.close || 0;
    const isUp = lastPrice >= firstPrice;
    const chartColor = isUp ? 'var(--success)' : 'var(--danger)';

    // Custom tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div style={{
                    background: 'var(--bg-card)',
                    border: '1px solid rgba(0,0,0,0.1)',
                    borderRadius: '8px',
                    padding: '10px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}>
                    <div style={{ fontWeight: 600, marginBottom: '4px' }}>{data.date}</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <div>Open: ${data.open}</div>
                        <div>High: ${data.high}</div>
                        <div>Low: ${data.low}</div>
                        <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Close: ${data.close}</div>
                    </div>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ width: '100%', height: '150px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={historyData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                    <defs>
                        <linearGradient id={`gradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                        tickFormatter={(val) => val.slice(5)}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                        tickFormatter={(val) => `$${val}`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                        type="monotone"
                        dataKey="close"
                        stroke={chartColor}
                        strokeWidth={2}
                        fill={`url(#gradient-${symbol})`}
                        animationDuration={1000}
                    />
                </AreaChart>
            </ResponsiveContainer>
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
