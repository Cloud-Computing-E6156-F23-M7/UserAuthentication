import React, { useState } from 'react';
import AdminComponent from './components/AdminComponent';
import FeedbackComponent from './components/FeedbackComponent';
import ActionComponent from './components/ActionComponent';
import './App.css';

function App() {
  const [activeComponent, setActiveComponent] = useState(null); // No component is active initially

  return (
    <div className="App">
      <h1 className="header">Site Management Dashboard</h1>
      <div className="component-buttons">
        <button onClick={() => setActiveComponent('admin')}>Admins</button>
        <button onClick={() => setActiveComponent('feedback')}>Feedbacks</button>
        <button onClick={() => setActiveComponent('action')}>Actions</button>
      </div>
      {activeComponent === 'admin' && <AdminComponent />}
      {activeComponent === 'feedback' && <FeedbackComponent />}
      {activeComponent === 'action' && <ActionComponent />}
    </div>
  );
}

export default App;

