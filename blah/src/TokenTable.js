import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEdit, faTrashAlt, faSave, faTimes, faRedo } from '@fortawesome/free-solid-svg-icons';
import './App.css';

function TokenTable({ adminToken }) {
  const [tokens, setTokens] = useState([]);
  const [error, setError] = useState('');
  const [editTokenId, setEditTokenId] = useState(null);
  const [editedRateLimit, setEditedRateLimit] = useState({});
  const [newToken, setNewToken] = useState(null);

  useEffect(() => {
    fetchTokens();
  }, [adminToken]);

  const fetchTokens = async () => {
    try {
      const response = await axios.get('http://localhost:5000/list-tokens', {
        headers: { Authorization: adminToken }
      });
      setTokens(response.data);
    } catch (error) {
      console.error('Error fetching tokens:', error);
      setError('Failed to fetch tokens');
    }
  };

  const handleRegenerateClick = async (tokenId) => {
    // Display a confirmation dialog
    const confirmRegenerate = window.confirm('Are you sure you want to regenerate this token?');
    if (confirmRegenerate) {
      // If the user confirms, proceed with the regeneration
      try {
        const response = await axios.post('http://localhost:5000/regenerate-token', { id: tokenId }, {
          headers: { Authorization: adminToken }
        });
        setNewToken(response.data.new_token); // Update the state with the new token
        fetchTokens(); // Refresh the token list
      } catch (error) {
        console.error('Error regenerating token:', error);
        setError('Failed to regenerate token');
      }
    }
    // If the user cancels, do nothing
  };
  

  const handleDeleteClick = async (tokenId) => {
    // Display a confirmation dialog
    const confirmDelete = window.confirm('Are you sure you want to delete this token?');
    if (confirmDelete) {
      // If the user confirms, proceed with the deletion
      try {
        await axios.post('http://localhost:5000/revoke-token', { token: tokenId }, {
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
      await axios.post('http://localhost:5000/edit-token', 
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
        <div style={{ fontSize: '0.8rem' }} className="new-token-alert">
          <strong>New Token:</strong> {newToken}
        </div>
      )}
      <table style={{ fontSize: '0.8rem' }} className="table table-sm table-bordered table-striped">
        <thead>
          <tr>
            <th>ID</th>
            <th>Hashed+Salted Token</th>
            <th>Rate Limit</th>
            <th>Date Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => (
            <tr key={token.id}>
              <td>{token.id}</td>
              <td>{token.token}</td>
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
 