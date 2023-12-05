import React, { useState } from 'react';
import './App.css';
import TokenTable from './TokenTable';
import SpeechGenerator from './SpeechGenerator'; // Import SpeechGenerator


function App() {
  const [adminToken, setAdminToken] = useState('');
  const [isTokenSubmitted, setIsTokenSubmitted] = useState(false);

  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://192.168.2.110:5000';

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
        {isTokenSubmitted && (
          <div className="components-wrapper">
            <SpeechGenerator token={adminToken} apiUrl={API_BASE_URL} />
            <TokenTable adminToken={adminToken} apiUrl={API_BASE_URL} />
          </div>
        )}
        </header>
    </div>
  );
}

export default App;
