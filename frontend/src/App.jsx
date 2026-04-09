import { useState } from 'react'
import './index.css'

function App() {
  const [text, setText] = useState('')
  const [strictness, setStrictness] = useState(2)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('http://127.0.0.1:8000/cite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          text,
          strictness
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to process request');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>SOURCERY</h1>
      </header>

      <main>
        <section className="input-section">
          <label htmlFor="text-input">Submit Academic Manuscript Excerpt</label>
          <textarea 
            id="text-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste a paragraph containing factual claims that require academic citations..."
          />
          
          <div className="slider-section">
            <label htmlFor="strictness-slider" className="slider-main-label">
              Relevancy Requirements: {strictness === 1 ? 'Strict' : strictness === 2 ? 'Balanced' : 'Desperate'}
            </label>
            <input 
              type="range" 
              id="strictness-slider" 
              min="1" max="3" step="1" 
              value={strictness} 
              onChange={(e) => setStrictness(parseInt(e.target.value))} 
            />
            <div className="slider-labels">
              <span>Rigorous Proofs</span>
              <span>Topical Matches</span>
              <span>Stretch Relevancy</span>
            </div>
          </div>

          <button onClick={handleSubmit} disabled={loading || !text.trim()}>
            {loading ? 'Processing...' : 'Identify Sources'}
          </button>
        </section>

        {loading && (
          <div className="loader">
            <div className="spinner"></div>
            <span>Querying academic databases and processing...</span>
          </div>
        )}

        {error && (
          <div style={{ color: 'var(--crimson-red)', marginTop: '20px', border: '1px solid var(--crimson-red)', padding: '15px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <section className="results-section">
            <h2>Annotated Manuscript</h2>
            <div className="annotated-text">
              {result.annotated_text.split('\n').map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>

            <h2>Bibliography (BibTeX)</h2>
            <pre className="bibtex-block">
              {result.bibtex}
            </pre>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
