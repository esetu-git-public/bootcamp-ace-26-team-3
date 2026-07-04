// frontend/src/App.js
import React from 'react';
import CustomerProfile from './pages/CustomerProfile';

function App() {
  return (
    <div className="App">
      {/* Renders your Customer Profile & Churn Insights dashboard directly */}
      <CustomerProfile />
    </div>
  );
}

export default App;