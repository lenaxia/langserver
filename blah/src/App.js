import React, { useState } from 'react';
import './App.css';
import TokenTable from './TokenTable';

function App() {
  const [adminToken, setAdminToken] = useState('');
  const [isTokenSubmitted, setIsTokenSubmitted] = useState(false);

  const handleTokenSubmit = () => {
    setIsTokenSubmitted(true);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>API Token Manager</h1>
        {!isTokenSubmitted && (
          <div className="container">
            <input
              type="text"
              className="input"
              placeholder="Enter Admin Token"
              value={adminToken}
              onChange={(e) => setAdminToken(e.target.value)}
            />
            <button className="button" onClick={handleTokenSubmit}>
              Submit
            </button>
          </div>
        )}
        {isTokenSubmitted && <TokenTable adminToken={adminToken} />}
      </header>
    </div>
  );
}

export default App;
