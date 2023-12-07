import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // Importing the external CSS file

function TokenManager({ setTokenFromApp }) {
  const [id, setId] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');

  const addToken = async () => {
    if (!id) {
      setError('Please enter an ID');
      return;
    }
    setError('');
    try {
      const response = await axios.post(`/add-token/${id}`);
      const newToken = response.data.token;
      setToken(newToken);
      setTokenFromApp(newToken); // Update token in App.js
    } catch (error) {
      console.error('Error adding token:', error);
      setError('Failed to add token');
    }
  };

  const revokeToken = async () => {
    if (!id) {
      setError('Please enter an ID or Token to revoke');
      return;
    }
    setError('');
    try {
      const response = await axios.post('/revoke-token', { token: id });
      alert(response.data.message); // Alert success message
    } catch (error) {
      console.error('Error revoking token:', error);
      if (error.response) {
        // Handle specific status codes
        if (error.response.status === 404) {
          setError('Token or ID not found');
        } else if (error.response.status === 429) {
          setError('Rate limit exceeded. Please try again later.');
        } else {
          setError('Failed to revoke token');
        }
      } else {
        setError('Failed to revoke token');
      }
    }
  };

  return (
    <div className="container">
      <input
        className="input"
        type="text"
        placeholder="Enter ID"
        value={id}
        onChange={e => setId(e.target.value)}
      />
      <button className="button" onClick={addToken}>Add Token</button>
      <button className="button" onClick={revokeToken}>Revoke Token/ID</button>
      {token && <div className="response">Token: {token}</div>}
      {error && <div className={`response error`}>{error}</div>}
    </div>
  );
}

export default TokenManager;

