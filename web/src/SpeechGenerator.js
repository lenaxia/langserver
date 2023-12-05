import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // Make sure to import the stylesheet

function SpeechGenerator({ token }) {
  const [requestData, setRequestData] = useState(
    JSON.stringify({
      localization: {
        "zh-tw": "馬",
        en: "horse"
      }
    }) +
    "\n\nor\n\n" +
    JSON.stringify({
      text: "horse",
      language: "en",
      translations: ["zh-TW", "de"]
    })
  );
  const [audioUrl, setAudioUrl] = useState(null);
  const [error, setError] = useState('');

  const generateSpeech = async () => {
    if (!token) {
      setError('Authorization token is required');
      return;
    }
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/generate-speech', requestData, {
        headers: {
          'Authorization': token,
          'Content-Type': 'application/json'
        },
        responseType: 'blob'
      });

      const url = URL.createObjectURL(response.data);
      setAudioUrl(url);
    } catch (error) {
      console.error('Error generating speech:', error);
      setError('Failed to generate speech');
    }
  };

  return (
    <div className="container">
      <textarea
        className="input"
        value={requestData}
        onChange={e => setRequestData(e.target.value)}
        style={{ height: '100px' }} // Additional inline style for textarea height
      />
      <button className="button" onClick={generateSpeech}>Generate Speech</button>
      {audioUrl && <div><audio className="audioPlayer" controls src={audioUrl} /></div>}
      {error && <div className={`response error`}>{error}</div>}
    </div>
  );
}

export default SpeechGenerator;

