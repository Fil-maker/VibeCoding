// Entry point: mounts App into the #root element of index.html and loads the design tokens.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import './styles/tokens.css';

const container = document.getElementById('root');
if (container === null) {
  throw new Error('The #root element is missing in index.html');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
