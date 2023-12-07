import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEdit, faTrashAlt, faSave, faTimes, faRedo } from '@fortawesome/free-solid-svg-icons';
import './App.css';

function TokenTable({ adminToken }) {
  const [id, setId] = useState('');
  const [tokens, setTokens] = useState([]);
  const [error, setError] = useState('');
  const [editTokenId, setEditTokenId] = useState(null);
  const [editedRateLimit, setEditedRateLimit] = useState({});
  const [newToken, setNewToken] = useState(null);
  const [newTokenId, setNewTokenId] = useState('');

  useEffect(() => {
    fetchTokens();
  }, [adminToken]);

  const fetchTokens = async () => {
    try {
      const response = await axios.get('/list-tokens', {
        headers: { Authorization: adminToken }
      });
      setTokens(response.data);
    } catch (error) {
      console.error('Error fetching tokens:', error);
      setError('Failed to fetch tokens');
    }
  };

  const addToken = async () => {
    if (!id) {
      setError('Please enter an ID');
      return;
    }
    setError('');
    try {
      const requestData = {
        id: id
      };
      const response = await axios.post('/add-token', requestData);
      const newToken = response.data.token;
      setNewToken(newToken); // Update the state with the new token
      setId('');
      fetchTokens(); // Optionally, refresh the token list
    } catch (error) {
      console.error('Error adding token:', error);
      setError('Failed to add token');
    }
  };


  const handleRegenerateClick = async (tokenId) => {
    const confirmRegenerate = window.confirm('Are you sure you want to regenerate this token?');
    if (confirmRegenerate) {
      try {
        const tokenDetails = tokens.find(token => token.id === tokenId);
        if (!tokenDetails) {
          console.error('Token details not found');
          setError('Token details not found');
          return;
        }

        // Revoke the existing token
        await axios.post('/revoke-token', { id: tokenId }, {
          headers: { Authorization: adminToken }
        });

        // Regenerate the token with the same ID and the previous rate limit
        const response = await axios.post(`/add-token`, { id: tokenId, rate_limit: tokenDetails.rate_limit }, {
          headers: { Authorization: adminToken }
        }); 
          
        const newToken = response.data.token;
        setNewToken(newToken); // Update the state with the new token
        fetchTokens(); // Refresh the token list
      } catch (error) {
        console.error('Error regenerating token:', error);
        setError('Failed to regenerate token');
      }
    }
  };
  
  

  const handleDeleteClick = async (tokenId) => {
    // Display a confirmation dialog
    const confirmDelete = window.confirm('Are you sure you want to delete this token?');
    if (confirmDelete) {
      // If the user confirms, proceed with the deletion
      try {
        await axios.post('/revoke-token', { token: tokenId }, {
          headers: { Authorization: adminToken }
        });
        fetchTokens(); // Refresh the token list
      } catch (error) {
        console.error('Error revoking token:', error);
        setError('Failed to revoke token');
      }
    }
    // If the user cancels, do nothing
  };
  

  const handleEditClick = (tokenId, rateLimit) => {
    setEditTokenId(tokenId);
    setEditedRateLimit({ ...editedRateLimit, [tokenId]: rateLimit });
  };

  const handleCancelEdit = () => {
    setEditTokenId(null);
  };

  const handleSaveEdit = async (tokenId) => {
    try {
      const newRateLimit = editedRateLimit[tokenId];
      await axios.post('/edit-token', 
        { id: tokenId, rate_limit: parseInt(newRateLimit, 10) },
        { headers: { Authorization: adminToken }}
      );
      fetchTokens();
      handleCancelEdit();
    } catch (error) {
      console.error('Error editing token:', error);
      setError('Failed to edit token');
    }
  };

  return (
    <div className="container">
      {newToken && (
        <div style={{ margin: '10px 0', padding: '10px' }} className="new-token-alert">
          <strong>New Token:</strong> {newToken}
        </div>
      )}
      <div style={{ textAlign: 'right' }}>
        <input
          className="input"
          type="text"
          placeholder="Enter ID"
          value={id}
          onChange={e => setId(e.target.value)}
        />
        <button className="button" onClick={addToken}>Add Token</button>
      </div>
      <table style={{ fontSize: '0.8rem' }} className="table table-sm table-bordered table-striped">
        <thead>
          <tr>
            <th>ID</th>
            <th className="hashed-token">Hashed+Salted Token</th>
            <th>Rate Limit</th>
            <th>Date Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => (
            <tr key={token.id}>
              <td>{token.id}</td>
              <td className="hashed-token">{token.token}</td>
              <td>
                {editTokenId === token.id ? (
                  <input 
                    type="text" 
                    value={editedRateLimit[token.id]} 
                    onChange={(e) => setEditedRateLimit({ ...editedRateLimit, [token.id]: e.target.value })}
                  />
                ) : (
                  token.rate_limit
                )}
              </td>
              <td>{token.date_created}</td>
              <td>
                {editTokenId === token.id ? (
                  <>
                    <FontAwesomeIcon icon={faSave} onClick={() => handleSaveEdit(token.id)} title="Save" />
                    <FontAwesomeIcon icon={faTimes} onClick={handleCancelEdit} title="Cancel" />
                  </>
                ) : (
                  <>
                    <FontAwesomeIcon icon={faEdit} onClick={() => handleEditClick(token.id, token.rate_limit)} title="Edit" />
                    <FontAwesomeIcon icon={faRedo} onClick={() => handleRegenerateClick(token.id)} title="Regenerate" />
                    <FontAwesomeIcon icon={faTrashAlt} onClick={() => handleDeleteClick(token.id)} title="Delete" />
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <div className="response error">{error}</div>}
    </div>
  );
}

export default TokenTable;
 
