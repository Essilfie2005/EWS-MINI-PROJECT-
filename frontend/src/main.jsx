import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext.jsx';
import App from './App.jsx';
import LoginPage from './pages/LoginPage.jsx';
import SignupPage from './pages/SignupPage.jsx';
import './index.css';

function Root() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem('ews_token'));

  // Show signup page at /signup regardless of auth state
  if (window.location.pathname === '/signup') {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/signup" element={<SignupPage />} />
        </Routes>
      </BrowserRouter>
    );
  }

  if (!authed) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<LoginPage onLogin={() => setAuthed(true)} />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <ToastProvider>
        <App onLogout={() => {
          localStorage.removeItem('ews_token');
          setAuthed(false);
        }} />
      </ToastProvider>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>
);
