import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext.jsx';
import App from './App.jsx';
import LoginPage from './pages/LoginPage.jsx';
import './index.css';

function Root() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem('ews_token'));

  if (!authed) {
    return <LoginPage onLogin={() => setAuthed(true)} />;
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
